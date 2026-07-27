"""
llm.py
======
Groq API client wrapper + offline rule-based fallback.

Two things worth pointing out during a demo:

1. **Mode transparency.** ``generate_minutes`` always returns a ``MinutesResult``
   carrying an explicit ``mode`` ("live" / "offline" / "error"). The UI renders a
   different badge for each. A failing API call can therefore never be mistaken
   for "no key configured" — a trap that hides broken integrations.

2. **Defensive JSON parsing.** LLMs wrap JSON in code fences, prepend chatter, or
   (for reasoning models) emit a thinking preamble. ``_extract_json`` strips all
   of that with several escalating strategies before giving up.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

import prompts

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# NOTE: llama-3.3-70b-versatile and llama-3.1-8b-instant are decommissioned by
# Groq on 2026-08-16, so they are deliberately NOT offered here.
AVAILABLE_MODELS: dict[str, str] = {
    "openai/gpt-oss-120b": "GPT-OSS 120B — best quality (recommended)",
    "openai/gpt-oss-20b": "GPT-OSS 20B — faster, lighter",
    "qwen/qwen3.6-27b": "Qwen 3.6 27B — alternative",
    "moonshotai/kimi-k2-instruct-0905": "Kimi K2 — long context",
}

DEFAULT_MODEL = "openai/gpt-oss-120b"

# Roughly 4 characters per token; keep well inside a 128k context window.
MAX_TRANSCRIPT_CHARS = 48_000
CHUNK_SIZE = 14_000


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #


@dataclass
class MinutesResult:
    """Everything the UI needs to render one generation attempt."""

    data: dict[str, Any]
    mode: str = "live"           # "live" | "offline" | "error"
    model: str = ""
    error: str = ""
    raw: str = ""
    elapsed: float = 0.0
    chunked: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.data) and self.mode != "error"


# --------------------------------------------------------------------------- #
# API key discovery
# --------------------------------------------------------------------------- #


def get_api_key(override: str = "") -> str:
    """
    Resolve the Groq key from, in order:
      1. an explicit override typed into the sidebar
      2. the GROQ_API_KEY environment variable
      3. a local .env file
      4. Streamlit secrets (for Streamlit Community Cloud)

    Touching ``st.secrets`` when no secrets file exists raises in some Streamlit
    versions, so that lookup is wrapped defensively.
    """
    if override and override.strip():
        return override.strip()

    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    # .env parsed manually to avoid a hard python-dotenv dependency.
    for path in (".env", os.path.join(os.path.dirname(__file__), ".env")):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY"):
                        _, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")
                        if value:
                            return value
        except (OSError, UnicodeDecodeError):
            pass

    try:
        import streamlit as st

        return str(st.secrets.get("GROQ_API_KEY", "")).strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #


def _extract_json(text: str) -> dict[str, Any] | None:
    """Pull the first valid JSON object out of a model response."""
    if not text:
        return None

    # Strategy 1: the whole response is already clean JSON.
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Strategy 2: fenced code block, ```json ... ``` or bare ``` ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: brace matching from the first '{', respecting strings/escapes.
    start = text.find("{")
    if start != -1:
        depth, in_string, escaped = 0, False, False
        for i, ch in enumerate(text[start:], start):
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    # Strategy 4: repair trailing commas, a very common LLM slip.
    if start != -1:
        candidate = re.sub(r",(\s*[}\]])", r"\1", text[start:])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _normalise(data: dict[str, Any]) -> dict[str, Any]:
    """Guarantee every expected key exists with the right type."""
    out: dict[str, Any] = {
        "title": str(data.get("title") or "Meeting Minutes"),
        "meeting_date": str(data.get("meeting_date") or "Not stated"),
        "duration": str(data.get("duration") or "Not stated"),
        "attendees": [],
        "absentees": [],
        "executive_summary": str(data.get("executive_summary") or ""),
        "agenda_items": [],
        "discussion_points": [],
        "decisions": [],
        "action_items": [],
        "risks_and_blockers": [],
        "open_questions": [],
        "next_meeting": str(data.get("next_meeting") or "Not scheduled"),
    }

    for key in ("attendees", "absentees", "agenda_items", "open_questions"):
        value = data.get(key) or []
        if isinstance(value, str):
            value = [v.strip() for v in re.split(r"[,;\n]", value) if v.strip()]
        out[key] = [str(v).strip() for v in value if str(v).strip()]

    for block in data.get("discussion_points") or []:
        if isinstance(block, dict):
            pts = block.get("points") or []
            if isinstance(pts, str):
                pts = [pts]
            out["discussion_points"].append(
                {
                    "topic": str(block.get("topic") or "Discussion"),
                    "points": [str(p).strip() for p in pts if str(p).strip()],
                }
            )
        elif isinstance(block, str) and block.strip():
            out["discussion_points"].append({"topic": "Discussion", "points": [block.strip()]})

    for dec in data.get("decisions") or []:
        if isinstance(dec, dict):
            out["decisions"].append(
                {
                    "decision": str(dec.get("decision") or "").strip(),
                    "rationale": str(dec.get("rationale") or "").strip(),
                    "owner": str(dec.get("owner") or "Unassigned").strip(),
                }
            )
        elif isinstance(dec, str) and dec.strip():
            out["decisions"].append({"decision": dec.strip(), "rationale": "", "owner": "Unassigned"})

    valid_priorities = {"high", "medium", "low"}
    for item in data.get("action_items") or []:
        if isinstance(item, dict):
            priority = str(item.get("priority") or "Medium").strip().title()
            if priority.lower() not in valid_priorities:
                priority = "Medium"
            out["action_items"].append(
                {
                    "task": str(item.get("task") or "").strip(),
                    "owner": str(item.get("owner") or "Unassigned").strip() or "Unassigned",
                    "deadline": str(item.get("deadline") or "No deadline stated").strip(),
                    "priority": priority,
                }
            )
        elif isinstance(item, str) and item.strip():
            out["action_items"].append(
                {
                    "task": item.strip(),
                    "owner": "Unassigned",
                    "deadline": "No deadline stated",
                    "priority": "Medium",
                }
            )

    for risk in data.get("risks_and_blockers") or []:
        if isinstance(risk, dict):
            out["risks_and_blockers"].append(
                {
                    "item": str(risk.get("item") or "").strip(),
                    "impact": str(risk.get("impact") or "").strip(),
                    "owner": str(risk.get("owner") or "Unassigned").strip(),
                }
            )
        elif isinstance(risk, str) and risk.strip():
            out["risks_and_blockers"].append({"item": risk.strip(), "impact": "", "owner": "Unassigned"})

    # Drop entries whose primary field ended up empty.
    out["decisions"] = [d for d in out["decisions"] if d["decision"]]
    out["action_items"] = [a for a in out["action_items"] if a["task"]]
    out["risks_and_blockers"] = [r for r in out["risks_and_blockers"] if r["item"]]
    out["discussion_points"] = [d for d in out["discussion_points"] if d["points"]]

    return out


# --------------------------------------------------------------------------- #
# Groq call
# --------------------------------------------------------------------------- #


def _call_groq(
    api_key: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
    json_mode: bool = True,
) -> str:
    """Single chat completion. Raises on failure; caller decides what to do."""
    from groq import Groq

    client = Groq(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_completion_tokens": 8000,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        # Some models reject response_format; retry once without it.
        if json_mode and "response_format" in str(exc).lower():
            kwargs.pop("response_format", None)
            response = client.chat.completions.create(**kwargs)
        else:
            raise

    return response.choices[0].message.content or ""


def _chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split on paragraph boundaries so speaker turns stay intact."""
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for para in paragraphs:
        if length + len(para) > size and current:
            chunks.append("\n".join(current))
            current, length = [para], len(para)
        else:
            current.append(para)
            length += len(para) + 1

    if current:
        chunks.append("\n".join(current))
    return chunks or [text]


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def generate_minutes(
    transcript: str,
    meeting_type: str = prompts.DEFAULT_MEETING_TYPE,
    detail_level: str = prompts.DEFAULT_DETAIL_LEVEL,
    meeting_title: str = "",
    meeting_date: str = "",
    known_attendees: str = "",
    api_key_override: str = "",
    model: str = DEFAULT_MODEL,
) -> MinutesResult:
    """Convert a raw transcript into structured minutes."""
    import time

    started = time.time()
    warnings: list[str] = []

    if not transcript or not transcript.strip():
        return MinutesResult(data={}, mode="error", error="Transcript is empty.")

    api_key = get_api_key(api_key_override)

    if not api_key:
        data = offline_minutes(transcript, meeting_title, meeting_date)
        return MinutesResult(
            data=data,
            mode="offline",
            elapsed=time.time() - started,
            warnings=["No API key found — using the offline rule-based generator."],
        )

    working = transcript.strip()
    chunked = False

    # Long transcripts: condense segment by segment, then extract once.
    if len(working) > MAX_TRANSCRIPT_CHARS:
        chunked = True
        chunks = _chunk_text(working)
        warnings.append(
            f"Transcript is long ({len(working):,} chars) — condensed in "
            f"{len(chunks)} passes before extraction."
        )
        condensed: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            sys_p, usr_p = prompts.build_chunk_summary_prompt(chunk, i, len(chunks))
            try:
                condensed.append(_call_groq(api_key, model, sys_p, usr_p, 0.2, json_mode=False))
            except Exception as exc:
                return MinutesResult(
                    data=offline_minutes(transcript, meeting_title, meeting_date),
                    mode="error",
                    model=model,
                    error=f"Failed while condensing segment {i}: {exc}",
                    elapsed=time.time() - started,
                    warnings=warnings,
                )
        working = "\n\n".join(condensed)

    system, user = prompts.build_minutes_prompt(
        working, meeting_type, detail_level, meeting_title, meeting_date, known_attendees
    )

    try:
        raw = _call_groq(api_key, model, system, user)
    except Exception as exc:
        message = str(exc)
        if "decommissioned" in message.lower() or "model_not_found" in message.lower():
            message = (
                f"The model '{model}' is no longer available on Groq. "
                "Pick a different model in the sidebar."
            )
        elif "invalid_api_key" in message.lower() or "401" in message:
            message = "Groq rejected the API key. Check that it is correct and active."
        elif "rate" in message.lower() and "limit" in message.lower():
            message = "Groq rate limit hit. Wait a few seconds and try again."
        return MinutesResult(
            data=offline_minutes(transcript, meeting_title, meeting_date),
            mode="error",
            model=model,
            error=message,
            elapsed=time.time() - started,
            warnings=warnings,
        )

    parsed = _extract_json(raw)
    if parsed is None:
        return MinutesResult(
            data=offline_minutes(transcript, meeting_title, meeting_date),
            mode="error",
            model=model,
            error="The model did not return valid JSON. Try again or switch models.",
            raw=raw[:2000],
            elapsed=time.time() - started,
            warnings=warnings,
        )

    return MinutesResult(
        data=_normalise(parsed),
        mode="live",
        model=model,
        raw=raw,
        elapsed=time.time() - started,
        chunked=chunked,
        warnings=warnings,
    )


def refine_minutes(
    current: dict[str, Any],
    instruction: str,
    api_key_override: str = "",
    model: str = DEFAULT_MODEL,
) -> MinutesResult:
    """Apply a revision instruction to already-generated minutes."""
    import time

    started = time.time()
    api_key = get_api_key(api_key_override)

    if not api_key:
        return MinutesResult(
            data=current,
            mode="offline",
            error="Refinement needs an API key — offline mode cannot revise.",
        )

    system, user = prompts.build_refine_prompt(json.dumps(current, indent=2), instruction)

    try:
        raw = _call_groq(api_key, model, system, user, temperature=0.3)
    except Exception as exc:
        return MinutesResult(data=current, mode="error", model=model, error=str(exc))

    parsed = _extract_json(raw)
    if parsed is None:
        return MinutesResult(
            data=current,
            mode="error",
            model=model,
            error="Refinement returned invalid JSON — original minutes kept.",
        )

    return MinutesResult(
        data=_normalise(parsed), mode="live", model=model, elapsed=time.time() - started
    )


# --------------------------------------------------------------------------- #
# Offline fallback
# --------------------------------------------------------------------------- #

_ACTION_CUES = re.compile(
    r"\b(will|shall|to do|action|assign|responsible|take care of|follow up|"
    r"send|prepare|draft|review|complete|finish|deliver|submit|schedule|"
    r"organis|organiz|set up|create|update|fix|check|contact|email|call)\b",
    re.IGNORECASE,
)
_DECISION_CUES = re.compile(
    r"\b(decided|decision|agreed|agreement|approved|resolved|concluded|"
    r"we will go with|final|settled on|confirmed|sign off|signed off)\b",
    re.IGNORECASE,
)
_RISK_CUES = re.compile(
    r"\b(risk|blocker|blocked|issue|problem|concern|delay|challenge|bottleneck|"
    r"stuck|waiting on|dependency|short(-| )staffed|over budget)\b",
    re.IGNORECASE,
)
_QUESTION_CUES = re.compile(r"\?\s*$")
_DATE_CUES = re.compile(
    r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"next week|this week|end of (the )?(week|month|quarter)|eod|eow|"
    r"\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}|"
    r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?)\b",
    re.IGNORECASE,
)
_SPEAKER = re.compile(r"^\s*([A-Z][A-Za-z.'-]{1,20}(?:\s+[A-Z][A-Za-z.'-]{1,20})?)\s*[:\-–]\s*(.+)$")

# Header labels that look like "Name:" but are not speakers.
_NON_SPEAKER_LABELS = {
    "note", "notes", "agenda", "action", "actions", "topic", "topics",
    "present", "attendees", "attending", "apologies", "absent", "absentees",
    "date", "time", "duration", "location", "venue", "chair", "chairperson",
    "minutes", "subject", "meeting", "summary", "decision", "decisions",
    "next steps", "next meeting", "attendee", "participants", "invited",
}


def offline_minutes(transcript: str, title: str = "", date: str = "") -> dict[str, Any]:
    """
    Rule-based extraction used when no API key is available.

    Deliberately transparent about being heuristic — it exists so the UX can be
    demonstrated without network access or API spend, not to rival the model.
    """
    # Transcripts are often hard-wrapped mid-sentence. Re-join continuation
    # lines so a single utterance is not split into several fragments.
    raw_lines = [ln.rstrip() for ln in transcript.splitlines()]
    lines: list[str] = []
    for raw in raw_lines:
        stripped = raw.strip()
        if not stripped:
            continue
        is_new = bool(_SPEAKER.match(stripped)) or not lines
        # A line starting lowercase (or mid-sentence) continues the previous one.
        if not is_new and lines and not stripped[0].isupper() and not stripped[0].isdigit():
            lines[-1] = f"{lines[-1]} {stripped}"
        elif not is_new and lines and not lines[-1].rstrip().endswith((".", "!", "?", ":", ";")):
            lines[-1] = f"{lines[-1]} {stripped}"
        else:
            lines.append(stripped)

    speakers: list[str] = []
    absentees: list[str] = []
    utterances: list[tuple[str, str]] = []

    def _split_names(blob: str) -> list[str]:
        """Pull names out of a 'Present: A, B (role), C' style header line."""
        found = []
        for part in re.split(r"[,;]| and ", blob):
            # Drop parenthetical roles, e.g. "Priya Menon (PM)".
            part = re.sub(r"\([^)]*\)", "", part).strip(" .")
            if 1 < len(part) <= 40 and re.match(r"^[A-Z][A-Za-z.'\- ]+$", part):
                found.append(part)
        return found

    for line in lines:
        match = _SPEAKER.match(line)
        if match:
            name, said = match.group(1).strip(), match.group(2).strip()
            label = name.lower()

            if label in {"present", "attendees", "attending", "participants"}:
                for person in _split_names(said):
                    if person not in speakers:
                        speakers.append(person)
                continue

            if label in {"apologies", "absent", "absentees"}:
                absentees.extend(p for p in _split_names(said) if p not in absentees)
                continue

            if label not in _NON_SPEAKER_LABELS:
                if name not in speakers:
                    speakers.append(name)
                utterances.append((name, said))
                continue

        utterances.append(("", line))

    sentences: list[tuple[str, str]] = []
    for speaker, text in utterances:
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if len(sentence) > 12:
                sentences.append((speaker, sentence))

    decisions, actions, risks, questions, general = [], [], [], [], []

    for speaker, sentence in sentences:
        if _QUESTION_CUES.search(sentence):
            questions.append(sentence)
        elif _DECISION_CUES.search(sentence):
            decisions.append({"decision": sentence, "rationale": "", "owner": speaker or "Unassigned"})
        elif _RISK_CUES.search(sentence):
            risks.append({"item": sentence, "impact": "", "owner": speaker or "Unassigned"})
        elif _ACTION_CUES.search(sentence):
            date_match = _DATE_CUES.search(sentence)
            owner = speaker or "Unassigned"
            for name in speakers:
                if re.search(rf"\b{re.escape(name)}\b", sentence):
                    owner = name
                    break
            actions.append(
                {
                    "task": sentence,
                    "owner": owner,
                    "deadline": date_match.group(0) if date_match else "No deadline stated",
                    "priority": "High" if date_match else "Medium",
                }
            )
        else:
            general.append((speaker, sentence))

    # Group leftover discussion into readable blocks.
    discussion: list[dict[str, Any]] = []
    if general:
        per_block = max(3, len(general) // 3 or 1)
        for i in range(0, len(general), per_block):
            block = general[i : i + per_block]
            discussion.append(
                {
                    "topic": f"Discussion (part {len(discussion) + 1})",
                    "points": [f"{sp}: {tx}" if sp else tx for sp, tx in block],
                }
            )

    # A header may list "Priya Menon" while the body says "Priya:" — keep the
    # fuller name and drop the bare first name.
    deduped: list[str] = []
    for name in speakers:
        if any(other != name and name in other.split() for other in speakers):
            continue
        if name not in deduped:
            deduped.append(name)
    speakers = deduped

    word_count = len(transcript.split())
    summary = (
        f"This meeting involved {len(speakers) or 'several'} participant"
        f"{'s' if len(speakers) != 1 else ''} across approximately {word_count:,} words "
        f"of discussion. The notes contain {len(decisions)} apparent decision"
        f"{'s' if len(decisions) != 1 else ''}, {len(actions)} action item"
        f"{'s' if len(actions) != 1 else ''}, and {len(risks)} risk or blocker"
        f"{'s' if len(risks) != 1 else ''}. "
        "This summary was produced by the offline keyword-based extractor; "
        "configure a Groq API key for a genuine AI-generated summary."
    )

    detected_date = date.strip()
    if not detected_date:
        found = _DATE_CUES.search(transcript[:600])
        detected_date = found.group(0) if found else "Not stated"

    return {
        "title": title.strip() or "Meeting Minutes (Offline Draft)",
        "meeting_date": detected_date,
        "duration": "Not stated",
        "attendees": speakers,
        "absentees": absentees,
        "executive_summary": summary,
        "agenda_items": [],
        "discussion_points": discussion,
        "decisions": decisions[:12],
        "action_items": actions[:20],
        "risks_and_blockers": risks[:10],
        "open_questions": questions[:10],
        "next_meeting": "Not scheduled",
    }


def health_check(api_key_override: str = "", model: str = DEFAULT_MODEL) -> tuple[bool, str]:
    """Cheap round-trip so the user can prove the API path really works."""
    api_key = get_api_key(api_key_override)
    if not api_key:
        return False, "No API key found in sidebar, environment, .env, or secrets."
    try:
        reply = _call_groq(
            api_key, model, "Reply with exactly: OK", "Health check.", 0.0, json_mode=False
        )
        return True, f"Connected to {model}. Response: {reply.strip()[:60]}"
    except Exception as exc:
        return False, str(exc)
