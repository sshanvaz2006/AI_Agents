"""
prompts.py
-----------
Centralized prompt-engineering layer for the Smart Email Assistant.

Keeping every prompt template in one place makes the "AI logic" of the
project easy to inspect, tune, and demo/viva-explain -- which is exactly
what a prompt-engineering-focused final year project should show off.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1. Domain data: email categories and writing tones
# ---------------------------------------------------------------------------

@dataclass
class CategoryInfo:
    label: str
    icon: str
    description: str
    fields_hint: str  # what info the model should look for in user input


CATEGORIES: dict[str, CategoryInfo] = {
    "job_application": CategoryInfo(
        label="Job Application",
        icon="💼",
        description="Applying for a job or internship, including a cover-letter-style email.",
        fields_hint="role/position, company name, relevant skills/experience, why they are a good fit",
    ),
    "leave_request": CategoryInfo(
        label="Leave Request",
        icon="🏖️",
        description="Requesting leave/time-off from a manager, HR, or professor.",
        fields_hint="type of leave, dates/duration, reason, handover/coverage plan",
    ),
    "meeting_invitation": CategoryInfo(
        label="Meeting Invitation",
        icon="📅",
        description="Inviting one or more people to a meeting or call.",
        fields_hint="purpose of meeting, proposed date/time, duration, attendees, agenda points",
    ),
    "customer_support": CategoryInfo(
        label="Customer Support",
        icon="🎧",
        description="Responding to or raising a customer support query.",
        fields_hint="issue description, order/ticket ID if any, resolution or next step offered",
    ),
    "complaint": CategoryInfo(
        label="Complaint",
        icon="⚠️",
        description="Raising a formal complaint about a product, service, or situation.",
        fields_hint="what went wrong, impact caused, desired resolution, relevant dates/references",
    ),
    "follow_up": CategoryInfo(
        label="Follow-up",
        icon="🔁",
        description="Following up on a previous email, interview, application, or conversation.",
        fields_hint="what the original interaction was about, how much time has passed, the ask",
    ),
    "custom": CategoryInfo(
        label="Custom / Other",
        icon="✍️",
        description="Any other email purpose described freely by the user.",
        fields_hint="whatever context the user provides",
    ),
}


@dataclass
class ToneInfo:
    label: str
    icon: str
    style_instruction: str


TONES: dict[str, ToneInfo] = {
    "formal": ToneInfo(
        "Formal", "🎩",
        "Use polished, professional, and respectful language. Avoid contractions and slang. "
        "Suitable for HR, senior management, or official correspondence.",
    ),
    "friendly": ToneInfo(
        "Friendly", "😊",
        "Use warm, approachable, conversational language while staying professional. "
        "Contractions are fine. Suitable for colleagues or people you already have rapport with.",
    ),
    "persuasive": ToneInfo(
        "Persuasive", "🎯",
        "Use confident, benefit-driven language that builds a compelling case and includes a "
        "clear call to action, without sounding pushy or exaggerated.",
    ),
    "concise": ToneInfo(
        "Concise", "⚡",
        "Be extremely brief and to the point. Short sentences, no filler, no repeated pleasantries. "
        "Prioritize the core message and the ask.",
    ),
    "apologetic": ToneInfo(
        "Apologetic", "🙏",
        "Acknowledge the issue sincerely, take ownership where appropriate, and reassure the "
        "reader, without being overly self-deprecating.",
    ),
    "assertive": ToneInfo(
        "Assertive", "💪",
        "Be direct and firm about expectations or requirements while remaining respectful and "
        "professional, avoiding aggressive or rude language.",
    ),
}


# ---------------------------------------------------------------------------
# 2. Core system prompt (persona + hard constraints)
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """You are "Mailwright", an expert professional email-writing assistant.

Your job: given a purpose, a desired tone, and context/bullet points from the user,
produce a single, ready-to-send, context-aware email.

Hard rules:
1. Output ONLY the email itself (subject line + body). No preamble like "Here is your email",
   no explanations, no markdown code fences.
2. Format your response EXACTLY as:
Subject: <subject line>

<email body>
3. The email body must include an appropriate greeting and sign-off. Use the sender name if
   given, otherwise use a generic closing like "Best regards".
4. Never invent concrete facts (dates, numbers, names, company policies) that the user did not
   provide or imply. If something essential is missing, phrase it generically instead of
   fabricating specifics.
5. Match the requested tone and category conventions precisely.
6. Keep the email realistic in length for its purpose (a leave request should not be as long as
   a job application cover email).
7. Do not use placeholder brackets like [Your Name] if the sender name was actually provided -
   use the real value. Only use a bracket placeholder such as [Your Name] when truly nothing
   was given.
"""


# ---------------------------------------------------------------------------
# 3. Prompt builders
# ---------------------------------------------------------------------------

def build_generation_prompt(
    category_key: str,
    tone_key: str,
    sender_name: str,
    recipient_name: str,
    context: str,
    extra_instructions: str = "",
) -> tuple[str, str]:
    """Builds (system_prompt, user_prompt) for a fresh email generation."""
    cat = CATEGORIES[category_key]
    tone = TONES[tone_key]

    system_prompt = BASE_SYSTEM_PROMPT

    user_prompt = f"""Email purpose category: {cat.label}
Category description: {cat.description}
Typical relevant details for this category: {cat.fields_hint}

Requested tone: {tone.label}
Tone style guide: {tone.style_instruction}

Sender name: {sender_name or "(not provided)"}
Recipient name: {recipient_name or "(not provided)"}

User-provided context / key points to include:
\"\"\"
{context.strip() or "(no extra context given, use only the category and tone to write a sensible generic email)"}
\"\"\"
"""

    if extra_instructions.strip():
        user_prompt += f"\nAdditional user instructions: {extra_instructions.strip()}\n"

    user_prompt += "\nNow write the email following the required output format exactly."
    return system_prompt, user_prompt


def build_regenerate_prompt(previous_email: str, category_key: str, tone_key: str) -> tuple[str, str]:
    """Ask the model to produce a fresh variant of an already-generated email."""
    cat = CATEGORIES[category_key]
    tone = TONES[tone_key]

    system_prompt = BASE_SYSTEM_PROMPT
    user_prompt = f"""Here is an email that was already generated for a "{cat.label}" purpose in a
"{tone.label}" tone:

\"\"\"
{previous_email.strip()}
\"\"\"

Write a DIFFERENT version of this email - same purpose, same tone, same key facts and intent,
but reworded with a noticeably different structure, opening line, and phrasing so it does not
feel like a duplicate. Keep it equally professional and appropriate.

Follow the required output format exactly."""
    return system_prompt, user_prompt


def build_grammar_fix_prompt(email_text: str) -> tuple[str, str]:
    system_prompt = (
        "You are a meticulous professional editor. You fix grammar, spelling, punctuation, and "
        "awkward phrasing in emails WITHOUT changing their meaning, tone, structure, facts, or "
        "the subject line's intent unless it contains a grammatical error. Output ONLY the "
        "corrected email in the exact format:\nSubject: <subject line>\n\n<email body>\n"
        "No commentary, no explanation of changes."
    )
    user_prompt = f"""Correct grammar, spelling, and clarity issues in this email, keeping the
tone and meaning identical:

\"\"\"
{email_text.strip()}
\"\"\""""
    return system_prompt, user_prompt


def build_tone_change_prompt(email_text: str, new_tone_key: str) -> tuple[str, str]:
    tone = TONES[new_tone_key]
    system_prompt = BASE_SYSTEM_PROMPT
    user_prompt = f"""Rewrite the following email so that it uses this tone instead:

Target tone: {tone.label}
Tone style guide: {tone.style_instruction}

Keep the same purpose, facts, and overall length category - only change the tone, word choice,
and phrasing style.

Original email:
\"\"\"
{email_text.strip()}
\"\"\"

Follow the required output format exactly."""
    return system_prompt, user_prompt


def build_length_adjust_prompt(email_text: str, mode: str) -> tuple[str, str]:
    """mode: 'shorten' or 'expand'"""
    instruction = (
        "Make this email noticeably shorter and more concise, cutting redundant phrases while "
        "keeping every essential fact and the core ask intact."
        if mode == "shorten"
        else
        "Expand this email slightly with a bit more context, courtesy, and detail, without "
        "making it feel padded or repetitive."
    )
    system_prompt = BASE_SYSTEM_PROMPT
    user_prompt = f"""{instruction}

Original email:
\"\"\"
{email_text.strip()}
\"\"\"

Follow the required output format exactly."""
    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# 4. Output parsing helper
# ---------------------------------------------------------------------------

def parse_subject_and_body(raw_text: str) -> tuple[str, str]:
    """Splits a model response formatted as 'Subject: ...\\n\\n body...' into parts."""
    raw_text = raw_text.strip()
    if raw_text.lower().startswith("subject:"):
        first_line, _, rest = raw_text.partition("\n")
        subject = first_line.split(":", 1)[1].strip()
        body = rest.strip()
        return subject, body
    # fallback: no explicit subject line found
    return "Untitled Email", raw_text
