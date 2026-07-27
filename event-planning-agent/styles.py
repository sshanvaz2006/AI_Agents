"""
styles.py
=========
Design system for the Event Planning Agent.

Deliberately distinct from the sibling projects in this repo: where the minutes
generator uses a cool violet/cyan scheme, this app uses a warm coral-to-amber
palette on a cream canvas — appropriate for celebrations and events, and it
makes the three projects immediately distinguishable in a portfolio.

* Type: "Outfit" for UI, "Fraunces" (a soft display serif) for headings,
  "JetBrains Mono" for figures and metadata.
* Depth: soft shadows, generous radii, hairline borders.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --ink-900: #1A1410;
    --ink-800: #2E2419;
    --ink-700: #4A3B2A;
    --ink-600: #6B5744;
    --stone-500: #8A7563;
    --stone-400: #A89684;
    --stone-300: #D6C9BC;
    --stone-200: #E9E0D6;
    --stone-100: #F5EFE8;
    --paper: #FFFFFF;
    --canvas: #FDFAF6;

    --coral: #F2542D;
    --coral-dark: #D63F1B;
    --coral-soft: #FFF0EB;
    --amber: #F2A104;
    --amber-soft: #FFF8E7;
    --teal: #0E9594;
    --teal-soft: #E6F5F5;
    --plum: #7B2D5E;
    --emerald: #1B998B;
    --emerald-soft: #E8F7F5;
    --rose: #D62246;
    --rose-soft: #FDECEF;

    --warm-gradient: linear-gradient(118deg, #F2542D 0%, #F2764B 42%, #F2A104 100%);
    --deep-gradient: linear-gradient(135deg, #2E2419 0%, #4A2C1A 55%, #7B2D5E 100%);

    --shadow-sm: 0 1px 2px rgba(46,36,25,.07), 0 1px 3px rgba(46,36,25,.05);
    --shadow-md: 0 4px 14px rgba(46,36,25,.08), 0 2px 5px rgba(46,36,25,.04);
    --shadow-lg: 0 14px 36px rgba(46,36,25,.12), 0 4px 10px rgba(46,36,25,.05);
    --shadow-xl: 0 26px 60px rgba(46,36,25,.16);

    --radius-sm: 11px;
    --radius-md: 16px;
    --radius-lg: 22px;
}

html, body, [class*="css"], .stApp { font-family:'Outfit', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: var(--canvas); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.6rem 2.4rem 4rem; max-width: 1340px; }

::-webkit-scrollbar { width:9px; height:9px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--stone-300); border-radius:6px; }
::-webkit-scrollbar-thumb:hover { background: var(--stone-400); }

@keyframes fadeUp { from{opacity:0; transform:translateY(11px);} to{opacity:1; transform:none;} }
.fade-in { animation: fadeUp .45s cubic-bezier(.22,1,.36,1) both; }

/* ---------- hero ---------- */
.hero {
    position:relative;
    background: var(--deep-gradient);
    background-image:
        radial-gradient(900px 420px at 8% -20%, rgba(242,84,45,.55), transparent 62%),
        radial-gradient(700px 340px at 92% 0%, rgba(242,161,4,.38), transparent 64%),
        radial-gradient(600px 320px at 55% 130%, rgba(123,45,94,.45), transparent 60%),
        linear-gradient(135deg,#2E2419,#4A2C1A);
    border-radius: var(--radius-lg);
    padding: 2.8rem 3rem 3rem;
    margin-bottom:1.7rem; overflow:hidden;
    box-shadow: var(--shadow-xl);
}
.hero::after {
    content:''; position:absolute; inset:0;
    background-image:
        linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
    background-size:44px 44px;
    mask-image: radial-gradient(circle at 25% 15%, black, transparent 80%);
    pointer-events:none;
}
.hero-eyebrow {
    display:inline-flex; align-items:center; gap:.5rem;
    font-size:.7rem; font-weight:700; letter-spacing:.17em; text-transform:uppercase;
    color:#FFD9A0; background:rgba(255,255,255,.1);
    border:1px solid rgba(255,255,255,.18);
    padding:.42rem .9rem; border-radius:100px;
    backdrop-filter: blur(8px); margin-bottom:1.15rem;
}
.hero-title, .hero h1 {
    font-family:'Fraunces', Georgia, serif !important;
    font-size: clamp(2.3rem, 4.7vw, 3.6rem) !important;
    line-height:1.05 !important; font-weight:400 !important;
    color:#FFFFFF !important; margin:0 0 .9rem !important;
    letter-spacing:-.018em !important; padding:0 !important;
}
.hero-title em {
    font-style:italic;
    background: linear-gradient(100deg,#FFB77A,#FFD9A0);
    -webkit-background-clip:text; background-clip:text; color:transparent;
}
.hero-sub { color:#D8C9BA; font-size:1.02rem; line-height:1.68; max-width:660px; margin:0; }
.hero-chips { display:flex; gap:.5rem; flex-wrap:wrap; margin-top:1.55rem; }
.hero-chip {
    font-size:.76rem; font-weight:600; color:#F0E4D8;
    background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15);
    padding:.4rem .82rem; border-radius:9px; backdrop-filter: blur(6px);
}

/* ---------- sections ---------- */
.section-head { display:flex; align-items:baseline; gap:.8rem; margin:.4rem 0 1.1rem; }
.section-title {
    font-family:'Fraunces', Georgia, serif;
    font-size:1.75rem; font-weight:400; color:var(--ink-900);
    letter-spacing:-.012em; margin:0;
}
.section-hint { font-size:.86rem; color:var(--stone-500); margin:0; }

/* ---------- cards ---------- */
.card {
    background:var(--paper); border:1px solid var(--stone-200);
    border-radius:var(--radius-md); padding:1.5rem 1.6rem;
    box-shadow:var(--shadow-sm); margin-bottom:1.1rem;
    transition: box-shadow .25s ease;
}
.card:hover { box-shadow:var(--shadow-md); }
.card-label {
    font-size:.68rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase;
    color:var(--coral); margin-bottom:.8rem;
}

.empty {
    background:var(--paper); border:1.5px dashed var(--stone-300);
    border-radius:var(--radius-md); padding:3.4rem 2rem; text-align:center;
}
.empty-icon { font-size:2.7rem; margin-bottom:.9rem; opacity:.8; }
.empty-title { font-size:1.03rem; font-weight:700; color:var(--ink-700); margin-bottom:.4rem; }
.empty-text { font-size:.88rem; color:var(--stone-500); max-width:350px; margin:0 auto; line-height:1.62; }

/* ---------- badges ---------- */
.badge {
    display:inline-flex; align-items:center; gap:.45rem;
    font-size:.76rem; font-weight:700; padding:.42rem .85rem;
    border-radius:9px; border:1px solid transparent;
}
.badge-live { background:var(--emerald-soft); color:#0F6B60; border-color:#A8DED6; }
.badge-off  { background:var(--amber-soft);   color:#96650A; border-color:#F5D98B; }
.badge-err  { background:var(--rose-soft);    color:#A81733; border-color:#F5BFC9; }
.pulse { width:7px; height:7px; border-radius:50%; background:currentColor; animation:pulseDot 2s infinite; }
@keyframes pulseDot { 0%,100%{opacity:1;} 50%{opacity:.35;} }

/* ---------- metrics ---------- */
.metric-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(112px,1fr)); gap:.75rem; margin-bottom:1.3rem; }
.metric {
    background:var(--paper); border:1px solid var(--stone-200);
    border-radius:var(--radius-sm); padding:.9rem 1rem;
    box-shadow:var(--shadow-sm); position:relative; overflow:hidden;
    transition: transform .2s ease, box-shadow .2s ease;
}
.metric:hover { transform:translateY(-2px); box-shadow:var(--shadow-md); }
.metric::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--warm-gradient); }
.metric-value {
    font-size:1.6rem; font-weight:800; color:var(--ink-900);
    line-height:1; letter-spacing:-.02em; margin-bottom:.3rem;
    font-family:'JetBrains Mono', monospace;
}
.metric-label { font-size:.63rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--stone-500); }

/* ---------- plan document ---------- */
.doc { background:var(--paper); border:1px solid var(--stone-200); border-radius:var(--radius-lg); box-shadow:var(--shadow-lg); overflow:hidden; }
.doc-header {
    background: var(--deep-gradient);
    background-image: radial-gradient(620px 220px at 15% 0%, rgba(242,84,45,.5), transparent 66%), linear-gradient(135deg,#2E2419,#4A2C1A);
    padding:1.95rem 2.1rem 1.75rem; color:#fff;
}
.doc-title { font-family:'Fraunces', Georgia, serif; font-size:1.9rem; font-weight:400; margin:0 0 .9rem; line-height:1.2; }
.doc-meta { display:flex; flex-wrap:wrap; gap:1.5rem; }
.doc-meta-item { display:flex; flex-direction:column; gap:.18rem; }
.doc-meta-key { font-size:.62rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; color:#C4A88C; }
.doc-meta-val { font-size:.87rem; font-weight:600; color:#F5EDE4; font-family:'JetBrains Mono', monospace; }
.doc-body { padding:1.9rem 2.1rem 2.1rem; }

.mblock { margin-bottom:2rem; }
.mblock:last-child { margin-bottom:0; }
.mblock-head { display:flex; align-items:center; gap:.6rem; padding-bottom:.6rem; margin-bottom:1rem; border-bottom:1px solid var(--stone-200); }
.mblock-title { font-size:.76rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:var(--ink-800); margin:0; }
.mblock-count { font-size:.68rem; font-weight:700; color:var(--coral); background:var(--coral-soft); padding:.15rem .52rem; border-radius:20px; }

.summary-text {
    font-size:1rem; line-height:1.78; color:var(--ink-700);
    background:linear-gradient(180deg,#FFFBF8,#FFF6F0);
    border-left:3px solid var(--coral); border-radius:0 var(--radius-sm) var(--radius-sm) 0;
    padding:1.15rem 1.35rem;
}

/* venue cards */
.venue {
    background:var(--stone-100); border:1px solid var(--stone-200);
    border-radius:var(--radius-sm); padding:1.05rem 1.2rem; margin-bottom:.7rem;
    border-left:3px solid var(--teal);
}
.venue-name { font-size:.98rem; font-weight:700; color:var(--ink-800); margin-bottom:.3rem; display:flex; justify-content:space-between; gap:1rem; align-items:baseline; }
.venue-cost { font-size:.85rem; font-weight:700; color:var(--teal); font-family:'JetBrains Mono', monospace; white-space:nowrap; }
.venue-why { font-size:.89rem; color:var(--ink-600); line-height:1.6; }
.venue-fit { font-size:.76rem; color:var(--stone-500); margin-top:.28rem; font-family:'JetBrains Mono', monospace; }

/* phase blocks */
.phase-head {
    display:flex; align-items:center; gap:.6rem; margin:1.4rem 0 .7rem;
    font-size:.8rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--plum);
}
.phase-line { flex:1; height:1px; background:var(--stone-200); }

.task {
    display:flex; gap:.75rem; align-items:flex-start;
    background:var(--paper); border:1px solid var(--stone-200);
    border-radius:var(--radius-sm); padding:.75rem .95rem; margin-bottom:.45rem;
    transition: border-color .18s ease;
}
.task:hover { border-color:var(--coral); }
.task-when {
    flex-shrink:0; font-size:.68rem; font-weight:700; font-family:'JetBrains Mono', monospace;
    background:var(--stone-100); color:var(--ink-600);
    padding:.22rem .48rem; border-radius:6px; min-width:62px; text-align:center; margin-top:.1rem;
}
.task-body { flex:1; }
.task-text { font-size:.92rem; color:var(--ink-800); line-height:1.5; }
.task-owner { font-size:.73rem; color:var(--stone-500); margin-top:.22rem; font-family:'JetBrains Mono', monospace; }

.prio { font-size:.63rem; font-weight:800; padding:.16rem .42rem; border-radius:5px; letter-spacing:.04em; flex-shrink:0; margin-top:.15rem; }
.prio-High   { background:#FDE2E7; color:#A81733; }
.prio-Medium { background:#FFF0D6; color:#96650A; }
.prio-Low    { background:#E1F0EF; color:#0F6B60; }

/* timeline */
.tl { position:relative; padding-left:1.5rem; }
.tl::before { content:''; position:absolute; left:5px; top:6px; bottom:6px; width:2px; background:linear-gradient(180deg,var(--coral),var(--amber)); }
.tl-item { position:relative; margin-bottom:1rem; }
.tl-item::before {
    content:''; position:absolute; left:-1.5rem; top:5px;
    width:12px; height:12px; border-radius:50%;
    background:var(--paper); border:2.5px solid var(--coral);
}
.tl-when { font-size:.7rem; font-weight:700; color:var(--coral); font-family:'JetBrains Mono', monospace; letter-spacing:.03em; }
.tl-name { font-size:.95rem; font-weight:700; color:var(--ink-800); margin:.1rem 0 .15rem; }
.tl-detail { font-size:.85rem; color:var(--ink-600); line-height:1.55; }

/* risks */
.risk { background:var(--rose-soft); border:1px solid #F5BFC9; border-left:3px solid var(--rose); border-radius:var(--radius-sm); padding:.9rem 1.1rem; margin-bottom:.6rem; }
.risk-top { display:flex; justify-content:space-between; gap:1rem; align-items:baseline; }
.risk-text { font-size:.92rem; font-weight:600; color:#7A0F26; line-height:1.5; }
.risk-lik { font-size:.63rem; font-weight:800; padding:.16rem .45rem; border-radius:5px; background:#fff; color:#A81733; flex-shrink:0; }
.risk-fix { font-size:.85rem; color:#93203A; margin-top:.35rem; line-height:1.55; }

/* pills, tips, invite */
.pill { display:inline-block; font-size:.78rem; font-weight:600; background:var(--stone-100); color:var(--ink-700); border:1px solid var(--stone-200); border-radius:100px; padding:.34rem .85rem; margin:0 .38rem .42rem 0; }
.tip { display:flex; gap:.6rem; font-size:.9rem; color:var(--ink-700); line-height:1.6; margin-bottom:.5rem; }
.tip-mark { color:var(--amber); font-weight:800; flex-shrink:0; }
.invite-box {
    background:var(--amber-soft); border:1px solid #F5D98B; border-radius:var(--radius-sm);
    padding:1.15rem 1.3rem; font-size:.93rem; line-height:1.72; color:var(--ink-700);
    font-style:italic; position:relative;
}
.eq-row { display:flex; justify-content:space-between; gap:1rem; align-items:baseline; padding:.55rem 0; border-bottom:1px dashed var(--stone-200); }
.eq-name { font-size:.91rem; color:var(--ink-800); }
.eq-qty { font-size:.8rem; color:var(--stone-500); font-family:'JetBrains Mono', monospace; white-space:nowrap; }
.eq-ess { font-size:.62rem; font-weight:800; padding:.13rem .4rem; border-radius:4px; background:var(--coral-soft); color:var(--coral-dark); margin-left:.4rem; }

/* budget bar */
.bud-bar { display:flex; height:26px; border-radius:7px; overflow:hidden; margin:.6rem 0 1rem; box-shadow:var(--shadow-sm); }
.bud-seg { display:flex; align-items:center; justify-content:center; font-size:.64rem; font-weight:800; color:#fff; overflow:hidden; white-space:nowrap; }

/* ---------- widget overrides ---------- */
.stButton > button {
    border-radius:var(--radius-sm); font-weight:600; font-size:.89rem;
    border:1px solid var(--stone-200); background:var(--paper); color:var(--ink-700);
    padding:.6rem 1.05rem; transition:all .18s ease; box-shadow:var(--shadow-sm);
}
.stButton > button:hover { border-color:var(--coral); color:var(--coral); transform:translateY(-1px); box-shadow:var(--shadow-md); }
.stButton > button[kind="primary"] {
    background:var(--warm-gradient); color:#fff; border:none;
    box-shadow:0 4px 16px rgba(242,84,45,.36); font-weight:700;
}
.stButton > button[kind="primary"]:hover { color:#fff; transform:translateY(-2px); box-shadow:0 9px 24px rgba(242,84,45,.46); }
.stDownloadButton > button {
    border-radius:var(--radius-sm); font-weight:600; font-size:.86rem;
    border:1px solid var(--stone-200); background:var(--paper); color:var(--ink-700); width:100%;
}
.stDownloadButton > button:hover { border-color:var(--coral); color:var(--coral); }

.stTextArea textarea, .stTextInput input, .stNumberInput input {
    border-radius:var(--radius-sm) !important; border:1px solid var(--stone-200) !important;
    font-size:.92rem !important; background:var(--paper) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
    border-color:var(--coral) !important; box-shadow:0 0 0 3px rgba(242,84,45,.11) !important;
}
.stSelectbox > div > div { border-radius:var(--radius-sm) !important; border-color:var(--stone-200) !important; }

section[data-testid="stSidebar"] { background:var(--paper); border-right:1px solid var(--stone-200); }
section[data-testid="stSidebar"] .block-container { padding-top:1.4rem; }

.stTabs [data-baseweb="tab-list"] { gap:.3rem; border-bottom:1px solid var(--stone-200); }
.stTabs [data-baseweb="tab"] { font-size:.88rem; font-weight:600; color:var(--stone-500); border-radius:var(--radius-sm) var(--radius-sm) 0 0; padding:.55rem 1rem; }
.stTabs [aria-selected="true"] { color:var(--coral) !important; background:var(--coral-soft) !important; }

div[data-testid="stExpander"] { border:1px solid var(--stone-200) !important; border-radius:var(--radius-sm) !important; background:var(--paper) !important; box-shadow:var(--shadow-sm); }
.stProgress > div > div > div { background:var(--warm-gradient) !important; }
.stDataFrame { border-radius:var(--radius-sm); overflow:hidden; border:1px solid var(--stone-200); }
hr { border:none; border-top:1px solid var(--stone-200); margin:1.5rem 0; }

.sidebar-brand { display:flex; align-items:center; gap:.65rem; padding-bottom:1rem; margin-bottom:.5rem; border-bottom:1px solid var(--stone-200); }
.sidebar-mark {
    width:34px; height:34px; border-radius:10px; background:var(--warm-gradient);
    display:flex; align-items:center; justify-content:center; font-size:1.05rem;
    box-shadow:0 3px 10px rgba(242,84,45,.32);
}
.sidebar-name { font-size:.97rem; font-weight:800; color:var(--ink-900); line-height:1.15; }
.sidebar-tag { font-size:.68rem; color:var(--stone-500); font-weight:500; }

.hist-item { background:var(--paper); border:1px solid var(--stone-200); border-radius:var(--radius-sm); padding:1rem 1.15rem; margin-bottom:.7rem; transition:all .18s ease; }
.hist-item:hover { border-color:var(--coral); box-shadow:var(--shadow-md); }
.hist-title { font-size:.95rem; font-weight:700; color:var(--ink-800); margin-bottom:.3rem; }
.hist-meta { font-size:.75rem; color:var(--stone-500); font-family:'JetBrains Mono', monospace; }

.footer-note { text-align:center; font-size:.78rem; color:var(--stone-400); padding:2.5rem 0 1rem; line-height:1.7; }
</style>
"""
