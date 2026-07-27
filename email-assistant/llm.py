"""
llm.py
------
Thin wrapper around the Groq API used by the app, plus a rule-based
offline fallback so the project still runs (in a clearly-labelled "Demo Mode")
if no API key is configured -- handy for classroom demos without internet/cost.
"""

import os
import streamlit as st

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from prompts import CATEGORIES, TONES

# Fast, high-quality instruction-following model available on Groq's free tier.
# Change from the sidebar at runtime if your account uses a different model id.
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_api_key() -> str | None:
    """Resolution order: sidebar override -> st.secrets -> environment variable."""
    key = st.session_state.get("api_key_override", "").strip()
    if key:
        return key
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY")


def is_online_mode() -> bool:
    return bool(get_api_key()) and Groq is not None


@st.cache_resource(show_spinner=False)
def _get_client(api_key: str):
    return Groq(api_key=api_key)


def call_model(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL,
                max_tokens: int = 700, temperature: float = 0.7) -> tuple[str, str | None]:
    """
    Returns (text, error). If error is not None, text will be empty and the
    caller should use the offline fallback instead.
    """
    api_key = get_api_key()
    if not api_key or Groq is None:
        return "", "NO_API_KEY"

    try:
        client = _get_client(api_key)
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        return text.strip(), None
    except Exception as exc:  # noqa: BLE001 - surface any API error to the UI
        return "", f"API_ERROR: {exc}"


# ---------------------------------------------------------------------------
# Offline / demo-mode fallback generator
# ---------------------------------------------------------------------------

_OFFLINE_OPENERS = {
    "formal": "I hope this email finds you well.",
    "friendly": "Hope you're doing great!",
    "persuasive": "I wanted to reach out about something I believe is worth your time.",
    "concise": "Quick note regarding the following.",
    "apologetic": "I want to start by sincerely apologizing for the inconvenience caused.",
    "assertive": "I'm writing to follow up on an important matter that needs your attention.",
}

_OFFLINE_CLOSERS = {
    "formal": "Thank you for your time and consideration.",
    "friendly": "Thanks so much, and looking forward to hearing from you!",
    "persuasive": "I'd really appreciate the chance to discuss this further at your convenience.",
    "concise": "Thanks.",
    "apologetic": "Thank you for your understanding, and I apologize again for any trouble caused.",
    "assertive": "I look forward to your prompt response on this.",
}


def offline_generate(category_key: str, tone_key: str, sender_name: str,
                      recipient_name: str, context: str, extra_instructions: str = "") -> str:
    """
    Deterministic, template-based fallback used when no API key is present.
    It is intentionally simple -- it exists purely to keep the app fully
    functional for demos, not to replace the LLM's language quality.
    """
    cat = CATEGORIES[category_key]
    tone = TONES[tone_key]
    greeting_name = recipient_name.strip() or "there"
    sign_name = sender_name.strip() or "[Your Name]"

    subject_map = {
        "job_application": f"Application for {context.split(',')[0].strip() if context else 'the Position'}",
        "leave_request": "Leave Request",
        "meeting_invitation": "Meeting Invitation",
        "customer_support": "Regarding Your Recent Query",
        "complaint": "Complaint Regarding Recent Experience",
        "follow_up": "Following Up on Our Previous Conversation",
        "custom": f"Regarding: {cat.label}",
    }
    subject = subject_map.get(category_key, cat.label)

    opener = _OFFLINE_OPENERS.get(tone_key, "")
    closer = _OFFLINE_CLOSERS.get(tone_key, "")
    body_context = context.strip() if context.strip() else (
        f"I'm writing to you regarding a {cat.label.lower()} matter."
    )
    extra = f"\n\n{extra_instructions.strip()}" if extra_instructions.strip() else ""

    body = f"""Dear {greeting_name},

{opener}

{body_context}{extra}

{closer}

Best regards,
{sign_name}"""

    return f"Subject: {subject}\n\n{body}"
