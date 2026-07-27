"""
app.py
======
AI Event Planning Agent — Streamlit front end.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

import budget as budget_mod
import export_utils
import llm
import prompts
from styles import CSS

st.set_page_config(
    page_title="AI Event Planning Agent",
    page_icon="🎉",
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
    "plan": None,
    "meta": None,
    "history": [],
    "page": "Plan",
    "ctx": {},          # the brief used for the current plan
    "contingency": 10,
    "scale_factor": 1.0,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# Category colours for the budget bar.
CAT_COLORS = {
    "Venue": "#F2542D",
    "Catering": "#F2A104",
    "Decoration": "#7B2D5E",
    "Equipment & AV": "#0E9594",
    "Marketing & Printing": "#1B998B",
    "Speakers & Talent": "#D62246",
    "Prizes & Gifts": "#B5651D",
    "Transport & Logistics": "#5B7C99",
    "Staffing & Security": "#4A3B2A",
    "Miscellaneous": "#A89684",
}


def esc(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------- #
# UI fragments
# --------------------------------------------------------------------------- #


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero fade-in">
            <div class="hero-eyebrow">✦ Planning &amp; Task Organisation</div>
            <h1 class="hero-title">From a one-line brief to a<br><em>complete event plan</em></h1>
            <p class="hero-sub">
                Describe your event — type, size, budget, date. The agent builds a
                phased checklist with owners and deadlines, a costed budget, venue
                options, equipment lists, an invitation strategy and a risk register.
            </p>
            <div class="hero-chips">
                <span class="hero-chip">Phased Checklist</span>
                <span class="hero-chip">Computed Budget</span>
                <span class="hero-chip">Venue &amp; Equipment</span>
                <span class="hero-chip">Timeline &amp; Risks</span>
                <span class="hero-chip">DOCX / CSV Export</span>
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
            '<span class="badge badge-off">◆ Offline demo mode — template planner</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-err">✕ API error — showing offline template</span>',
            unsafe_allow_html=True,
        )


def render_metrics(plan: dict, bud, symbol: str) -> None:
    essential = sum(1 for e in plan.get("equipment", []) if e.get("essential"))
    cards = [
        (f"{symbol}{bud.grand_total:,.0f}", "Total Cost"),
        (f"{symbol}{bud.per_head:,.0f}", "Per Head"),
        (str(len(plan.get("checklist", []))), "Tasks"),
        (str(len(plan.get("timeline", []))), "Milestones"),
        (str(essential), "Essentials"),
        (str(len(plan.get("risks", []))), "Risks"),
    ]
    html = '<div class="metric-row">'
    for value, label in cards:
        html += (
            f'<div class="metric"><div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_budget_bar(bud, symbol: str) -> None:
    """Stacked proportional bar showing spend by category."""
    if not bud.by_category or bud.subtotal <= 0:
        return
    ordered = sorted(bud.by_category.items(), key=lambda kv: -kv[1])
    html = '<div class="bud-bar">'
    for cat, amount in ordered:
        pct = amount / bud.subtotal * 100
        color = CAT_COLORS.get(cat, "#A89684")
        label = f"{pct:.0f}%" if pct >= 7 else ""
        html += (
            f'<div class="bud-seg" style="width:{pct}%;background:{color}" '
            f'title="{esc(cat)}: {symbol}{amount:,.0f} ({pct:.1f}%)">{label}</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    legend = ""
    for cat, amount in ordered:
        color = CAT_COLORS.get(cat, "#A89684")
        pct = bud.category_pct.get(cat, 0)
        legend += (
            f'<span class="pill"><span style="display:inline-block;width:8px;height:8px;'
            f'border-radius:2px;background:{color};margin-right:.4rem"></span>'
            f"{esc(cat)} · {symbol}{amount:,.0f} ({pct:.0f}%)</span>"
        )
    st.markdown(legend, unsafe_allow_html=True)


def render_plan(plan: dict, bud, symbol: str, event_date: str, attendees: int) -> None:
    """Render the plan as a styled document."""
    meta_items = []
    if event_date:
        meta_items.append(("Date", event_date))
    if attendees:
        meta_items.append(("Attendees", str(attendees)))
    meta_items.append(("Estimated Cost", f"{symbol}{bud.grand_total:,.0f}"))
    if attendees:
        meta_items.append(("Per Head", f"{symbol}{bud.per_head:,.0f}"))

    head = f"""
    <div class="doc fade-in">
      <div class="doc-header">
        <h2 class="doc-title">{esc(plan.get('event_title', 'Event Plan'))}</h2>
        <div class="doc-meta">
    """
    for key, value in meta_items:
        head += (
            f'<div class="doc-meta-item"><span class="doc-meta-key">{esc(key)}</span>'
            f'<span class="doc-meta-val">{esc(value)}</span></div>'
        )
    head += '</div></div><div class="doc-body">'

    body = ""

    if plan.get("summary"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Overview</p></div>'
        body += f'<div class="summary-text">{esc(plan["summary"])}</div></div>'

    venue = plan.get("venue", {})
    if venue.get("recommendations"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Venue Options</p>'
        body += f'<span class="mblock-count">{len(venue["recommendations"])}</span></div>'
        for rec in venue["recommendations"]:
            try:
                cost = float(rec.get("est_cost") or 0)
                cost_str = f"{symbol}{cost:,.0f}" if cost > 0 else "—"
            except (TypeError, ValueError):
                cost_str = "—"
            body += '<div class="venue"><div class="venue-name">'
            body += f'<span>{esc(rec.get("option", ""))}</span><span class="venue-cost">{cost_str}</span></div>'
            if rec.get("why"):
                body += f'<div class="venue-why">{esc(rec["why"])}</div>'
            if rec.get("capacity_fit"):
                body += f'<div class="venue-fit">{esc(rec["capacity_fit"])}</div>'
            body += "</div>"
        body += "</div>"

    if venue.get("layout") or venue.get("requirements"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Venue Setup</p></div>'
        if venue.get("layout"):
            body += f'<div class="venue-why" style="margin-bottom:.8rem">{esc(venue["layout"])}</div>'
        for req in venue.get("requirements", []):
            body += f'<span class="pill">✓ {esc(req)}</span>'
        body += "</div>"

    if plan.get("timeline"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Timeline</p>'
        body += f'<span class="mblock-count">{len(plan["timeline"])}</span></div><div class="tl">'
        for ms in plan["timeline"]:
            when = export_utils.fmt_days(ms["days_before_event"])
            date_str = export_utils.actual_date(event_date, ms["days_before_event"])
            body += '<div class="tl-item">'
            body += f'<div class="tl-when">{esc(when)}{" · " + esc(date_str) if date_str else ""}</div>'
            body += f'<div class="tl-name">{esc(ms["milestone"])}</div>'
            if ms.get("detail"):
                body += f'<div class="tl-detail">{esc(ms["detail"])}</div>'
            body += "</div>"
        body += "</div></div>"

    inv = plan.get("invitations", {})
    if inv.get("channels") or inv.get("sample_message"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Invitations</p></div>'
        for channel in inv.get("channels", []):
            body += f'<span class="pill">✉ {esc(channel)}</span>'
        if inv.get("send_schedule"):
            body += f'<div class="venue-why" style="margin-top:.7rem"><strong>Schedule:</strong> {esc(inv["send_schedule"])}</div>'
        if inv.get("rsvp_method"):
            body += f'<div class="venue-why" style="margin-top:.35rem"><strong>RSVP:</strong> {esc(inv["rsvp_method"])}</div>'
        if inv.get("sample_message"):
            body += f'<div class="invite-box" style="margin-top:.9rem">“{esc(inv["sample_message"])}”</div>'
        body += "</div>"

    if plan.get("risks"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Risk Register</p>'
        body += f'<span class="mblock-count">{len(plan["risks"])}</span></div>'
        for risk in plan["risks"]:
            body += '<div class="risk"><div class="risk-top">'
            body += f'<span class="risk-text">{esc(risk["risk"])}</span>'
            body += f'<span class="risk-lik">{esc(risk["likelihood"])}</span></div>'
            if risk.get("mitigation"):
                body += f'<div class="risk-fix">→ {esc(risk["mitigation"])}</div>'
            body += "</div>"
        body += "</div>"

    if plan.get("tips"):
        body += '<div class="mblock"><div class="mblock-head"><p class="mblock-title">Planner Tips</p></div>'
        for tip in plan["tips"]:
            body += f'<div class="tip"><span class="tip-mark">◆</span><span>{esc(tip)}</span></div>'
        body += "</div>"

    st.markdown(head + body + "</div></div>", unsafe_allow_html=True)


def render_checklist(plan: dict, event_date: str) -> None:
    """Phase-grouped checklist with interactive completion tracking."""
    tasks = plan.get("checklist", [])
    if not tasks:
        return

    done_key = "done_tasks"
    if done_key not in st.session_state:
        st.session_state[done_key] = set()

    completed = len(st.session_state[done_key])
    total = len(tasks)

    st.markdown(
        '<div class="section-head"><h3 class="section-title">Checklist</h3>'
        f'<p class="section-hint">{completed} of {total} complete</p></div>',
        unsafe_allow_html=True,
    )
    st.progress(completed / total if total else 0.0)

    phases: dict[str, list] = {}
    for i, task in enumerate(tasks):
        phases.setdefault(task["phase"], []).append((i, task))

    for phase in prompts.CHECKLIST_PHASES:
        if phase not in phases:
            continue
        st.markdown(
            f'<div class="phase-head">{esc(phase)}<span class="phase-line"></span></div>',
            unsafe_allow_html=True,
        )
        for i, task in phases[phase]:
            when = export_utils.fmt_days(task["days_before_event"])
            date_str = export_utils.actual_date(event_date, task["days_before_event"])
            col_check, col_body = st.columns([0.045, 0.955])
            with col_check:
                checked = st.checkbox(
                    "done",
                    value=i in st.session_state[done_key],
                    key=f"task_{i}",
                    label_visibility="collapsed",
                )
                if checked:
                    st.session_state[done_key].add(i)
                else:
                    st.session_state[done_key].discard(i)
            with col_body:
                strike = "text-decoration:line-through;opacity:.5" if checked else ""
                st.markdown(
                    f"""
                    <div class="task" style="{strike}">
                        <span class="task-when">{esc(when)}</span>
                        <div class="task-body">
                            <div class="task-text">{esc(task['task'])}</div>
                            <div class="task-owner">{esc(task['owner_role'])}
                            {' · ' + esc(date_str) if date_str else ''}</div>
                        </div>
                        <span class="prio prio-{esc(task['priority'])}">{esc(task['priority'])}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #


def render_sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-mark">🎉</div>
                <div>
                    <div class="sidebar-name">Event Planner</div>
                    <div class="sidebar-tag">AI planning &amp; organisation</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if HAS_OPTION_MENU:
            page = option_menu(
                menu_title=None,
                options=["Plan", "Checklist", "Budget", "History", "About"],
                icons=["stars", "check2-square", "cash-coin", "clock-history", "info-circle"],
                default_index=["Plan", "Checklist", "Budget", "History", "About"].index(
                    st.session_state.page
                ),
                styles={
                    "container": {"padding": "0.4rem 0", "background-color": "transparent"},
                    "icon": {"font-size": "0.95rem"},
                    "nav-link": {
                        "font-size": "0.9rem",
                        "font-weight": "600",
                        "color": "#8A7563",
                        "padding": "0.6rem 0.9rem",
                        "border-radius": "11px",
                        "margin": "0.12rem 0",
                        "--hover-color": "#F5EFE8",
                    },
                    "nav-link-selected": {
                        "background": "linear-gradient(118deg,#F2542D,#F2A104)",
                        "color": "white",
                        "font-weight": "700",
                    },
                },
            )
        else:
            page = st.radio(
                "Navigate",
                ["Plan", "Checklist", "Budget", "History", "About"],
                label_visibility="collapsed",
            )

        st.session_state.page = page

        st.markdown("---")
        st.markdown("**⚙︎ Model Settings**")

        model = st.selectbox(
            "Model",
            options=list(llm.AVAILABLE_MODELS.keys()),
            format_func=lambda m: llm.AVAILABLE_MODELS[m],
            index=0,
        )
        api_key = st.text_input(
            "Groq API key",
            type="password",
            placeholder="gsk_...",
            help="Optional if GROQ_API_KEY is set in your environment or .env file. "
                 "Nothing typed here is written to disk.",
        )

        if llm.get_api_key(api_key):
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
            st.success(message) if ok else st.error(message)

        st.markdown("---")
        st.caption(
            f"Session: **{len(st.session_state.history)}** plans generated  \n"
            f"{datetime.now().strftime('%d %b %Y')}"
        )

    return st.session_state.page, api_key, model


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #


def page_plan(api_key: str, model: str) -> None:
    render_hero()

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Event Brief</h3>'
            '<p class="section-hint">Tell the agent what you are planning</p></div>',
            unsafe_allow_html=True,
        )

        event_type = st.selectbox(
            "Event type",
            options=list(prompts.EVENT_TYPES.keys()),
            format_func=lambda k: f"{prompts.EVENT_TYPES[k]['icon']}  {prompts.EVENT_TYPES[k]['label']}",
            index=list(prompts.EVENT_TYPES.keys()).index(prompts.DEFAULT_EVENT_TYPE),
        )
        st.caption(prompts.EVENT_TYPES[event_type]["description"])

        event_name = st.text_input(
            "Event name", placeholder="e.g. TechFest 2026 — Annual Coding Summit"
        )

        c1, c2 = st.columns(2)
        with c1:
            attendees = st.number_input(
                "Expected attendees", min_value=1, max_value=100_000, value=150, step=10
            )
        with c2:
            currency = st.selectbox("Currency", options=list(llm.CURRENCIES.keys()), index=0)

        symbol = llm.CURRENCIES[currency]
        band, _ = prompts.scale_for(int(attendees))
        st.caption(f"Scale band: **{band}** — the plan adapts its depth to this size.")

        total_budget = st.number_input(
            f"Total budget ({symbol})",
            min_value=0.0,
            max_value=1e9,
            value=75_000.0,
            step=5_000.0,
            help="Set 0 to let the agent propose a budget.",
        )

        c3, c4 = st.columns(2)
        with c3:
            event_date_obj = st.date_input(
                "Event date", value=date.today() + timedelta(days=45), format="DD/MM/YYYY"
            )
        with c4:
            duration = st.text_input("Duration", placeholder="e.g. 1 day, 6 hours")

        location = st.text_input(
            "Location / city", placeholder="e.g. Hyderabad, India", value="Hyderabad, India"
        )

        formality = st.select_slider(
            "Formality",
            options=["Casual", "Semi-formal", "Formal"],
            value="Semi-formal",
        )

        notes = st.text_area(
            "Special requirements (optional)",
            height=110,
            placeholder=(
                "e.g. Vegetarian catering only. Need a stage for cultural events. "
                "Two guest speakers travelling from Bangalore. Must finish before 6pm."
            ),
        )

        st.markdown("")
        generate = st.button("✨  Generate Event Plan", type="primary", width="stretch")

    with right:
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Plan</h3>'
            '<p class="section-hint">Your plan summary appears here</p></div>',
            unsafe_allow_html=True,
        )

        if generate:
            event_date_str = event_date_obj.strftime("%d %B %Y") if event_date_obj else ""
            with st.spinner("Planning your event — venue, budget, checklist, timeline…"):
                result = llm.generate_plan(
                    event_type=event_type,
                    event_name=event_name,
                    attendees=int(attendees),
                    budget=float(total_budget),
                    currency=currency,
                    location=location,
                    event_date=event_date_str,
                    duration=duration,
                    notes=notes,
                    formality=formality,
                    api_key_override=api_key,
                    model=model,
                )
            st.session_state.plan = result.data
            st.session_state.meta = result
            st.session_state.ctx = {
                "event_type": event_type,
                "attendees": int(attendees),
                "budget": float(total_budget),
                "currency": currency,
                "symbol": symbol,
                "event_date": event_date_str,
                "location": location,
            }
            st.session_state.done_tasks = set()
            st.session_state.scale_factor = 1.0

            if result.ok:
                st.session_state.history.insert(
                    0,
                    {
                        "data": result.data,
                        "ctx": dict(st.session_state.ctx),
                        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M"),
                        "mode": result.mode,
                        "type": prompts.EVENT_TYPES[event_type]["label"],
                    },
                )
                st.session_state.history = st.session_state.history[:20]

        if st.session_state.plan:
            meta = st.session_state.meta
            ctx = st.session_state.ctx
            render_status_badge(meta)

            if meta and meta.error:
                st.error(f"**{meta.error}**")
            for warning in (meta.warnings if meta else []):
                st.warning(warning)

            bud = budget_mod.build_budget(
                st.session_state.plan.get("budget_items", []),
                target=ctx.get("budget", 0),
                attendees=ctx.get("attendees", 1),
                contingency_pct=st.session_state.contingency,
            )
            st.markdown("")
            render_metrics(st.session_state.plan, bud, ctx.get("symbol", "₹"))

            for warning in bud.warnings:
                st.warning(warning)

            render_budget_bar(bud, ctx.get("symbol", "₹"))
        else:
            st.markdown(
                """
                <div class="empty">
                    <div class="empty-icon">🎈</div>
                    <div class="empty-title">No plan yet</div>
                    <p class="empty-text">
                        Fill in the brief on the left and hit Generate. The defaults
                        already describe a realistic event, so you can just press the
                        button to see what it produces.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.plan:
        ctx = st.session_state.ctx
        bud = budget_mod.build_budget(
            st.session_state.plan.get("budget_items", []),
            target=ctx.get("budget", 0),
            attendees=ctx.get("attendees", 1),
            contingency_pct=st.session_state.contingency,
        )
        st.markdown("---")
        render_plan(
            st.session_state.plan,
            bud,
            ctx.get("symbol", "₹"),
            ctx.get("event_date", ""),
            ctx.get("attendees", 0),
        )
        render_toolbar(api_key, model, bud)


def render_toolbar(api_key: str, model: str, bud) -> None:
    plan = st.session_state.plan
    ctx = st.session_state.ctx

    st.markdown("---")
    st.markdown(
        '<div class="section-head"><h3 class="section-title">Refine</h3>'
        '<p class="section-hint">Adjust the plan without starting over</p></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(prompts.REFINEMENT_ACTIONS))
    for col, (key, action) in zip(cols, prompts.REFINEMENT_ACTIONS.items()):
        with col:
            if st.button(action["label"], width="stretch", key=f"refine_{key}"):
                with st.spinner(f"{action['label']}…"):
                    result = llm.refine_plan(plan, action["instruction"], api_key, model)
                if result.ok and result.mode == "live":
                    st.session_state.plan = result.data
                    st.session_state.meta = result
                    st.rerun()
                else:
                    st.error(result.error or "Refinement failed.")

    with st.expander("✎ Custom revision instruction"):
        custom = st.text_input(
            "Instruction",
            placeholder="e.g. Add a sponsorship workstream; move the venue booking two weeks earlier",
            label_visibility="collapsed",
        )
        if st.button("Apply revision") and custom.strip():
            with st.spinner("Revising…"):
                result = llm.refine_plan(plan, custom.strip(), api_key, model)
            if result.ok and result.mode == "live":
                st.session_state.plan = result.data
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

    symbol = ctx.get("symbol", "₹")
    event_date = ctx.get("event_date", "")
    attendees = ctx.get("attendees", 0)
    title = plan.get("event_title", "event_plan")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.download_button(
            "⬇ Word",
            data=export_utils.to_docx(plan, bud, symbol, event_date, attendees),
            file_name=export_utils.safe_filename(title, "docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
    with c2:
        st.download_button(
            "⬇ Markdown",
            data=export_utils.to_markdown(plan, bud, symbol, event_date, attendees),
            file_name=export_utils.safe_filename(title, "md"),
            mime="text/markdown",
            width="stretch",
        )
    with c3:
        st.download_button(
            "⬇ Checklist",
            data=export_utils.checklist_to_csv(plan, event_date),
            file_name=export_utils.safe_filename(title + "_checklist", "csv"),
            mime="text/csv",
            width="stretch",
            disabled=not plan.get("checklist"),
        )
    with c4:
        st.download_button(
            "⬇ Budget",
            data=export_utils.budget_to_csv(bud),
            file_name=export_utils.safe_filename(title + "_budget", "csv"),
            mime="text/csv",
            width="stretch",
            disabled=not bud.lines,
        )
    with c5:
        st.download_button(
            "⬇ JSON",
            data=export_utils.to_json(plan, bud),
            file_name=export_utils.safe_filename(title, "json"),
            mime="application/json",
            width="stretch",
        )

    with st.expander("📋 Copy as plain text"):
        st.code(export_utils.to_text(plan, bud, symbol, event_date, attendees), language=None)

    with st.expander("🔍 Structured data (what the agent produced)"):
        st.caption(
            "The model returns the plan as JSON with unit costs and quantities only. "
            "Every total below was computed in Python by budget.py — never by the model."
        )
        st.json(export_utils.to_json(plan, bud))


def page_checklist() -> None:
    if not st.session_state.plan:
        st.markdown(
            '<div class="empty"><div class="empty-icon">📋</div>'
            '<div class="empty-title">No plan yet</div>'
            '<p class="empty-text">Generate a plan first and your checklist will appear here, '
            "grouped by phase with tick-boxes.</p></div>",
            unsafe_allow_html=True,
        )
        return

    ctx = st.session_state.ctx
    render_checklist(st.session_state.plan, ctx.get("event_date", ""))

    st.markdown("---")
    st.download_button(
        "⬇ Download checklist as CSV",
        data=export_utils.checklist_to_csv(st.session_state.plan, ctx.get("event_date", "")),
        file_name=export_utils.safe_filename(
            st.session_state.plan.get("event_title", "event") + "_checklist", "csv"
        ),
        mime="text/csv",
    )


def page_budget() -> None:
    if not st.session_state.plan:
        st.markdown(
            '<div class="empty"><div class="empty-icon">💰</div>'
            '<div class="empty-title">No plan yet</div>'
            '<p class="empty-text">Generate a plan first and the costed budget will appear here.</p></div>',
            unsafe_allow_html=True,
        )
        return

    plan = st.session_state.plan
    ctx = st.session_state.ctx
    symbol = ctx.get("symbol", "₹")

    st.markdown(
        '<div class="section-head"><h3 class="section-title">Budget</h3>'
        '<p class="section-hint">Every figure computed in Python, not by the model</p></div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        contingency = st.slider(
            "Contingency %", min_value=0, max_value=25, value=st.session_state.contingency, step=1
        )
        st.session_state.contingency = contingency
    with c2:
        scale = st.slider(
            "Scale all unit costs", min_value=0.5, max_value=1.5,
            value=st.session_state.scale_factor, step=0.05,
            help="Model everything getting cheaper or more expensive, without another API call.",
        )
        st.session_state.scale_factor = scale

    bud = budget_mod.build_budget(
        plan.get("budget_items", []),
        target=ctx.get("budget", 0),
        attendees=ctx.get("attendees", 1),
        contingency_pct=contingency,
    )
    if scale != 1.0:
        bud.lines = budget_mod.rescale(bud.lines, scale)
        bud = budget_mod.build_budget(
            [
                {
                    "category": line.category,
                    "item": line.item,
                    "unit_cost": line.unit_cost,
                    "quantity": line.quantity,
                    "unit": line.unit,
                    "notes": line.notes,
                }
                for line in bud.lines
            ],
            target=ctx.get("budget", 0),
            attendees=ctx.get("attendees", 1),
            contingency_pct=contingency,
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Subtotal", f"{symbol}{bud.subtotal:,.0f}")
    m2.metric(f"Contingency ({contingency}%)", f"{symbol}{bud.contingency:,.0f}")
    m3.metric("Grand total", f"{symbol}{bud.grand_total:,.0f}")
    if bud.target > 0:
        m4.metric(
            "vs budget",
            f"{symbol}{abs(bud.variance):,.0f}",
            delta=f"{-bud.variance_pct:.1f}%" if bud.over_budget else f"{abs(bud.variance_pct):.1f}% spare",
            delta_color="inverse" if bud.over_budget else "normal",
        )
    else:
        m4.metric("Per head", f"{symbol}{bud.per_head:,.0f}")

    for warning in bud.warnings:
        st.warning(warning)

    render_budget_bar(bud, symbol)

    st.markdown("")
    rows = [
        {
            "Category": line.category,
            "Item": line.item,
            f"Unit ({symbol})": line.unit_cost,
            "Qty": line.quantity,
            "Unit": line.unit,
            f"Total ({symbol})": line.total,
            "Notes": line.notes,
        }
        for line in bud.lines
    ]
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Item": st.column_config.TextColumn(width="medium"),
            "Notes": st.column_config.TextColumn(width="medium"),
            f"Unit ({symbol})": st.column_config.NumberColumn(format="%.0f"),
            f"Total ({symbol})": st.column_config.NumberColumn(format="%.0f"),
        },
    )

    st.download_button(
        "⬇ Download budget as CSV",
        data=export_utils.budget_to_csv(bud),
        file_name=export_utils.safe_filename(plan.get("event_title", "event") + "_budget", "csv"),
        mime="text/csv",
    )

    if plan.get("equipment"):
        st.markdown("---")
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Equipment</h3>'
            f'<p class="section-hint">{len(plan["equipment"])} items</p></div>',
            unsafe_allow_html=True,
        )
        html = ""
        for eq in plan["equipment"]:
            badge = '<span class="eq-ess">ESSENTIAL</span>' if eq["essential"] else ""
            html += (
                f'<div class="eq-row"><span class="eq-name">{esc(eq["item"])}{badge}'
                + (f'<br><span style="font-size:.78rem;color:#8A7563">{esc(eq["notes"])}</span>' if eq.get("notes") else "")
                + f'</span><span class="eq-qty">{esc(eq["quantity"])}</span></div>'
            )
        st.markdown(html, unsafe_allow_html=True)

    if plan.get("day_schedule"):
        st.markdown("---")
        st.markdown(
            '<div class="section-head"><h3 class="section-title">Event Day Schedule</h3>'
            '<p class="section-hint">Run-of-show</p></div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            [
                {"Time": s.get("time", ""), "Activity": s["activity"], "Owner": s.get("owner", "")}
                for s in plan["day_schedule"]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Time": st.column_config.TextColumn(width="small"),
                "Activity": st.column_config.TextColumn(width="large"),
            },
        )


def page_history() -> None:
    st.markdown(
        '<div class="section-head"><h3 class="section-title">Session History</h3>'
        '<p class="section-hint">The last 20 plans from this session</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.history:
        st.markdown(
            '<div class="empty"><div class="empty-icon">🕐</div>'
            '<div class="empty-title">Nothing here yet</div>'
            '<p class="empty-text">Plans you generate will be listed here so you can reload them. '
            "History lives in the browser session only.</p></div>",
            unsafe_allow_html=True,
        )
        return

    for i, entry in enumerate(st.session_state.history):
        plan = entry["data"]
        ctx = entry.get("ctx", {})
        col_main, col_btn = st.columns([5, 1])
        with col_main:
            mode_icon = "●" if entry["mode"] == "live" else "◆"
            st.markdown(
                f"""
                <div class="hist-item">
                    <div class="hist-title">{esc(plan.get('event_title', 'Untitled'))}</div>
                    <div class="hist-meta">
                        {mode_icon} {entry['timestamp']} · {esc(entry['type'])} ·
                        {ctx.get('attendees', '?')} guests ·
                        {len(plan.get('checklist', []))} tasks
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Reload", key=f"reload_{i}", width="stretch"):
                st.session_state.plan = plan
                st.session_state.ctx = ctx
                st.session_state.meta = None
                st.session_state.done_tasks = set()
                st.session_state.page = "Plan"
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
            The agent turns a short event brief — type, size, budget, date, location —
            into a complete plan: venue options, a costed budget, a phased checklist
            with owners and relative deadlines, equipment lists, an invitation
            strategy, a run-of-show, and a risk register. Recommendations are
            customised by both <strong>event type</strong> and <strong>scale band</strong>,
            so a 20-person birthday and a 2000-person fest receive genuinely
            different plans rather than the same template with numbers swapped.
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
                <strong>app.py</strong> — UI, routing, state<br>
                <strong>prompts.py</strong> — prompt engineering, schema, scale bands<br>
                <strong>llm.py</strong> — Groq client, JSON recovery, fallback<br>
                <strong>budget.py</strong> — deterministic budget arithmetic<br>
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
                Role prompting with domain-specific modifiers<br>
                Scale-aware planning via banded guidance<br>
                Relative-date encoding, resolved in code<br>
                Multi-strategy JSON recovery parsing<br>
                Graceful degradation to a template planner
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="card">
            <div class="card-label">◈ Why the model never does arithmetic</div>
            The most important design decision in this project. Language models are
            unreliable at multi-step arithmetic — ask one for a budget and it will
            confidently return line items whose stated total is wrong. So the model
            is only ever asked for <em>unit_cost</em> and <em>quantity</em>. Every
            multiplication, subtotal, contingency, per-head figure and variance
            against the target budget is computed in <code>budget.py</code> with
            Python. The budget is therefore guaranteed internally consistent no
            matter what the model returns, and the contingency and scaling sliders
            recompute instantly with no further API calls.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card">
            <div class="card-label">◈ Why deadlines are relative</div>
            The model emits <code>days_before_event</code> as an integer, never a
            calendar date. Models routinely invent dates that fall after the event or
            land on impossible days. Resolving offsets against the real event date in
            Python guarantees a coherent timeline, and it means changing the event
            date reflows the entire plan without regenerating it.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card">
            <div class="card-label">◈ Honest limitations</div>
            Cost estimates are the model's best guess for the region given and should
            be validated against real quotes before committing money. Offline mode is
            a fixed template — it demonstrates the interface without an API key but
            does not adapt to your brief. Checklist completion state and history live
            in the browser session and are lost on refresh; SQLite persistence is the
            obvious next extension.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="footer-note">AI Event Planning Agent<br>'
        "Built with Streamlit · Powered by Groq</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    page, api_key, model = render_sidebar()

    if page == "Plan":
        page_plan(api_key, model)
    elif page == "Checklist":
        page_checklist()
    elif page == "Budget":
        page_budget()
    elif page == "History":
        page_history()
    else:
        page_about()


if __name__ == "__main__":
    main()
