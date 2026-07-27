"""
app.py
======
AI Meeting Minutes Generator — Streamlit front end.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

import export_utils
import llm
import prompts
from styles import CSS

# --------------------------------------------------------------------------- #
# Page configuration
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="AI Meeting Minutes Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

try:
    from streamlit_option_menu import option_menu

    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #

DEFAULTS = {
    "minutes": None,        # dict | None — the current minutes
    "meta": None,           # MinutesResult metadata for the current minutes
    "history": [],          # list of past generations
    "transcript": "",
    "page": "Generate",
    "editing": False,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


SAMPLE_TRANSCRIPT = """Project Sync — Orion Release
Thursday, 12 March, 10:00-10:45

Present: Priya Menon (PM), Arjun Rao (Eng Lead), Sara Fernandes (Design), Dev Kapoor (QA)
Apologies: Meera Iyer (Marketing)

Priya: Morning everyone. Let's start with where we are on the Orion release. Arjun?

Arjun: Backend is basically done. The payments integration went in on Tuesday, and
we've got 94% test coverage on that module. The one thing I'm worried about is the
migration script — it ran for about forty minutes on the staging dataset, and
production is roughly four times bigger. So we could be looking at close to three
hours of downtime if we do it the naive way.

Priya: Three hours is not going to fly. Marketing has the launch email scheduled.

Arjun: Right. I think we should do a phased migration instead. Migrate the read
tables first while the app stays up, then a short window for the write tables.
Maybe fifteen minutes of actual downtime.

Priya: Okay, I think that's the right call. Let's go with the phased migration.
Arjun, can you write that up as a proper runbook so Dev can test it?

Arjun: Yes, I'll have the runbook done by Monday.

Dev: I'll need at least two days to run through it properly on staging, so if I get
it Monday I can report back Wednesday.

Priya: Works. Sara, where are we on design?

Sara: The new onboarding flow is finished and in Figma. But I'm blocked on the
empty states — I still don't have final copy from Meera, and she's out today. It's
been about a week now.

Priya: I'll chase Meera on the copy. That's becoming a real risk, we can't ship
onboarding with placeholder text.

Sara: One more thing — should the onboarding flow be skippable? We went back and
forth on it last sprint and never actually settled it.

Priya: Good question. Let's park that and decide next week when we have usage data
from the beta group.

Dev: On QA — I've filed nineteen bugs, fourteen are closed. The five open ones are
all cosmetic, nothing blocking. But I want to flag that we still have no automated
regression suite for the checkout path. We're testing it by hand every release and
it's going to bite us.

Priya: Agreed, that's a gap. Dev, can you scope what it would take to automate it?
Not to build it now, just an estimate.

Dev: Sure, I'll put together an estimate by end of month.

Priya: Last thing — are we still targeting the 28th for release?

Arjun: If the phased migration tests clean, yes. If not we'd need to slip a week.

Priya: Let's plan for the 28th and treat Wednesday's test result as the go/no-go.
I'll book a short call Wednesday afternoon to make the call.

Sara: Sounds good.

Priya: Great, thanks everyone."""


# --------------------------------------------------------------------------- #
# Reusable UI fragments
# --------------------------------------------------------------------------- #


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero fade-in">
            <div class="hero-eyebrow">✦ AI-Powered Documentation</div>
            <h1 class="hero-title">Turn messy notes into<br><em>board-ready minutes</em></h1>
            <p class="hero-sub">
                Paste a transcript or upload a file. The agent identifies discussion
                points, extracts decisions, assigns responsibilities with deadlines,
                and flags risks — then exports it all as a polished document.
            </p>
            <div class="hero-chips">
                <span class="hero-chip">Information Extraction</span>
                <span class="hero-chip">Structured JSON Output</span>
                <span class="hero-chip">Action Item Tracking</span>
                <span class="hero-chip">DOCX / MD / CSV Export</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(meta) -> None:
    if meta is None:
        return
    if meta.mode == "live":
        st.markdown(
            f'<span class="badge badge-live"><span class="pulse"></span>'
            f"Live · {meta.model.split('/')[-1]} · {meta.elapsed:.1f}s</span>",
            unsafe_allow_html=True,
        )
    elif meta.mode == "offline":
        st.markdown(
            '<span class="badge badge-off">◆ Offline demo mode — rule-based extraction</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<span class="badge badge-err">✕ API error — showing offline draft</span>',
                    unsafe_allow_html=True)


def render_metrics(d: dict) -> None:
    cards = [
        (len(d.get("attendees", [])), "Attendees"),
        (len(d.get("discussion_points", [])), "Topics"),
        (len(d.get("decisions", [])), "Decisions"),
        (len(d.get("action_items", [])), "Actions"),
        (len(d.get("risks_and_blockers", [])), "Risks"),
        (len(d.get("open_questions", [])), "Questions"),
    ]
    html = '<div class="metric-row">'
    for value, label in cards:
        html += (
            f'<div class="metric"><div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def esc(text) -> str:
    """Minimal HTML escaping for values interpolated into markup."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_minutes(d: dict) -> None:
    """Render the minutes as a styled document."""
    head = f"""
    <div class="doc fade-in">
      <div class="doc-header">
        <h2 class="doc-title">{esc(d.get('title', 'Meeting Minutes'))}</h2>
        <div class="doc-meta">
          <div class="doc-meta-item">
            <span class="doc-meta-key">Date</span>
            <span class="doc-meta-val">{esc(d.get('meeting_date', 'Not stated'))}</span>
          </div>
          <div class="doc-meta-item">
            <span class="doc-meta-key">Duration</span>
            <span class="doc-meta-val">{esc(d.get('duration', 'Not stated'))}</span>
          </div>
          <div class="doc-meta-item">
            <span class="doc-meta-key">Next Meeting</span>
            <span class="doc-meta-val">{esc(d.get('next_meeting', 'Not scheduled'))}</span>
          </div>
        </div>
      </div>
      <div class="doc-body">
    """

    body = ""

    if d.get("attendees") or d.get("absentees"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += '<p class="mblock-title">Attendance</p></div>'
        for person in d.get("attendees", []):
            body += f'<span class="pill">● {esc(person)}</span>'
        for person in d.get("absentees", []):
            body += f'<span class="pill pill-out">○ {esc(person)} (apologies)</span>'
        body += "</div>"

    if d.get("executive_summary"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += '<p class="mblock-title">Executive Summary</p></div>'
        body += f'<div class="summary-text">{esc(d["executive_summary"])}</div></div>'

    if d.get("agenda_items"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += f'<p class="mblock-title">Agenda</p><span class="mblock-count">{len(d["agenda_items"])}</span></div>'
        body += '<div class="topic"><ul>'
        for item in d["agenda_items"]:
            body += f"<li>{esc(item)}</li>"
        body += "</ul></div></div>"

    if d.get("discussion_points"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += f'<p class="mblock-title">Discussion</p><span class="mblock-count">{len(d["discussion_points"])}</span></div>'
        for block in d["discussion_points"]:
            body += f'<div class="topic"><div class="topic-name">{esc(block.get("topic", ""))}</div><ul>'
            for point in block.get("points", []):
                body += f"<li>{esc(point)}</li>"
            body += "</ul></div>"
        body += "</div>"

    if d.get("decisions"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += f'<p class="mblock-title">Decisions</p><span class="mblock-count">{len(d["decisions"])}</span></div>'
        for i, dec in enumerate(d["decisions"], 1):
            body += f'<div class="dec"><div class="dec-num">{i}</div><div>'
            body += f'<div class="dec-text">{esc(dec.get("decision", ""))}</div>'
            if dec.get("rationale"):
                body += f'<div class="dec-why">Rationale: {esc(dec["rationale"])}</div>'
            if dec.get("owner") and dec["owner"] != "Unassigned":
                body += f'<div class="dec-owner">OWNER: {esc(dec["owner"])}</div>'
            body += "</div></div>"
        body += "</div>"

    if d.get("risks_and_blockers"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += f'<p class="mblock-title">Risks &amp; Blockers</p><span class="mblock-count">{len(d["risks_and_blockers"])}</span></div>'
        for risk in d["risks_and_blockers"]:
            body += f'<div class="risk"><div class="risk-text">{esc(risk.get("item", ""))}</div>'
            detail = []
            if risk.get("impact"):
                detail.append(f"Impact: {esc(risk['impact'])}")
            if risk.get("owner") and risk["owner"] != "Unassigned":
                detail.append(f"Owner: {esc(risk['owner'])}")
            if detail:
                body += f'<div class="risk-impact">{" · ".join(detail)}</div>'
            body += "</div>"
        body += "</div>"

    if d.get("open_questions"):
        body += '<div class="mblock"><div class="mblock-head">'
        body += f'<p class="mblock-title">Open Questions</p><span class="mblock-count">{len(d["open_questions"])}</span></div>'
        for q in d["open_questions"]:
            body += f'<div class="q"><span class="q-mark">?</span><span>{esc(q)}</span></div>'
        body += "</div>"

    st.markdown(head + body + "</div></div>", unsafe_allow_html=True)

    # Action items get a real dataframe — sortable and easy to scan.
    if d.get("action_items"):
        st.markdown("")
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Action Items</h3>'
            f'<p class="section-hint">{len(d["action_items"])} tasks extracted</p></div>',
            unsafe_allow_html=True,
        )
        rows = [
            {
                "#": i,
                "Task": a.get("task", ""),
                "Owner": a.get("owner", "Unassigned"),
                "Deadline": a.get("deadline", "—"),
                "Priority": a.get("priority", "Medium"),
            }
            for i, a in enumerate(d["action_items"], 1)
        ]
        st.dataframe(
            rows,
            width="stretch",
            hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn(width="small"),
                "Task": st.column_config.TextColumn(width="large"),
                "Owner": st.column_config.TextColumn(width="small"),
                "Deadline": st.column_config.TextColumn(width="small"),
                "Priority": st.column_config.TextColumn(width="small"),
            },
        )

        unassigned = sum(1 for a in d["action_items"] if a.get("owner") == "Unassigned")
        undated = sum(1 for a in d["action_items"] if a.get("deadline") == "No deadline stated")
        if unassigned or undated:
            notes = []
            if unassigned:
                notes.append(f"**{unassigned}** action{'s' if unassigned != 1 else ''} without an owner")
            if undated:
                notes.append(f"**{undated}** without a deadline")
            st.info(
                "⚠︎ " + " and ".join(notes) +
                " — the transcript did not make these clear. Worth following up."
            )


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #


def render_sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-mark">📝</div>
                <div>
                    <div class="sidebar-name">Minutes Generator</div>
                    <div class="sidebar-tag">AI meeting documentation</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if HAS_OPTION_MENU:
            page = option_menu(
                menu_title=None,
                options=["Generate", "History", "About"],
                icons=["magic", "clock-history", "info-circle"],
                default_index=["Generate", "History", "About"].index(st.session_state.page),
                styles={
                    "container": {"padding": "0.4rem 0", "background-color": "transparent"},
                    "icon": {"font-size": "0.95rem"},
                    "nav-link": {
                        "font-size": "0.9rem",
                        "font-weight": "600",
                        "color": "#64748B",
                        "padding": "0.65rem 0.9rem",
                        "border-radius": "10px",
                        "margin": "0.15rem 0",
                        "--hover-color": "#F1F5F9",
                    },
                    "nav-link-selected": {
                        "background": "linear-gradient(115deg,#6D5EF8,#8B5CF6)",
                        "color": "white",
                        "font-weight": "700",
                    },
                },
            )
        else:
            page = st.radio("Navigate", ["Generate", "History", "About"], label_visibility="collapsed")

        st.session_state.page = page

        st.markdown("---")
        st.markdown("**⚙︎ Model Settings**")

        model = st.selectbox(
            "Model",
            options=list(llm.AVAILABLE_MODELS.keys()),
            format_func=lambda m: llm.AVAILABLE_MODELS[m],
            index=0,
            help="Groq-hosted models. GPT-OSS 120B gives the best extraction quality.",
        )

        api_key = st.text_input(
            "Groq API key",
            type="password",
            placeholder="gsk_...",
            help="Optional if GROQ_API_KEY is set in your environment or .env file. "
                 "Nothing typed here is written to disk.",
        )

        detected = llm.get_api_key(api_key)
        if detected:
            st.markdown(
                '<span class="badge badge-live"><span class="pulse"></span>API key detected</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="badge badge-off">◆ No key — offline mode</span>',
                unsafe_allow_html=True,
            )
            st.caption("Get a free key at console.groq.com/keys")

        if st.button("⚡ Test connection", width="stretch"):
            with st.spinner("Pinging Groq…"):
                ok, message = llm.health_check(api_key, model)
            if ok:
                st.success(message)
            else:
                st.error(message)

        st.markdown("---")
        st.caption(
            f"Session: **{len(st.session_state.history)}** minutes generated  \n"
            f"{datetime.now().strftime('%d %b %Y')}"
        )

    return st.session_state.page, api_key, model


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #


def page_generate(api_key: str, model: str) -> None:
    render_hero()

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Input</h3>'
            '<p class="section-hint">Paste, upload, or try the sample</p></div>',
            unsafe_allow_html=True,
        )

        tab_paste, tab_upload = st.tabs(["✎  Paste text", "⬆  Upload file"])

        with tab_paste:
            transcript = st.text_area(
                "Transcript",
                value=st.session_state.get("transcript", ""),
                height=290,
                placeholder=(
                    "Paste your meeting transcript or raw notes here…\n\n"
                    "Speaker labels help but are not required:\n"
                    "  Priya: Let's review the timeline.\n"
                    "  Arjun: Backend is done, migration is the risk."
                ),
                label_visibility="collapsed",
            )
            # Keep session state in sync with manual typing.
            if transcript != st.session_state.transcript:
                st.session_state.transcript = transcript

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📄 Load sample", width="stretch"):
                    st.session_state.transcript = SAMPLE_TRANSCRIPT
                    st.rerun()
            with col_b:
                if st.button("🗑 Clear", width="stretch"):
                    st.session_state.transcript = ""
                    st.session_state.minutes = None
                    st.session_state.meta = None
                    st.rerun()

        with tab_upload:
            uploaded = st.file_uploader(
                "Upload a transcript",
                type=["txt", "md", "vtt", "srt", "log", "csv"],
                help="Plain text formats. VTT/SRT subtitle files are cleaned automatically.",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                try:
                    raw = uploaded.read().decode("utf-8", errors="replace")
                    if uploaded.name.lower().endswith((".vtt", ".srt")):
                        raw = _clean_subtitles(raw)
                    transcript = raw
                    st.session_state.transcript = raw
                    st.success(f"Loaded **{uploaded.name}** — {len(raw.split()):,} words")
                    with st.expander("Preview"):
                        st.text(raw[:1500] + ("…" if len(raw) > 1500 else ""))
                except Exception as exc:
                    st.error(f"Could not read that file: {exc}")

        transcript = st.session_state.transcript or transcript

        if transcript.strip():
            words = len(transcript.split())
            st.caption(f"**{words:,}** words · **{len(transcript):,}** characters")

        with st.expander("⚙︎ Meeting context (optional)"):
            meeting_title = st.text_input("Meeting title", placeholder="Q3 Planning Review")
            meeting_date = st.text_input("Date", placeholder="12 March 2026")
            known_attendees = st.text_input(
                "Known attendees", placeholder="Priya Menon, Arjun Rao, Sara Fernandes"
            )

        st.markdown("**Meeting type**")
        meeting_type = st.selectbox(
            "Meeting type",
            options=list(prompts.MEETING_TYPES.keys()),
            format_func=lambda k: prompts.MEETING_TYPES[k]["label"],
            label_visibility="collapsed",
        )
        st.caption(prompts.MEETING_TYPES[meeting_type]["description"])

        st.markdown("**Detail level**")
        detail_level = st.select_slider(
            "Detail level",
            options=list(prompts.DETAIL_LEVELS.keys()),
            value=prompts.DEFAULT_DETAIL_LEVEL,
            format_func=lambda k: prompts.DETAIL_LEVELS[k]["label"],
            label_visibility="collapsed",
        )
        st.caption(prompts.DETAIL_LEVELS[detail_level]["description"])

        st.markdown("")
        generate = st.button(
            "✨  Generate Minutes",
            type="primary",
            width="stretch",
            disabled=not transcript.strip(),
        )

    with right:
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Output</h3>'
            '<p class="section-hint">Structured minutes appear here</p></div>',
            unsafe_allow_html=True,
        )

        if generate and transcript.strip():
            with st.spinner("Reading the transcript and extracting structure…"):
                result = llm.generate_minutes(
                    transcript=transcript,
                    meeting_type=meeting_type,
                    detail_level=detail_level,
                    meeting_title=meeting_title,
                    meeting_date=meeting_date,
                    known_attendees=known_attendees,
                    api_key_override=api_key,
                    model=model,
                )
            st.session_state.minutes = result.data
            st.session_state.meta = result

            if result.ok:
                st.session_state.history.insert(
                    0,
                    {
                        "data": result.data,
                        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M"),
                        "mode": result.mode,
                        "type": prompts.MEETING_TYPES[meeting_type]["label"],
                    },
                )
                st.session_state.history = st.session_state.history[:20]

        if st.session_state.minutes:
            meta = st.session_state.meta
            render_status_badge(meta)

            if meta and meta.error:
                st.error(f"**{meta.error}**")
            for warning in (meta.warnings if meta else []):
                st.warning(warning)

            st.markdown("")
            render_metrics(st.session_state.minutes)
        else:
            st.markdown(
                """
                <div class="empty">
                    <div class="empty-icon">🗒️</div>
                    <div class="empty-title">No minutes yet</div>
                    <p class="empty-text">
                        Add a transcript on the left and hit Generate. Try the sample
                        if you just want to see what it produces.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Full-width document below the two columns.
    if st.session_state.minutes:
        st.markdown("---")
        render_minutes(st.session_state.minutes)
        render_toolbar(api_key, model)


def render_toolbar(api_key: str, model: str) -> None:
    """Refinement buttons and export options."""
    d = st.session_state.minutes

    st.markdown("---")
    st.markdown(
        '<div class="section-head"><h3 class="section-title">Refine</h3>'
        '<p class="section-hint">Adjust the minutes without re-reading the transcript</p></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(prompts.REFINEMENT_ACTIONS))
    for col, (key, action) in zip(cols, prompts.REFINEMENT_ACTIONS.items()):
        with col:
            if st.button(action["label"], width="stretch", key=f"refine_{key}"):
                with st.spinner(f"{action['label']}…"):
                    result = llm.refine_minutes(d, action["instruction"], api_key, model)
                if result.ok and result.mode == "live":
                    st.session_state.minutes = result.data
                    st.session_state.meta = result
                    st.rerun()
                else:
                    st.error(result.error or "Refinement failed.")

    with st.expander("✎ Custom revision instruction"):
        custom = st.text_input(
            "Instruction",
            placeholder="e.g. Merge the two migration topics; drop the cosmetic bug detail",
            label_visibility="collapsed",
        )
        if st.button("Apply revision") and custom.strip():
            with st.spinner("Revising…"):
                result = llm.refine_minutes(d, custom.strip(), api_key, model)
            if result.ok and result.mode == "live":
                st.session_state.minutes = result.data
                st.session_state.meta = result
                st.rerun()
            else:
                st.error(result.error or "Revision failed.")

    st.markdown("---")
    st.markdown(
        '<div class="section-head"><h3 class="section-title">Export</h3>'
        '<p class="section-hint">Download in the format you need</p></div>',
        unsafe_allow_html=True,
    )

    title = d.get("title", "meeting_minutes")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.download_button(
            "⬇ Word (.docx)",
            data=export_utils.to_docx(d),
            file_name=export_utils.safe_filename(title, "docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
    with c2:
        st.download_button(
            "⬇ Markdown",
            data=export_utils.to_markdown(d),
            file_name=export_utils.safe_filename(title, "md"),
            mime="text/markdown",
            width="stretch",
        )
    with c3:
        st.download_button(
            "⬇ Actions (.csv)",
            data=export_utils.actions_to_csv(d),
            file_name=export_utils.safe_filename(title + "_actions", "csv"),
            mime="text/csv",
            width="stretch",
            disabled=not d.get("action_items"),
        )
    with c4:
        st.download_button(
            "⬇ JSON",
            data=export_utils.to_json(d),
            file_name=export_utils.safe_filename(title, "json"),
            mime="application/json",
            width="stretch",
        )

    with st.expander("📋 Copy as plain text"):
        st.code(export_utils.to_text(d), language=None)

    with st.expander("🔍 Structured data (what the agent extracted)"):
        st.caption(
            "This is the raw JSON the model returned after normalisation — the "
            "information-extraction layer that everything else is rendered from."
        )
        st.json(d)


def page_history() -> None:
    st.markdown(
        '<div class="section-head"><h3 class="section-title">Session History</h3>'
        '<p class="section-hint">The last 20 sets of minutes from this session</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.history:
        st.markdown(
            """
            <div class="empty">
                <div class="empty-icon">🕐</div>
                <div class="empty-title">Nothing here yet</div>
                <p class="empty-text">
                    Minutes you generate will be listed here so you can reload them.
                    History lives in the browser session only.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for i, entry in enumerate(st.session_state.history):
        d = entry["data"]
        with st.container():
            col_main, col_btn = st.columns([5, 1])
            with col_main:
                mode_icon = "●" if entry["mode"] == "live" else "◆"
                st.markdown(
                    f"""
                    <div class="hist-item">
                        <div class="hist-title">{esc(d.get('title', 'Untitled'))}</div>
                        <div class="hist-meta">
                            {mode_icon} {entry['timestamp']} · {esc(entry['type'])} ·
                            {len(d.get('decisions', []))} decisions ·
                            {len(d.get('action_items', []))} actions
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button("Reload", key=f"reload_{i}", width="stretch"):
                    st.session_state.minutes = d
                    st.session_state.meta = None
                    st.session_state.page = "Generate"
                    st.rerun()

    st.markdown("")
    if st.button("🗑 Clear history"):
        st.session_state.history = []
        st.rerun()


def page_about() -> None:
    st.markdown(
        '<div class="section-head"><h3 class="section-title">About this project</h3>'
        '<p class="section-hint">Architecture and design decisions</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card">
            <div class="card-label">◈ What it does</div>
            The agent converts unstructured meeting transcripts into structured,
            professional minutes. Rather than producing a prose summary, it performs
            <strong>information extraction</strong> — identifying discrete decisions,
            action items with owners and deadlines, risks, and unresolved questions,
            each as a typed field in a JSON object. Everything you see rendered, and
            every export format, is generated from that one structured object.
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="card">
                <div class="card-label">◈ Architecture</div>
                <strong>app.py</strong> — Streamlit UI, routing, state<br>
                <strong>prompts.py</strong> — all prompt engineering<br>
                <strong>llm.py</strong> — Groq client, JSON parsing, fallback<br>
                <strong>export_utils.py</strong> — DOCX/MD/TXT/CSV/JSON<br>
                <strong>styles.py</strong> — design system CSS
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="card">
                <div class="card-label">◈ Techniques used</div>
                Schema-constrained generation (JSON mode)<br>
                Role prompting with explicit anti-hallucination rules<br>
                Map-reduce chunking for long transcripts<br>
                Multi-strategy JSON recovery parsing<br>
                Graceful degradation to rule-based extraction
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="card">
            <div class="card-label">◈ Why structured output matters</div>
            Asking a model for "a summary" gives you prose you must re-read. Asking for
            a <em>schema</em> gives you data: action items become a sortable table and a
            CSV you can import into a tracker; unassigned owners can be counted and
            flagged; the same extraction renders as Word, Markdown, or JSON without
            calling the model again. This is the difference between summarisation and
            information extraction, and it is the core idea the project demonstrates.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card">
            <div class="card-label">◈ Honest limitations</div>
            The agent can only extract what the transcript states. Owners and deadlines
            left implicit in conversation will surface as "Unassigned" — a deliberate
            choice, since a wrong name is worse than a visible gap. Offline mode is
            keyword-based and included so the interface can be demonstrated without an
            API key; it is not a substitute for the model. History is session-only and
            is lost on refresh.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="footer-note">AI Meeting Minutes Generator<br>'
        "Built with Streamlit · Powered by Groq</div>",
        unsafe_allow_html=True,
    )


def _clean_subtitles(text: str) -> str:
    """Strip VTT/SRT timing lines and indices, keeping the spoken text."""
    import re

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "WEBVTT" or stripped.isdigit():
            continue
        if "-->" in stripped:
            continue
        stripped = re.sub(r"<[^>]+>", "", stripped)
        lines.append(stripped)

    # Collapse consecutive duplicates, common in auto-generated captions.
    deduped = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    page, api_key, model = render_sidebar()

    if page == "Generate":
        page_generate(api_key, model)
    elif page == "History":
        page_history()
    else:
        page_about()


if __name__ == "__main__":
    main()
