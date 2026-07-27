"""
llm.py
======
Groq API client wrapper + offline template-based fallback planner.

Mirrors the reliability approach used across this repo:

* ``PlanResult.mode`` is one of "live" / "offline" / "error" so the UI can show
  three distinct badges. A failed API call can never be mistaken for
  "no key configured".
* ``_extract_json`` recovers JSON from fenced blocks, reasoning preambles and
  trailing-comma slips before giving up.
* ``_normalise`` guarantees every field exists with the right type, so the UI
  and the exporters never crash on a malformed response.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import prompts

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# llama-3.3-70b-versatile and llama-3.1-8b-instant are decommissioned by Groq
# on 2026-08-16 and are deliberately not offered.
AVAILABLE_MODELS: dict[str, str] = {
    "openai/gpt-oss-120b": "GPT-OSS 120B — best quality (recommended)",
    "openai/gpt-oss-20b": "GPT-OSS 20B — faster, lighter",
    "qwen/qwen3.6-27b": "Qwen 3.6 27B — alternative",
    "moonshotai/kimi-k2-instruct-0905": "Kimi K2 — long context",
}

DEFAULT_MODEL = "openai/gpt-oss-120b"

CURRENCIES = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "AED": "AED ",
    "SGD": "S$",
}


@dataclass
class PlanResult:
    """Everything the UI needs to render one generation attempt."""

    data: dict[str, Any]
    mode: str = "live"           # "live" | "offline" | "error"
    model: str = ""
    error: str = ""
    raw: str = ""
    elapsed: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.data) and self.mode != "error"


# --------------------------------------------------------------------------- #
# API key discovery
# --------------------------------------------------------------------------- #


def get_api_key(override: str = "") -> str:
    """Resolve the Groq key from sidebar → env → .env → st.secrets."""
    if override and override.strip():
        return override.strip()

    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

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

    # Touching st.secrets with no secrets file raises in some versions.
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

    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

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

    if start != -1:
        candidate = re.sub(r",(\s*[}\]])", r"\1", text[start:])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[\n;]", value) if v.strip()]
    return [value]


def _as_int(value, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    try:
        cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch == "-")
        return int(cleaned) if cleaned not in ("", "-") else default
    except ValueError:
        return default


def _normalise(data: dict[str, Any]) -> dict[str, Any]:
    """Guarantee every expected key exists with the right type."""
    priorities = {"high", "medium", "low"}
    allowed_phases = set(prompts.CHECKLIST_PHASES)

    out: dict[str, Any] = {
        "event_title": str(data.get("event_title") or "Event Plan"),
        "summary": str(data.get("summary") or ""),
        "venue": {"recommendations": [], "layout": "", "requirements": []},
        "budget_items": [],
        "checklist": [],
        "equipment": [],
        "invitations": {
            "channels": [],
            "send_schedule": "",
            "guest_segments": [],
            "rsvp_method": "",
            "sample_message": "",
        },
        "timeline": [],
        "day_schedule": [],
        "risks": [],
        "tips": [],
    }

    # ---- venue ----
    venue = data.get("venue")
    if isinstance(venue, dict):
        out["venue"]["layout"] = str(venue.get("layout") or "")
        out["venue"]["requirements"] = [str(r).strip() for r in _as_list(venue.get("requirements")) if str(r).strip()]
        for rec in _as_list(venue.get("recommendations")):
            if isinstance(rec, dict):
                option = str(rec.get("option") or "").strip()
                if option:
                    out["venue"]["recommendations"].append(
                        {
                            "option": option,
                            "why": str(rec.get("why") or "").strip(),
                            "capacity_fit": str(rec.get("capacity_fit") or "").strip(),
                            "est_cost": rec.get("est_cost", 0),
                        }
                    )
            elif isinstance(rec, str) and rec.strip():
                out["venue"]["recommendations"].append(
                    {"option": rec.strip(), "why": "", "capacity_fit": "", "est_cost": 0}
                )

    # ---- budget (kept raw; budget.py does the maths) ----
    for item in _as_list(data.get("budget_items")):
        if isinstance(item, dict) and str(item.get("item") or "").strip():
            out["budget_items"].append(item)

    # ---- checklist ----
    for task in _as_list(data.get("checklist")):
        if isinstance(task, dict):
            text = str(task.get("task") or "").strip()
            if not text:
                continue
            phase = str(task.get("phase") or "").strip()
            if phase not in allowed_phases:
                match = next((p for p in allowed_phases if p.lower() == phase.lower()), None)
                phase = match or "Planning & Approvals"
            priority = str(task.get("priority") or "Medium").strip().title()
            if priority.lower() not in priorities:
                priority = "Medium"
            out["checklist"].append(
                {
                    "phase": phase,
                    "task": text,
                    "owner_role": str(task.get("owner_role") or "Organiser").strip() or "Organiser",
                    "days_before_event": _as_int(task.get("days_before_event"), 7),
                    "priority": priority,
                }
            )
        elif isinstance(task, str) and task.strip():
            out["checklist"].append(
                {
                    "phase": "Planning & Approvals",
                    "task": task.strip(),
                    "owner_role": "Organiser",
                    "days_before_event": 7,
                    "priority": "Medium",
                }
            )

    # ---- equipment ----
    for eq in _as_list(data.get("equipment")):
        if isinstance(eq, dict):
            name = str(eq.get("item") or "").strip()
            if name:
                out["equipment"].append(
                    {
                        "item": name,
                        "quantity": str(eq.get("quantity") or "1").strip(),
                        "essential": bool(eq.get("essential", True)),
                        "notes": str(eq.get("notes") or "").strip(),
                    }
                )
        elif isinstance(eq, str) and eq.strip():
            out["equipment"].append(
                {"item": eq.strip(), "quantity": "1", "essential": True, "notes": ""}
            )

    # ---- invitations ----
    inv = data.get("invitations")
    if isinstance(inv, dict):
        out["invitations"]["channels"] = [str(c).strip() for c in _as_list(inv.get("channels")) if str(c).strip()]
        out["invitations"]["send_schedule"] = str(inv.get("send_schedule") or "")
        out["invitations"]["rsvp_method"] = str(inv.get("rsvp_method") or "")
        out["invitations"]["sample_message"] = str(inv.get("sample_message") or "")
        for seg in _as_list(inv.get("guest_segments")):
            if isinstance(seg, dict) and str(seg.get("segment") or "").strip():
                out["invitations"]["guest_segments"].append(
                    {
                        "segment": str(seg["segment"]).strip(),
                        "count": _as_int(seg.get("count"), 0),
                        "approach": str(seg.get("approach") or "").strip(),
                    }
                )

    # ---- timeline ----
    for ms in _as_list(data.get("timeline")):
        if isinstance(ms, dict) and str(ms.get("milestone") or "").strip():
            out["timeline"].append(
                {
                    "milestone": str(ms["milestone"]).strip(),
                    "days_before_event": _as_int(ms.get("days_before_event"), 7),
                    "detail": str(ms.get("detail") or "").strip(),
                }
            )
    out["timeline"].sort(key=lambda m: -m["days_before_event"])

    # ---- day schedule ----
    for slot in _as_list(data.get("day_schedule")):
        if isinstance(slot, dict) and str(slot.get("activity") or "").strip():
            out["day_schedule"].append(
                {
                    "time": str(slot.get("time") or "").strip(),
                    "activity": str(slot["activity"]).strip(),
                    "owner": str(slot.get("owner") or "").strip(),
                }
            )

    # ---- risks ----
    for risk in _as_list(data.get("risks")):
        if isinstance(risk, dict) and str(risk.get("risk") or "").strip():
            likelihood = str(risk.get("likelihood") or "Medium").strip().title()
            if likelihood.lower() not in priorities:
                likelihood = "Medium"
            out["risks"].append(
                {
                    "risk": str(risk["risk"]).strip(),
                    "likelihood": likelihood,
                    "mitigation": str(risk.get("mitigation") or "").strip(),
                }
            )
        elif isinstance(risk, str) and risk.strip():
            out["risks"].append({"risk": risk.strip(), "likelihood": "Medium", "mitigation": ""})

    out["tips"] = [str(t).strip() for t in _as_list(data.get("tips")) if str(t).strip()]

    # Sort the checklist by phase order, then by urgency.
    phase_order = {p: i for i, p in enumerate(prompts.CHECKLIST_PHASES)}
    out["checklist"].sort(
        key=lambda t: (phase_order.get(t["phase"], 99), -t["days_before_event"])
    )

    return out


# --------------------------------------------------------------------------- #
# Groq call
# --------------------------------------------------------------------------- #


def _call_groq(
    api_key: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.4,
    json_mode: bool = True,
) -> str:
    from groq import Groq

    client = Groq(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_completion_tokens": 10000,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        if json_mode and "response_format" in str(exc).lower():
            kwargs.pop("response_format", None)
            response = client.chat.completions.create(**kwargs)
        else:
            raise

    return response.choices[0].message.content or ""


def _friendly_error(exc: Exception, model: str) -> str:
    message = str(exc)
    lowered = message.lower()
    if "decommissioned" in lowered or "model_not_found" in lowered:
        return (
            f"The model '{model}' is no longer available on Groq. "
            "Pick a different model in the sidebar."
        )
    if "invalid_api_key" in lowered or "401" in message:
        return "Groq rejected the API key. Check that it is correct and active."
    if "rate" in lowered and "limit" in lowered:
        return "Groq rate limit hit. Wait a few seconds and try again."
    if "timeout" in lowered:
        return "The request timed out. Try again, or switch to a smaller model."
    return message


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def generate_plan(
    event_type: str,
    event_name: str,
    attendees: int,
    budget: float,
    currency: str,
    location: str,
    event_date: str,
    duration: str,
    notes: str,
    formality: str = "Semi-formal",
    api_key_override: str = "",
    model: str = DEFAULT_MODEL,
) -> PlanResult:
    """Generate a complete event plan."""
    started = time.time()
    api_key = get_api_key(api_key_override)

    if not api_key:
        return PlanResult(
            data=offline_plan(event_type, event_name, attendees, budget, currency, location),
            mode="offline",
            elapsed=time.time() - started,
            warnings=["No API key found — using the offline template planner."],
        )

    system, user = prompts.build_plan_prompt(
        event_type, event_name, attendees, budget, currency,
        location, event_date, duration, notes, formality,
    )

    try:
        raw = _call_groq(api_key, model, system, user)
    except Exception as exc:
        return PlanResult(
            data=offline_plan(event_type, event_name, attendees, budget, currency, location),
            mode="error",
            model=model,
            error=_friendly_error(exc, model),
            elapsed=time.time() - started,
        )

    parsed = _extract_json(raw)
    if parsed is None:
        return PlanResult(
            data=offline_plan(event_type, event_name, attendees, budget, currency, location),
            mode="error",
            model=model,
            error="The model did not return valid JSON. Try again or switch models.",
            raw=raw[:2000],
            elapsed=time.time() - started,
        )

    return PlanResult(
        data=_normalise(parsed),
        mode="live",
        model=model,
        raw=raw,
        elapsed=time.time() - started,
    )


def refine_plan(
    current: dict[str, Any],
    instruction: str,
    api_key_override: str = "",
    model: str = DEFAULT_MODEL,
) -> PlanResult:
    """Apply a revision instruction to an existing plan."""
    started = time.time()
    api_key = get_api_key(api_key_override)

    if not api_key:
        return PlanResult(
            data=current,
            mode="offline",
            error="Refinement needs an API key — offline mode cannot revise.",
        )

    system, user = prompts.build_refine_prompt(json.dumps(current, indent=2), instruction)

    try:
        raw = _call_groq(api_key, model, system, user)
    except Exception as exc:
        return PlanResult(data=current, mode="error", model=model, error=_friendly_error(exc, model))

    parsed = _extract_json(raw)
    if parsed is None:
        return PlanResult(
            data=current,
            mode="error",
            model=model,
            error="Refinement returned invalid JSON — original plan kept.",
        )

    return PlanResult(
        data=_normalise(parsed), mode="live", model=model, elapsed=time.time() - started
    )


# --------------------------------------------------------------------------- #
# Offline fallback planner
# --------------------------------------------------------------------------- #

# Per-head unit costs in INR, scaled for other currencies by a rough divisor.
_BASE_COSTS = {
    "venue_per_head": 150,
    "catering_per_head": 350,
    "decor_per_head": 80,
    "printing_per_head": 25,
    "gift_per_head": 60,
}

_CURRENCY_DIVISOR = {"INR": 1, "USD": 70, "EUR": 75, "GBP": 85, "AED": 19, "SGD": 55}


def offline_plan(
    event_type: str,
    event_name: str,
    attendees: int,
    budget: float,
    currency: str = "INR",
    location: str = "",
) -> dict[str, Any]:
    """
    Rule-based template planner used when no API key is available.

    Deliberately transparent about being a template — it exists so the interface
    can be demonstrated without network access, not to rival the model.
    """
    etype = prompts.EVENT_TYPES.get(event_type, prompts.EVENT_TYPES[prompts.DEFAULT_EVENT_TYPE])
    band, _ = prompts.scale_for(attendees)
    div = _CURRENCY_DIVISOR.get(currency, 1)

    def cost(key: str) -> float:
        return round(_BASE_COSTS[key] / div, 2)

    title = event_name.strip() or f"{etype['label']} ({attendees} guests)"

    budget_items = [
        {
            "category": "Venue",
            "item": "Venue hire",
            "unit_cost": cost("venue_per_head") * max(attendees, 1),
            "quantity": 1,
            "unit": "lump sum",
            "notes": "Template estimate — replace with a real quote.",
        },
        {
            "category": "Catering",
            "item": "Food and beverages",
            "unit_cost": cost("catering_per_head"),
            "quantity": attendees,
            "unit": "person",
            "notes": "Assumes one full meal plus refreshments.",
        },
        {
            "category": "Decoration",
            "item": "Decoration and signage",
            "unit_cost": cost("decor_per_head"),
            "quantity": attendees,
            "unit": "person",
            "notes": "Scales loosely with venue size.",
        },
        {
            "category": "Marketing & Printing",
            "item": "Invitations and printed material",
            "unit_cost": cost("printing_per_head"),
            "quantity": attendees,
            "unit": "person",
            "notes": "Cards, badges, agenda sheets.",
        },
        {
            "category": "Equipment & AV",
            "item": "Sound system and projector rental",
            "unit_cost": round(6000 / div, 2),
            "quantity": 1,
            "unit": "day",
            "notes": "Single-day rental with an operator.",
        },
        {
            "category": "Miscellaneous",
            "item": "Buffer for unplanned expenses",
            "unit_cost": round(3000 / div, 2),
            "quantity": 1,
            "unit": "lump sum",
            "notes": "Separate from the percentage contingency.",
        },
    ]

    if event_type in {"college_fest", "hackathon", "conference"}:
        budget_items.append(
            {
                "category": "Prizes & Gifts",
                "item": "Prizes and certificates",
                "unit_cost": round(15000 / div, 2),
                "quantity": 1,
                "unit": "lump sum",
                "notes": "Winner prizes plus participation certificates.",
            }
        )
    if attendees > 300:
        budget_items.append(
            {
                "category": "Staffing & Security",
                "item": "Security personnel",
                "unit_cost": round(1200 / div, 2),
                "quantity": max(2, attendees // 150),
                "unit": "guard",
                "notes": "Roughly one guard per 150 attendees.",
            }
        )

    checklist = [
        ("Planning & Approvals", "Define the event objective and success criteria in writing", "Organiser", 45, "High"),
        ("Planning & Approvals", "Fix the date and confirm it does not clash with other events", "Organiser", 42, "High"),
        ("Planning & Approvals", "Prepare the budget and get it approved", "Finance Lead", 40, "High"),
        ("Planning & Approvals", "Obtain written permission from the authority or institution", "Organiser", 38, "High"),
        ("Booking & Procurement", "Shortlist three venues, visit each and compare quotes", "Logistics Lead", 35, "High"),
        ("Booking & Procurement", "Book the venue and pay the advance", "Logistics Lead", 30, "High"),
        ("Booking & Procurement", "Finalise the caterer and confirm the menu", "Hospitality Lead", 25, "High"),
        ("Booking & Procurement", "Book sound, projector and lighting; confirm an on-site operator", "Technical Lead", 21, "High"),
        ("Promotion & Invitations", "Prepare and proofread the invitation copy", "Publicity Lead", 20, "Medium"),
        ("Promotion & Invitations", "Send invitations to all guest segments", "Publicity Lead", 18, "High"),
        ("Promotion & Invitations", "Publish the event on social media and notice boards", "Publicity Lead", 15, "Medium"),
        ("Promotion & Invitations", "Follow up with non-responders and confirm headcount", "Publicity Lead", 8, "High"),
        ("Final Week", "Confirm final headcount with the caterer", "Hospitality Lead", 5, "High"),
        ("Final Week", "Do a full technical rehearsal at the venue", "Technical Lead", 3, "High"),
        ("Final Week", "Print badges, agendas, signage and the attendance register", "Publicity Lead", 3, "Medium"),
        ("Final Week", "Brief every volunteer on their exact role and timing", "Organiser", 2, "High"),
        ("Final Week", "Reconfirm every vendor by phone", "Logistics Lead", 1, "High"),
        ("Event Day", "Arrive early and verify the venue setup against the layout plan", "Logistics Lead", 0, "High"),
        ("Event Day", "Test all AV equipment before guests arrive", "Technical Lead", 0, "High"),
        ("Event Day", "Open the registration or welcome desk", "Hospitality Lead", 0, "High"),
        ("Event Day", "Run the event to the schedule and manage overruns", "Organiser", 0, "High"),
        ("Event Day", "Capture photographs and video for records", "Publicity Lead", 0, "Medium"),
        ("Post-Event", "Settle all vendor payments and collect receipts", "Finance Lead", -2, "High"),
        ("Post-Event", "Send thank-you messages to guests, speakers and sponsors", "Organiser", -3, "Medium"),
        ("Post-Event", "Collect feedback through a short form", "Organiser", -3, "Medium"),
        ("Post-Event", "Write a brief report with actual spend versus budget", "Finance Lead", -7, "Medium"),
    ]

    equipment = [
        {"item": "Public address system with microphones", "quantity": "1 set", "essential": True, "notes": "Include at least one spare mic."},
        {"item": "Projector and screen", "quantity": "1", "essential": True, "notes": "Carry both HDMI and VGA adapters."},
        {"item": "Extension boards and power strips", "quantity": "6+", "essential": True, "notes": "More than you think you need."},
        {"item": "Chairs and tables", "quantity": f"{attendees} chairs", "essential": True, "notes": "Confirm the venue supplies these."},
        {"item": "Registration desk with stationery", "quantity": "1", "essential": attendees > 50, "notes": "Pens, register, name list."},
        {"item": "First-aid kit", "quantity": "1", "essential": True, "notes": "Mandatory for any gathering."},
        {"item": "Signage and directional boards", "quantity": "4-6", "essential": attendees > 50, "notes": "Entry, hall, washrooms, refreshments."},
        {"item": "Backup laptop with presentations preloaded", "quantity": "1", "essential": True, "notes": "The most common day-of failure."},
    ]

    return {
        "event_title": title,
        "summary": (
            f"A template plan for a {band.lower()}-scale {etype['label'].lower()} "
            f"for approximately {attendees} attendees"
            f"{' in ' + location if location else ''}. This plan was produced by the "
            "offline rule-based planner; configure a Groq API key for a genuinely "
            "customised plan with location-appropriate costs and event-specific tasks."
        ),
        "venue": {
            "recommendations": [
                {
                    "option": "Institution auditorium or seminar hall",
                    "why": "Lowest cost, familiar to attendees, AV usually built in.",
                    "capacity_fit": f"Suitable for around {attendees} people",
                    "est_cost": cost("venue_per_head") * max(attendees, 1) * 0.5,
                },
                {
                    "option": "Banquet hall or community centre",
                    "why": "More polished setting with catering usually included.",
                    "capacity_fit": f"Comfortable for {attendees}-{int(attendees * 1.3)}",
                    "est_cost": cost("venue_per_head") * max(attendees, 1),
                },
                {
                    "option": "Open-air ground or lawn",
                    "why": "Good for large informal gatherings; weather is the risk.",
                    "capacity_fit": f"Scales well beyond {attendees}",
                    "est_cost": cost("venue_per_head") * max(attendees, 1) * 0.7,
                },
            ],
            "layout": (
                "Theatre-style seating facing the stage with a clear central aisle, "
                "a registration desk at the entrance, and refreshments positioned "
                "away from the main seating to avoid congestion."
            ),
            "requirements": [
                "Reliable power supply with a backup generator",
                "Adequate washroom facilities for the headcount",
                "Parking or clear drop-off point",
                "Wheelchair-accessible entry",
                "Permission to use sound equipment at the planned hours",
            ],
        },
        "budget_items": budget_items,
        "checklist": [
            {
                "phase": phase,
                "task": task,
                "owner_role": owner,
                "days_before_event": days,
                "priority": priority,
            }
            for phase, task, owner, days, priority in checklist
        ],
        "equipment": equipment,
        "invitations": {
            "channels": ["Email", "WhatsApp broadcast", "Printed invitation cards", "Notice board poster"],
            "send_schedule": (
                "Send the first invitation 18-20 days before the event, a reminder "
                "at 8 days, and a final confirmation message 2 days before."
            ),
            "guest_segments": [
                {"segment": "Primary invitees", "count": int(attendees * 0.7), "approach": "Direct personal invitation"},
                {"segment": "Faculty / seniors / VIPs", "count": max(5, int(attendees * 0.1)), "approach": "Formal written invitation delivered in person"},
                {"segment": "Open registrations", "count": int(attendees * 0.2), "approach": "Public form shared on social media"},
            ],
            "rsvp_method": "Google Form linked in every message, with responses tracked in a shared sheet.",
            "sample_message": (
                f"You are cordially invited to {title}. Join us for an engaging "
                "session with insightful speakers and refreshments. Your presence "
                "would make the occasion special. Kindly confirm your attendance "
                "through the registration link below so we can plan seating and "
                "catering accurately. We look forward to welcoming you."
            ),
        },
        "timeline": [
            {"milestone": "Objective and date fixed", "days_before_event": 45, "detail": "Written brief approved by the organising authority."},
            {"milestone": "Budget approved", "days_before_event": 40, "detail": "Line-item budget signed off and funds available."},
            {"milestone": "Venue confirmed", "days_before_event": 30, "detail": "Booking receipt in hand, advance paid."},
            {"milestone": "Vendors locked", "days_before_event": 21, "detail": "Catering, AV and decoration contracts confirmed."},
            {"milestone": "Invitations dispatched", "days_before_event": 18, "detail": "All segments contacted, RSVP tracking live."},
            {"milestone": "Headcount confirmed", "days_before_event": 5, "detail": "Final numbers shared with the caterer."},
            {"milestone": "Rehearsal complete", "days_before_event": 3, "detail": "Full technical run-through done at the venue."},
            {"milestone": "Event day", "days_before_event": 0, "detail": "Execute to the run-of-show."},
            {"milestone": "Settlement and report", "days_before_event": -7, "detail": "All payments cleared, feedback summarised."},
        ],
        "day_schedule": [
            {"time": "07:30", "activity": "Team arrives; venue and setup check", "owner": "Logistics Lead"},
            {"time": "08:30", "activity": "AV testing and rehearsal of opening", "owner": "Technical Lead"},
            {"time": "09:00", "activity": "Registration desk opens", "owner": "Hospitality Lead"},
            {"time": "09:45", "activity": "Guests seated; welcome address", "owner": "Organiser"},
            {"time": "10:00", "activity": "Main programme begins", "owner": "Organiser"},
            {"time": "11:30", "activity": "Refreshment break", "owner": "Hospitality Lead"},
            {"time": "11:45", "activity": "Programme resumes", "owner": "Organiser"},
            {"time": "13:00", "activity": "Vote of thanks and closing", "owner": "Organiser"},
            {"time": "13:15", "activity": "Lunch / refreshments", "owner": "Hospitality Lead"},
            {"time": "14:30", "activity": "Teardown and venue handover", "owner": "Logistics Lead"},
        ],
        "risks": [
            {"risk": "Lower attendance than expected", "likelihood": "Medium", "mitigation": "Over-invite by 20-30% and send reminders at 8 and 2 days."},
            {"risk": "AV equipment failure during the event", "likelihood": "Medium", "mitigation": "Test everything the day before; keep a backup laptop and spare mic on site."},
            {"risk": "Key speaker or chief guest cancels late", "likelihood": "Low", "mitigation": "Identify a standby speaker and reconfirm 48 hours in advance."},
            {"risk": "Catering quantity or quality shortfall", "likelihood": "Medium", "mitigation": "Order for 10% above the confirmed headcount and do a tasting beforehand."},
            {"risk": "Budget overrun on unplanned items", "likelihood": "High", "mitigation": "Hold a 10% contingency and require approval for any unbudgeted spend."},
        ],
        "tips": [
            "Assign one named person per task — shared ownership means no ownership.",
            "Keep a single WhatsApp group for the core team on event day, not several.",
            "Print the run-of-show and hand a copy to every coordinator.",
            "Photograph the venue setup before guests arrive; it settles disputes later.",
            "Collect feedback the same day while impressions are fresh.",
        ],
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
        return False, _friendly_error(exc, model)
