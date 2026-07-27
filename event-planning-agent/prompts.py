"""
prompts.py
==========
Prompt-engineering layer for the AI Event Planning Agent.

Design notes (useful for a viva walkthrough):

* The agent returns **strict JSON**, not prose. A plan is inherently structured
  data — tasks with owners and dates, budget lines with unit costs — so asking
  for a schema turns "write me a plan" into a genuine planning/organisation task.

* **The model never does arithmetic.** It proposes budget *line items* with a
  unit cost and a quantity; every total, subtotal, contingency and per-head
  figure is computed in ``budget.py`` with Python. LLMs are unreliable at
  multi-step maths, and a budget that does not add up is the fastest way to
  lose credibility in a demo.

* **Deadlines are relative, not absolute.** The model emits
  ``days_before_event`` integers; ``app.py`` converts them to real dates against
  the user's event date. This stops the model inventing calendar dates that fall
  after the event or on impossible days.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Event types — each carries the domain knowledge that matters for planning it.
# --------------------------------------------------------------------------- #

EVENT_TYPES: dict[str, dict[str, str]] = {
    "birthday": {
        "label": "Birthday Party",
        "icon": "🎂",
        "description": "Private celebration for family and friends.",
        "focus": (
            "Prioritise venue ambience, catering, cake, decorations, music and "
            "photography. Guest logistics are informal — no registration desk or "
            "badges. Keep the checklist practical and family-friendly. Budget "
            "should lean toward food and decoration rather than AV equipment."
        ),
    },
    "workshop": {
        "label": "Workshop / Training",
        "icon": "🛠️",
        "description": "Hands-on skill session with an instructor.",
        "focus": (
            "Prioritise trainer logistics, participant materials (handouts, kits, "
            "worksheets), seating layout suited to hands-on work, power outlets "
            "and reliable Wi-Fi, and a feedback form. Include pre-reading "
            "distribution and post-event certificates. Equipment matters more "
            "than decoration."
        ),
    },
    "conference": {
        "label": "Conference",
        "icon": "🎤",
        "description": "Multi-session professional event with speakers.",
        "focus": (
            "Prioritise speaker management (invitations, travel, honorarium, bios, "
            "slide collection), a registration desk with badges, session tracks and "
            "a printed agenda, professional AV with backup, press or social media "
            "coverage, and sponsor deliverables. Timeline should start much earlier "
            "than for a small event."
        ),
    },
    "college_fest": {
        "label": "College Fest",
        "icon": "🎪",
        "description": "Multi-day student festival with competitions.",
        "focus": (
            "Prioritise faculty and administration approvals, student volunteer "
            "teams with clear coordinators, sponsorship outreach, event categories "
            "and competition rules, stage and sound setup, prizes and certificates, "
            "crowd control and security, and social media promotion. Budget is "
            "usually sponsorship-driven, so include an expected-sponsorship note."
        ),
    },
    "seminar": {
        "label": "Seminar / Guest Lecture",
        "icon": "📚",
        "description": "Single-speaker academic or professional talk.",
        "focus": (
            "Prioritise speaker invitation and confirmation, hall booking, "
            "projector and microphone with a tested backup, attendance register, "
            "a memento or thank-you gift for the speaker, and light refreshments. "
            "This is a comparatively simple event — do not over-engineer the plan."
        ),
    },
    "wedding": {
        "label": "Wedding / Reception",
        "icon": "💍",
        "description": "Large multi-ceremony family event.",
        "focus": (
            "Prioritise venue and date booking well in advance, catering with menu "
            "tasting, decoration and floral work, photography and videography, "
            "guest accommodation and transport, invitation printing and dispatch, "
            "and a detailed day-of ceremony schedule. Budgets are large — be "
            "realistic about the dominance of catering and venue costs."
        ),
    },
    "hackathon": {
        "label": "Hackathon",
        "icon": "💻",
        "description": "Overnight or multi-day coding competition.",
        "focus": (
            "Prioritise reliable high-bandwidth internet, power distribution and "
            "extension boards, 24-hour venue access, judging panel and criteria, "
            "problem statements, mentors, food across odd hours including night, "
            "prizes, and participant registration with team formation. Internet "
            "and power are make-or-break — flag them as high risk."
        ),
    },
    "corporate": {
        "label": "Corporate Event",
        "icon": "🏢",
        "description": "Team offsite, product launch or annual meet.",
        "focus": (
            "Prioritise agenda alignment with business objectives, senior "
            "leadership availability, professional venue and catering, branding "
            "and collateral, team activities, and formal invitations with RSVP "
            "tracking. Maintain a polished, corporate register throughout."
        ),
    },
}

DEFAULT_EVENT_TYPE = "workshop"


# --------------------------------------------------------------------------- #
# Scale bands — size changes planning qualitatively, not just quantitatively.
# --------------------------------------------------------------------------- #

SCALE_BANDS: list[tuple[int, str, str]] = [
    (
        30,
        "Intimate",
        "Under 30 guests. A single coordinator can manage everything. Skip "
        "formal registration, security and volunteer hierarchies — they would "
        "be overkill. Keep the checklist short and actionable.",
    ),
    (
        100,
        "Small",
        "30-100 guests. One coordinator plus 2-3 helpers. Introduce a simple "
        "sign-in sheet and a basic run-of-show. Still no need for security or "
        "large volunteer teams.",
    ),
    (
        300,
        "Medium",
        "100-300 guests. Requires named sub-teams (logistics, hospitality, "
        "technical, publicity), a registration desk, crowd flow planning, and "
        "a written run-of-show with time slots.",
    ),
    (
        1000,
        "Large",
        "300-1000 guests. Requires formal team structure with coordinators, "
        "security personnel, medical/first-aid presence, parking management, "
        "multiple registration counters, and permits where applicable.",
    ),
    (
        10**9,
        "Very Large",
        "Over 1000 guests. Requires professional event-management support, "
        "police/municipal permissions, crowd control barriers, ambulance on "
        "standby, fire safety clearance, and a formal incident response plan. "
        "Emphasise compliance and safety heavily.",
    ),
]


def scale_for(attendees: int) -> tuple[str, str]:
    """Return the (band name, planning guidance) for a headcount."""
    for ceiling, name, guidance in SCALE_BANDS:
        if attendees <= ceiling:
            return name, guidance
    return SCALE_BANDS[-1][1], SCALE_BANDS[-1][2]


# --------------------------------------------------------------------------- #
# Budget categories — fixed vocabulary so the maths layer can group reliably.
# --------------------------------------------------------------------------- #

BUDGET_CATEGORIES = [
    "Venue",
    "Catering",
    "Decoration",
    "Equipment & AV",
    "Marketing & Printing",
    "Speakers & Talent",
    "Prizes & Gifts",
    "Transport & Logistics",
    "Staffing & Security",
    "Miscellaneous",
]

CHECKLIST_PHASES = [
    "Planning & Approvals",
    "Booking & Procurement",
    "Promotion & Invitations",
    "Final Week",
    "Event Day",
    "Post-Event",
]


# --------------------------------------------------------------------------- #
# The JSON contract
# --------------------------------------------------------------------------- #

OUTPUT_SCHEMA = """{
  "event_title": "string - a polished name for the event",
  "summary": "string - 3-5 sentence overview of the plan and its approach",
  "venue": {
    "recommendations": [
      {
        "option": "string - type of venue, e.g. \\"College auditorium\\"",
        "why": "string - why it suits this event and size",
        "capacity_fit": "string - e.g. \\"Comfortable for 150-200\\"",
        "est_cost": number - estimated cost in the given currency, 0 if free
      }
    ],
    "layout": "string - recommended seating/space arrangement",
    "requirements": ["string - must-haves the venue needs, e.g. \\"3-phase power\\""]
  },
  "budget_items": [
    {
      "category": "string - MUST be one of the allowed categories",
      "item": "string - specific line item",
      "unit_cost": number - cost per unit, numeric only, no currency symbol,
      "quantity": number - how many units,
      "unit": "string - e.g. \\"person\\", \\"day\\", \\"item\\", \\"lump sum\\"",
      "notes": "string - assumption behind the estimate, else \\"\\""
    }
  ],
  "checklist": [
    {
      "phase": "string - MUST be one of the allowed phases",
      "task": "string - imperative, specific and actionable",
      "owner_role": "string - role responsible, e.g. \\"Logistics Lead\\"",
      "days_before_event": number - integer; 0 means on the day, negative means after,
      "priority": "string - High, Medium or Low"
    }
  ],
  "equipment": [
    {
      "item": "string",
      "quantity": "string - e.g. \\"2\\", \\"1 per table\\"",
      "essential": true or false,
      "notes": "string - sourcing or setup note, else \\"\\""
    }
  ],
  "invitations": {
    "channels": ["string - e.g. \\"Printed cards\\", \\"WhatsApp broadcast\\""],
    "send_schedule": "string - when to send and when to follow up",
    "guest_segments": [
      {"segment": "string - e.g. \\"Faculty\\"", "count": number, "approach": "string"}
    ],
    "rsvp_method": "string - how RSVPs will be collected and tracked",
    "sample_message": "string - a ready-to-send invitation, 40-80 words"
  },
  "timeline": [
    {
      "milestone": "string - e.g. \\"Venue confirmed\\"",
      "days_before_event": number - integer,
      "detail": "string - what completion looks like"
    }
  ],
  "day_schedule": [
    {"time": "string - e.g. \\"09:00\\"", "activity": "string", "owner": "string"}
  ],
  "risks": [
    {"risk": "string", "likelihood": "string - High/Medium/Low", "mitigation": "string"}
  ],
  "tips": ["string - practical advice specific to this event type and scale"]
}"""


BASE_SYSTEM_PROMPT = f"""You are "Orchestrate", a professional event planner with \
fifteen years of experience running everything from intimate gatherings to \
thousand-delegate conferences.

Your job is to turn a short event brief into a complete, realistic, actionable plan.

## CRITICAL RULES

1. **Never do arithmetic.** For every budget line give a `unit_cost` and a \
`quantity` only. Do NOT compute totals, subtotals, or grand totals — a separate \
system handles all calculation. Providing your own totals will corrupt the output.
2. **Scale the plan to the event.** A 20-person birthday must not receive a \
security team, a registration desk, or a volunteer hierarchy. A 2000-person fest \
must not be planned as though one person can run it. Match the depth of the plan \
to the size and formality of the event.
3. **Be specific, never generic.** "Book venue" is useless. "Shortlist three \
auditoriums, visit each, confirm the one with tiered seating and a working \
projector" is a real task. Every checklist item must be something a person can \
actually pick up and do.
4. **Use realistic local costs.** Estimate in the currency given in the brief and \
for the region given. Prices must be plausible for that market, not generic \
Western figures. State your assumption in the `notes` field of each line.
5. **Deadlines are relative.** Give `days_before_event` as an integer. Never \
invent calendar dates — the system computes them.
6. **Respect the allowed vocabularies.** `category` must be one of: \
{", ".join(BUDGET_CATEGORIES)}. `phase` must be one of: {", ".join(CHECKLIST_PHASES)}.
7. **Cover the full lifecycle.** The checklist must include post-event tasks \
(vendor settlement, thank-you notes, feedback collection, cleanup) — these are \
the most commonly forgotten items in an amateur plan.
8. **Be honest about risk.** Identify what realistically goes wrong for this \
specific event type and give a concrete mitigation, not a platitude.

## OUTPUT FORMAT

Return ONLY a single valid JSON object matching this schema exactly. No markdown \
code fences, no commentary before or after, no explanation.

{OUTPUT_SCHEMA}
"""


# --------------------------------------------------------------------------- #
# Prompt builders
# --------------------------------------------------------------------------- #


def build_plan_prompt(
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
) -> tuple[str, str]:
    """Build the (system, user) prompt pair for a full plan generation."""
    etype = EVENT_TYPES.get(event_type, EVENT_TYPES[DEFAULT_EVENT_TYPE])
    band, guidance = scale_for(attendees)

    budget_line = (
        f"Total budget: {currency} {budget:,.0f} "
        f"(approximately {currency} {budget / max(attendees, 1):,.0f} per head)"
        if budget > 0
        else "Total budget: not specified — propose a sensible budget and justify it."
    )

    system = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"## EVENT TYPE: {etype['label']}\n{etype['focus']}\n\n"
        f"## SCALE: {band} ({attendees} attendees)\n{guidance}"
    )

    user = f"""Create a complete event plan from this brief.

EVENT BRIEF
- Event: {event_name or etype['label']}
- Type: {etype['label']}
- Expected attendees: {attendees}
- {budget_line}
- Currency: {currency}
- Location / region: {location or 'not specified'}
- Date: {event_date or 'not yet fixed'}
- Duration: {duration or 'not specified'}
- Formality: {formality}

ADDITIONAL REQUIREMENTS FROM THE ORGANISER
{notes.strip() if notes.strip() else '(none given)'}

Produce a plan whose budget lines, when multiplied out and summed, land close to
the stated total budget without exceeding it. Remember: give unit_cost and
quantity only, never totals.

Return only the JSON object."""

    return system, user


def build_refine_prompt(current_json: str, instruction: str) -> tuple[str, str]:
    """Build a prompt that revises an existing plan."""
    system = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        "## REVISION MODE\n"
        "You are revising a plan you produced earlier. Apply the user's "
        "instruction and leave every unrelated part of the plan unchanged. "
        "Return the complete revised JSON object, never a fragment or a diff. "
        "The no-arithmetic rule still applies."
    )
    user = (
        f"Current plan:\n\n{current_json}\n\n"
        f"REVISION INSTRUCTION: {instruction}\n\n"
        "Return only the full revised JSON object."
    )
    return system, user


REFINEMENT_ACTIONS: dict[str, dict[str, str]] = {
    "cheaper": {
        "label": "Cut Costs 20%",
        "instruction": (
            "Reduce the overall budget by roughly 20%. Do this by lowering unit "
            "costs to more economical options, reducing quantities where "
            "reasonable, or removing genuinely non-essential line items. Never "
            "cut safety, security or first-aid provisions. Update the notes on "
            "each changed line to explain the cheaper choice."
        ),
    },
    "premium": {
        "label": "Make It Premium",
        "instruction": (
            "Upgrade the plan to a premium tier. Raise unit costs to reflect "
            "better vendors, add tasteful enhancements (better catering, "
            "professional photography, welcome kits, upgraded AV), and reflect "
            "the higher standard in the venue recommendations and checklist."
        ),
    },
    "detail": {
        "label": "More Detail",
        "instruction": (
            "Expand the checklist with additional specific sub-tasks, add more "
            "entries to the day-of schedule, and enrich the equipment list. Do "
            "not change the budget."
        ),
    },
    "simplify": {
        "label": "Simplify",
        "instruction": (
            "Condense the plan for a smaller organising team. Merge related "
            "checklist tasks, drop nice-to-have items, and keep only what is "
            "genuinely necessary to run the event well."
        ),
    },
}
