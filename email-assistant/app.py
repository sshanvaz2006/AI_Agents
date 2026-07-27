"""
Smart Email Assistant - AI-Powered Professional Email Generator
Final Year B.Tech Project

Run with:  streamlit run app.py
"""

import datetime as dt

import streamlit as st
from streamlit_option_menu import option_menu

from styles import CUSTOM_CSS
from prompts import CATEGORIES, TONES, parse_subject_and_body, \
    build_generation_prompt, build_regenerate_prompt, build_grammar_fix_prompt, \
    build_tone_change_prompt, build_length_adjust_prompt
from llm import call_model, offline_generate, is_online_mode, DEFAULT_MODEL
from export_utils import build_docx_bytes, build_txt_bytes


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Smart Email Assistant",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_state():
    defaults = {
        "email_history": [],
        "current_subject": "",
        "current_body": "",
        "current_category": "job_application",
        "current_tone": "formal",
        "api_key_override": "",
        "model_choice": DEFAULT_MODEL,
        "has_generated": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def run_llm(system_prompt: str, user_prompt: str, category_key: str, tone_key: str,
            sender_name: str = "", recipient_name: str = "", context: str = "",
            extra_instructions: str = "") -> tuple[str, str, bool]:
    """Runs the model (or offline fallback) and returns (subject, body, was_online)."""
    text, error = call_model(system_prompt, user_prompt, model=st.session_state.model_choice)

    if error:
        fallback_raw = offline_generate(
            category_key, tone_key, sender_name, recipient_name, context, extra_instructions
        )
        subject, body = parse_subject_and_body(fallback_raw)
        if error != "NO_API_KEY":
            st.warning(f"⚠️ API call failed, showing offline demo output instead. Details: {error}")
        return subject, body, False

    subject, body = parse_subject_and_body(text)
    return subject, body, True


def push_history(subject: str, body: str, category_key: str, tone_key: str):
    st.session_state.email_history.insert(0, {
        "subject": subject,
        "body": body,
        "category": category_key,
        "tone": tone_key,
        "time": dt.datetime.now().strftime("%d %b, %I:%M %p"),
    })
    st.session_state.email_history = st.session_state.email_history[:20]


def render_email_card():
    if not st.session_state.has_generated:
        return

    mode_badge = (
        '<span class="badge-online">🟢 AI-generated</span>'
        if st.session_state.get("last_was_online")
        else '<span class="badge-offline">🟡 Offline demo mode</span>'
    )

    word_count = len(st.session_state.current_body.split())
    char_count = len(st.session_state.current_body)

    st.markdown('<div class="section-label">Generated email</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="email-card">
            <div class="email-subject">📨 {st.session_state.current_subject}</div>
            <div class="email-body">{st.session_state.current_body}</div>
        </div>
        <div style="margin-bottom: 0.8rem;">
            {mode_badge}
            <span class="stat-pill">📝 {word_count} words</span>
            <span class="stat-pill">🔤 {char_count} characters</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Editable copy so the user can tweak before export/copy
    with st.expander("✏️ Edit manually before exporting"):
        st.session_state.current_subject = st.text_input("Subject", st.session_state.current_subject)
        st.session_state.current_body = st.text_area("Body", st.session_state.current_body, height=220)

    # Copy-to-clipboard block (native, no extra JS libs needed)
    with st.expander("📋 Copy text"):
        st.code(f"Subject: {st.session_state.current_subject}\n\n{st.session_state.current_body}", language=None)

    st.markdown('<div class="section-label">Refine this email</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("🔄 Regenerate", use_container_width=True):
            sys_p, user_p = build_regenerate_prompt(
                st.session_state.current_body,
                st.session_state.current_category,
                st.session_state.current_tone,
            )
            subj, body, online = run_llm(
                sys_p, user_p, st.session_state.current_category, st.session_state.current_tone
            )
            st.session_state.current_subject, st.session_state.current_body = subj, body
            st.session_state.last_was_online = online
            push_history(subj, body, st.session_state.current_category, st.session_state.current_tone)
            st.rerun()

    with c2:
        if st.button("✅ Fix Grammar", use_container_width=True):
            sys_p, user_p = build_grammar_fix_prompt(
                f"Subject: {st.session_state.current_subject}\n\n{st.session_state.current_body}"
            )
            subj, body, online = run_llm(
                sys_p, user_p, st.session_state.current_category, st.session_state.current_tone
            )
            st.session_state.current_subject, st.session_state.current_body = subj, body
            st.session_state.last_was_online = online
            st.rerun()

    with c3:
        if st.button("✂️ Shorten", use_container_width=True):
            sys_p, user_p = build_length_adjust_prompt(
                f"Subject: {st.session_state.current_subject}\n\n{st.session_state.current_body}",
                mode="shorten",
            )
            subj, body, online = run_llm(
                sys_p, user_p, st.session_state.current_category, st.session_state.current_tone
            )
            st.session_state.current_subject, st.session_state.current_body = subj, body
            st.session_state.last_was_online = online
            st.rerun()

    with c4:
        if st.button("➕ Expand", use_container_width=True):
            sys_p, user_p = build_length_adjust_prompt(
                f"Subject: {st.session_state.current_subject}\n\n{st.session_state.current_body}",
                mode="expand",
            )
            subj, body, online = run_llm(
                sys_p, user_p, st.session_state.current_category, st.session_state.current_tone
            )
            st.session_state.current_subject, st.session_state.current_body = subj, body
            st.session_state.last_was_online = online
            st.rerun()

    st.markdown('<div class="section-label">Change tone</div>', unsafe_allow_html=True)
    tc1, tc2 = st.columns([3, 1])
    with tc1:
        new_tone_key = st.selectbox(
            "New tone", options=list(TONES.keys()),
            format_func=lambda k: f"{TONES[k].icon} {TONES[k].label}",
            index=list(TONES.keys()).index(st.session_state.current_tone),
            label_visibility="collapsed",
        )
    with tc2:
        if st.button("Apply tone", use_container_width=True):
            sys_p, user_p = build_tone_change_prompt(
                f"Subject: {st.session_state.current_subject}\n\n{st.session_state.current_body}",
                new_tone_key,
            )
            subj, body, online = run_llm(sys_p, user_p, st.session_state.current_category, new_tone_key)
            st.session_state.current_subject, st.session_state.current_body = subj, body
            st.session_state.current_tone = new_tone_key
            st.session_state.last_was_online = online
            st.rerun()

    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇️ Download as .txt",
            data=build_txt_bytes(st.session_state.current_subject, st.session_state.current_body),
            file_name="email.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "⬇️ Download as .docx",
            data=build_docx_bytes(st.session_state.current_subject, st.session_state.current_body),
            file_name="email.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Sidebar navigation + settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ✉️ Smart Email Assistant")
    page = option_menu(
        menu_title=None,
        options=["Home", "Compose", "History", "About"],
        icons=["house", "pencil-square", "clock-history", "info-circle"],
        default_index=1,
        styles={
            "container": {"padding": "0", "background-color": "transparent"},
            "icon": {"color": "#4F46E5", "font-size": "16px"},
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "2px 0", "border-radius": "8px"},
            "nav-link-selected": {"background-color": "#4F46E5", "color": "white"},
        },
    )

    st.markdown("---")
    st.markdown("##### ⚙️ Model Settings")
    st.session_state.api_key_override = st.text_input(
        "Groq API key (optional)",
        type="password",
        value=st.session_state.api_key_override,
        help="Leave empty to use the GROQ_API_KEY environment variable / "
             "st.secrets, or to fall back to offline demo mode. "
             "Get a free key at console.groq.com/keys",
    )
    st.session_state.model_choice = st.text_input(
        "Model name", value=st.session_state.model_choice,
        help="Change this if you want a different Groq-hosted model, "
             "e.g. llama-3.1-8b-instant, gemma2-9b-it, openai/gpt-oss-120b.",
    )

    if is_online_mode():
        st.success("🟢 Connected — live AI generation")
    else:
        st.warning("🟡 No API key — running in offline demo mode")


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------

if page == "Home":
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">Write better emails, faster ✉️</div>
            <div class="hero-subtitle">
                An AI-powered assistant that turns a few bullet points into a polished,
                context-aware, professional email — in the tone you choose.
            </div>
            <div class="hero-badges">
                <span class="hero-badge">🎓 B.Tech Final Year Project</span>
                <span class="hero-badge">🤖 Prompt Engineering</span>
                <span class="hero-badge">⚡ Built with Streamlit</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### What can it do?")
    features = [
        ("💼", "6 Email Categories", "Job applications, leave requests, meetings, support, complaints, follow-ups."),
        ("🎭", "4+ Writing Tones", "Formal, friendly, persuasive, concise, apologetic, and assertive styles."),
        ("🔄", "Regenerate & Refine", "Re-roll, fix grammar, shorten, expand, or switch tone in one click."),
        ("📤", "Export Anywhere", "Copy instantly, or download as .txt / .docx."),
    ]
    cols = st.columns(4)
    for col, (emoji, title, desc) in zip(cols, features):
        with col:
            st.markdown(
                f"""<div class="feature-card">
                    <div class="emoji">{emoji}</div>
                    <h4>{title}</h4>
                    <p>{desc}</p>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("")
    st.info("👉 Head to the **Compose** tab from the sidebar to generate your first email.")


# ---------------------------------------------------------------------------
# COMPOSE PAGE
# ---------------------------------------------------------------------------

elif page == "Compose":
    st.markdown("### 📝 Compose a New Email")
    st.caption("Fill in the details below — the assistant will handle structure, tone, and phrasing.")

    left, right = st.columns([1.05, 1])

    with left:
        st.markdown('<div class="section-label">1. Purpose</div>', unsafe_allow_html=True)
        category_key = st.selectbox(
            "Email category",
            options=list(CATEGORIES.keys()),
            format_func=lambda k: f"{CATEGORIES[k].icon} {CATEGORIES[k].label}",
            label_visibility="collapsed",
        )
        st.caption(CATEGORIES[category_key].description)

        st.markdown('<div class="section-label">2. Tone / writing style</div>', unsafe_allow_html=True)
        tone_key = st.selectbox(
            "Tone",
            options=list(TONES.keys()),
            format_func=lambda k: f"{TONES[k].icon} {TONES[k].label}",
            label_visibility="collapsed",
        )
        st.caption(TONES[tone_key].style_instruction)

        st.markdown('<div class="section-label">3. Names (optional)</div>', unsafe_allow_html=True)
        n1, n2 = st.columns(2)
        with n1:
            sender_name = st.text_input("Your name", placeholder="e.g. Aarav Sharma")
        with n2:
            recipient_name = st.text_input("Recipient's name", placeholder="e.g. Ms. Priya Nair")

        st.markdown('<div class="section-label">4. Context / key points</div>', unsafe_allow_html=True)
        context = st.text_area(
            "Context",
            placeholder=f"e.g. {CATEGORIES[category_key].fields_hint}",
            height=140,
            label_visibility="collapsed",
        )

        with st.expander("➕ Additional instructions (optional)"):
            extra_instructions = st.text_input(
                "Anything specific to include or avoid?",
                placeholder="e.g. mention I can join within 30 days / keep it under 100 words",
            )

        generate = st.button("✨ Generate Email", type="primary", use_container_width=True)

        if generate:
            with st.spinner("Drafting your email..."):
                sys_p, user_p = build_generation_prompt(
                    category_key, tone_key, sender_name, recipient_name, context, extra_instructions
                )
                subj, body, online = run_llm(
                    sys_p, user_p, category_key, tone_key,
                    sender_name, recipient_name, context, extra_instructions,
                )
            st.session_state.current_subject = subj
            st.session_state.current_body = body
            st.session_state.current_category = category_key
            st.session_state.current_tone = tone_key
            st.session_state.last_was_online = online
            st.session_state.has_generated = True
            push_history(subj, body, category_key, tone_key)
            st.rerun()

    with right:
        render_email_card()
        if not st.session_state.has_generated:
            st.markdown(
                """<div class="feature-card" style="text-align:center; padding: 2.5rem 1rem;">
                    <div style="font-size:2rem;">📭</div>
                    <p style="margin-top:0.5rem;">Your generated email will appear here.</p>
                </div>""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# HISTORY PAGE
# ---------------------------------------------------------------------------

elif page == "History":
    st.markdown("### 🕘 Generation History")
    st.caption("Your last 20 generated emails in this session (not saved after you close the app).")

    if not st.session_state.email_history:
        st.info("No emails generated yet. Go to **Compose** to create your first one.")
    else:
        for idx, item in enumerate(st.session_state.email_history):
            cat = CATEGORIES[item["category"]]
            tone = TONES[item["tone"]]
            with st.container():
                st.markdown(
                    f"""<div class="history-item">
                        <div class="h-subject">📨 {item['subject']}</div>
                        <div class="h-meta">{cat.icon} {cat.label} · {tone.icon} {tone.label} · {item['time']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns([1, 5])
                with c1:
                    if st.button("Reload", key=f"reload_{idx}"):
                        st.session_state.current_subject = item["subject"]
                        st.session_state.current_body = item["body"]
                        st.session_state.current_category = item["category"]
                        st.session_state.current_tone = item["tone"]
                        st.session_state.has_generated = True
                        st.session_state.last_was_online = True
                        st.success("Loaded into Compose tab — switch tabs to view/edit it.")

        if st.button("🗑️ Clear history"):
            st.session_state.email_history = []
            st.rerun()


# ---------------------------------------------------------------------------
# ABOUT PAGE
# ---------------------------------------------------------------------------

elif page == "About":
    st.markdown("### ℹ️ About this Project")
    st.markdown(
        """
This **Smart Email Assistant** is a B.Tech final year project demonstrating
**prompt engineering** and **context-aware natural language generation**
using a large language model.

#### 🎯 Objective
Build an AI agent that understands a user's intent (email category + tone +
context) and produces a well-structured, ready-to-send professional email,
with the ability to iteratively refine the output (regenerate, fix grammar,
change tone, shorten/expand).

#### 🧠 How the "AI Agent" works
1. **Intent capture** — category, tone, names, and free-text context are
   collected from the user.
2. **Prompt construction** (`prompts.py`) — a structured system prompt encodes
   hard formatting rules and persona; a dynamic user prompt injects the
   captured intent and category-specific guidance.
3. **Generation** (`llm.py`) — the prompt is sent to a Groq-hosted LLM
   (Llama 3.3 70B by default) via Groq's chat completions API, known for
   very low-latency inference.
   If no API key is available, a rule-based **offline demo mode** keeps the
   app fully functional.
4. **Refinement loop** — follow-up prompts (regenerate / grammar fix / tone
   change / shorten / expand) reuse the same prompt-engineering pattern on
   the model's own previous output.

#### 🛠️ Tech Stack
- **Frontend / App framework:** Streamlit + `streamlit-option-menu`
- **Styling:** Custom CSS injected via `st.markdown` (Google Fonts, gradient
  hero, card layouts) — no default Streamlit look
- **LLM:** Groq API (`groq` Python SDK, Llama 3.3 70B by default)
- **Document export:** `python-docx`
- **Language:** Python 3.10+

#### 📁 Project structure
```
email-assistant/
├── app.py            # Streamlit UI & page routing
├── prompts.py         # Prompt engineering: templates & builders
├── llm.py             # Model client + offline fallback
├── export_utils.py    # .txt / .docx export helpers
├── styles.py           # Custom CSS
├── requirements.txt
└── .streamlit/config.toml
```

#### 🚀 Possible extensions
- Multi-language email generation
- Email thread / reply-aware context
- User accounts with persistent history (SQLite)
- Attachment-aware summarizing replies
        """
    )

st.markdown(
    '<div class="footer-note">Smart Email Assistant · B.Tech Final Year Project · '
    'Built with Streamlit & Groq</div>',
    unsafe_allow_html=True,
)
