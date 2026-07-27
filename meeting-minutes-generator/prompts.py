"""
prompts.py
==========
Prompt-engineering layer for the AI Meeting Minutes Generator.

Everything the LLM is ever asked to do lives in this file, so every "AI
capability" in the app is traceable to a specific, inspectable prompt.

Design notes (useful for a viva walkthrough):

* The agent is asked to return **strict JSON**, not prose. Structured output
  is what makes downstream rendering, filtering and export possible — it turns
  a summarisation task into an *information extraction* task.
* A JSON Schema is embedded in the system prompt so the model knows the exact
  shape expected, including which fields may be empty.
* Anti-hallucination rules are explicit: the model may only report what is
  present in the transcript, and must use the sentinel "Unassigned" /
  "No deadline stated" rather than inventing owners or dates.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Meeting types — each nudges the model toward the vocabulary and the
# information that actually matters for that kind of meeting.
# --------------------------------------------------------------------------- #

MEETING_TYPES: dict[str, dict[str, str]] = {
    "general": {
        "label": "General / Team Meeting",
        "icon": "people",
        "description": "A standard team or departmental meeting.",
        "focus": (
            "Capture the broad agenda, what each participant contributed, and "
            "any cross-team dependencies that were raised."
        ),
    },
    "standup": {
        "label": "Daily Stand-up",
        "icon": "sunrise",
        "description": "Short daily sync: progress, plans, blockers.",
        "focus": (
            "Emphasise per-person progress, today's plan, and especially "
            "BLOCKERS. Blockers should appear as risks. Keep the summary very "
            "short — stand-ups rarely contain formal decisions."
        ),
    },
    "project_review": {
        "label": "Project / Sprint Review",
        "icon": "kanban",
        "description": "Milestone, sprint or project status review.",
        "focus": (
            "Emphasise milestone status, scope changes, slipped dates, and "
            "explicit go/no-go decisions. Deadlines matter a great deal here."
        ),
    },
    "client": {
        "label": "Client / Stakeholder Call",
        "icon": "briefcase",
        "description": "External client or stakeholder discussion.",
        "focus": (
            "Emphasise client requests, commitments made to the client, "
            "pricing or contractual points, and follow-ups the client is "
            "waiting on. Be precise about who promised what."
        ),
    },
    "brainstorm": {
        "label": "Brainstorming Session",
        "icon": "lightbulb",
        "description": "Idea generation and exploratory discussion.",
        "focus": (
            "Capture the ideas proposed and which were favoured or discarded "
            "and why. Many ideas will NOT be decisions — do not promote a "
            "suggestion to a decision unless the group clearly agreed."
        ),
    },
    "board": {
        "label": "Board / Formal Meeting",
        "icon": "bank",
        "description": "Formal governance meeting with resolutions.",
        "focus": (
            "Use formal minute-taking language. Record motions, who proposed "
            "and seconded them, and the outcome of any vote. Precision and "
            "neutrality are essential."
        ),
    },
    "interview": {
        "label": "Interview / 1-on-1",
        "icon": "person-video2",
        "description": "Interview, appraisal or one-to-one conversation.",
        "focus": (
            "Capture topics covered, feedback given in both directions, and "
            "agreed next steps. Keep evaluative language factual and neutral."
        ),
    },
}

DEFAULT_MEETING_TYPE = "general"


# --------------------------------------------------------------------------- #
# Output detail levels
# --------------------------------------------------------------------------- #

DETAIL_LEVELS: dict[str, dict[str, str]] = {
    "concise": {
        "label": "Concise",
        "icon": "lightning-charge",
        "description": "Tight bullets. Best for quick circulation.",
        "guide": (
            "Be brief. The executive summary is 2-3 sentences. Each discussion "
            "point gets at most 2 short bullets. Merge closely related points."
        ),
    },
    "standard": {
        "label": "Standard",
        "icon": "file-text",
        "description": "Balanced detail — the usual choice.",
        "guide": (
            "The executive summary is 3-5 sentences. Each discussion point "
            "gets 2-4 bullets carrying the substance of what was said."
        ),
    },
    "detailed": {
        "label": "Detailed",
        "icon": "journal-richtext",
        "description": "Thorough minutes for formal records.",
        "guide": (
            "The executive summary is 5-8 sentences. Each discussion point "
            "gets 3-6 bullets. Preserve nuance, dissenting views, and the "
            "reasoning behind conclusions. Attribute points to speakers where "
            "the transcript makes the speaker clear."
        ),
    },
}

DEFAULT_DETAIL_LEVEL = "standard"


# --------------------------------------------------------------------------- #
# The JSON contract
# --------------------------------------------------------------------------- #

OUTPUT_SCHEMA = """{
  "title": "string - a short descriptive title for the meeting",
  "meeting_date": "string - date if stated in the transcript, else \\"Not stated\\"",
  "duration": "string - duration if stated, else \\"Not stated\\"",
  "attendees": ["string - names or roles of people present"],
  "absentees": ["string - anyone explicitly noted as absent; [] if none"],
  "executive_summary": "string - a flowing paragraph summarising the meeting",
  "agenda_items": ["string - agenda topics, if an agenda is discernible"],
  "discussion_points": [
    {
      "topic": "string - short topic heading",
      "points": ["string - the substance of what was discussed"]
    }
  ],
  "decisions": [
    {
      "decision": "string - what was decided, stated plainly",
      "rationale": "string - why, if given, else \\"\\"",
      "owner": "string - who is accountable, else \\"Unassigned\\""
    }
  ],
  "action_items": [
    {
      "task": "string - the action, phrased as an imperative",
      "owner": "string - person responsible, else \\"Unassigned\\"",
      "deadline": "string - as stated, e.g. \\"Friday\\", \\"15 March\\", else \\"No deadline stated\\"",
      "priority": "string - one of: High, Medium, Low"
    }
  ],
  "risks_and_blockers": [
    {
      "item": "string - the risk, issue or blocker",
      "impact": "string - the consequence, else \\"\\"",
      "owner": "string - who is handling it, else \\"Unassigned\\""
    }
  ],
  "open_questions": ["string - questions raised but left unresolved"],
  "next_meeting": "string - date/time/purpose if mentioned, else \\"Not scheduled\\""
}"""


BASE_SYSTEM_PROMPT = f"""You are "Scribe", a meticulous professional minute-taker \
with years of experience producing board-grade meeting records.

Your task is to read a raw, messy meeting transcript or set of notes and convert \
it into structured, accurate minutes.

## CRITICAL RULES

1. **Never fabricate.** Report only what is present in the transcript. If a \
detail is absent, use the specified fallback value. Do not guess at names, \
dates, numbers, or commitments that were not stated.
2. **Distinguish discussion from decision.** A suggestion, proposal, or opinion \
is NOT a decision. Only record something under "decisions" if the group \
clearly settled on it.
3. **Distinguish decision from action.** A decision is a conclusion reached. An \
action item is concrete work someone must now do. "We will move to the new \
vendor" is a decision; "Priya to draft the vendor contract by Friday" is an \
action item.
4. **Attribute carefully.** Assign an owner only when the transcript makes it \
clear. Otherwise use "Unassigned" — an honest gap is far more useful to a \
reader than a wrong name.
5. **Infer priority sensibly.** Base it on stated urgency, proximity of the \
deadline, and whether others are blocked by it. Default to "Medium" when there \
is no signal.
6. **Clean up speech, preserve meaning.** Remove filler ("um", "you know", \
false starts) and repetition. Never remove substance, and never editorialise.
7. **Empty arrays are correct.** If the meeting produced no decisions, return \
an empty array. Do not pad the output to look thorough.

## OUTPUT FORMAT

Return ONLY a single valid JSON object matching this schema exactly. No \
markdown code fences, no commentary before or after, no explanation.

{OUTPUT_SCHEMA}
"""


# --------------------------------------------------------------------------- #
# Prompt builders
# --------------------------------------------------------------------------- #


def build_minutes_prompt(
    transcript: str,
    meeting_type: str = DEFAULT_MEETING_TYPE,
    detail_level: str = DEFAULT_DETAIL_LEVEL,
    meeting_title: str = "",
    meeting_date: str = "",
    known_attendees: str = "",
) -> tuple[str, str]:
    """Build the (system, user) prompt pair for the main extraction pass."""
    mtype = MEETING_TYPES.get(meeting_type, MEETING_TYPES[DEFAULT_MEETING_TYPE])
    detail = DETAIL_LEVELS.get(detail_level, DETAIL_LEVELS[DEFAULT_DETAIL_LEVEL])

    system = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"## MEETING TYPE: {mtype['label']}\n{mtype['focus']}\n\n"
        f"## DETAIL LEVEL: {detail['label']}\n{detail['guide']}"
    )

    hints: list[str] = []
    if meeting_title.strip():
        hints.append(f"The meeting is titled: {meeting_title.strip()}")
    if meeting_date.strip():
        hints.append(f"The meeting date is: {meeting_date.strip()}")
    if known_attendees.strip():
        hints.append(
            "Known attendees (use these spellings; add anyone else you find "
            f"in the transcript): {known_attendees.strip()}"
        )

    hint_block = ("\n\nCONTEXT PROVIDED BY THE USER:\n" + "\n".join(f"- {h}" for h in hints)) if hints else ""

    user = (
        "Produce structured minutes for the following meeting."
        f"{hint_block}\n\n"
        "--- BEGIN TRANSCRIPT ---\n"
        f"{transcript.strip()}\n"
        "--- END TRANSCRIPT ---\n\n"
        "Return only the JSON object."
    )
    return system, user


def build_refine_prompt(current_json: str, instruction: str) -> tuple[str, str]:
    """Build a prompt that revises already-generated minutes."""
    system = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        "## REVISION MODE\n"
        "You are revising minutes you produced earlier. Apply the user's "
        "instruction and leave everything else byte-for-byte unchanged. Do not "
        "introduce information that was not in the original minutes. Return the "
        "complete revised JSON object, not a diff or a fragment."
    )
    user = (
        "Here are the current minutes:\n\n"
        f"{current_json}\n\n"
        f"REVISION INSTRUCTION: {instruction}\n\n"
        "Return only the full revised JSON object."
    )
    return system, user


# Canned one-click refinements exposed as buttons in the UI.
REFINEMENT_ACTIONS: dict[str, dict[str, str]] = {
    "shorten": {
        "label": "Make Concise",
        "icon": "arrows-collapse",
        "instruction": (
            "Condense the executive summary and trim every discussion bullet to "
            "its essential meaning. Do not delete any decision, action item, or "
            "risk — only compress the wording."
        ),
    },
    "expand": {
        "label": "Add Detail",
        "icon": "arrows-expand",
        "instruction": (
            "Expand the executive summary and discussion points using detail "
            "already present in the minutes. Do not invent new facts."
        ),
    },
    "formalise": {
        "label": "More Formal",
        "icon": "bank",
        "instruction": (
            "Rewrite all prose in formal, third-person minute-taking register "
            "suitable for a board record. Avoid contractions and casual phrasing."
        ),
    },
    "actions": {
        "label": "Sharpen Actions",
        "icon": "check2-square",
        "instruction": (
            "Review every action item. Rephrase each as a clear imperative "
            "starting with a verb, and re-examine the priority assignments for "
            "consistency. Do not add or remove action items."
        ),
    },
}


# --------------------------------------------------------------------------- #
# Chunking for long transcripts
# --------------------------------------------------------------------------- #


def build_chunk_summary_prompt(chunk: str, index: int, total: int) -> tuple[str, str]:
    """Prompt for condensing one slice of an over-long transcript."""
    system = (
        "You are a meeting note condenser. You will be given ONE SEGMENT of a "
        "longer meeting transcript. Condense it while preserving every name, "
        "decision, commitment, number, date and blocker. Remove only filler and "
        "repetition. Output plain prose and bullets — no JSON, no preamble. "
        "This output will later be combined with other segments, so do not add "
        "conclusions of your own."
    )
    user = (
        f"Segment {index} of {total}:\n\n"
        "--- BEGIN SEGMENT ---\n"
        f"{chunk.strip()}\n"
        "--- END SEGMENT ---"
    )
    return system, user
