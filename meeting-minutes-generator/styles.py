"""
styles.py
=========
All custom CSS for the app, injected once from app.py.

Design language
---------------
* Palette: deep slate/indigo base with a violet-to-cyan accent gradient.
* Type: "Plus Jakarta Sans" for UI, "Instrument Serif" for display headings,
  "JetBrains Mono" for metadata — a serif display face is unusual in Streamlit
  apps and instantly signals a designed product rather than a default theme.
* Depth: layered shadows and 1px hairline borders instead of heavy boxes.
* Motion: restrained. Entrance fades and hover lifts only.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --ink-900: #0B1020;
    --ink-800: #121834;
    --ink-700: #1B2347;
    --ink-600: #2A3563;
    --slate-500: #64748B;
    --slate-400: #94A3B8;
    --slate-300: #CBD5E1;
    --slate-200: #E2E8F0;
    --slate-100: #F1F5F9;
    --paper: #FFFFFF;
    --canvas: #F7F8FC;

    --violet: #6D5EF8;
    --violet-dark: #5646E8;
    --violet-soft: #EEEBFF;
    --cyan: #22D3EE;
    --emerald: #10B981;
    --emerald-soft: #ECFDF5;
    --amber: #F59E0B;
    --amber-soft: #FFFBEB;
    --rose: #F43F5E;
    --rose-soft: #FFF1F3;

    --accent-gradient: linear-gradient(115deg, #6D5EF8 0%, #8B5CF6 45%, #22D3EE 100%);

    --shadow-sm: 0 1px 2px rgba(11,16,32,.06), 0 1px 3px rgba(11,16,32,.04);
    --shadow-md: 0 4px 12px rgba(11,16,32,.06), 0 2px 4px rgba(11,16,32,.04);
    --shadow-lg: 0 12px 32px rgba(11,16,32,.10), 0 4px 8px rgba(11,16,32,.04);
    --shadow-xl: 0 24px 56px rgba(11,16,32,.14);

    --radius-sm: 10px;
    --radius-md: 14px;
    --radius-lg: 20px;
}

/* ---------- base ---------- */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}
.stApp { background: var(--canvas); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.6rem 2.4rem 4rem; max-width: 1320px; }

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--slate-300); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--slate-400); }

@keyframes fadeUp { from { opacity:0; transform: translateY(10px);} to {opacity:1; transform:none;} }
@keyframes shimmer { 0%{background-position:-1000px 0;} 100%{background-position:1000px 0;} }
.fade-in { animation: fadeUp .45s cubic-bezier(.22,1,.36,1) both; }

/* ---------- hero ---------- */
.hero {
    position: relative;
    background: var(--ink-900);
    background-image:
        radial-gradient(900px 400px at 12% -10%, rgba(109,94,248,.55), transparent 60%),
        radial-gradient(700px 350px at 88% 0%, rgba(34,211,238,.32), transparent 62%),
        radial-gradient(500px 300px at 50% 120%, rgba(139,92,246,.28), transparent 60%);
    border-radius: var(--radius-lg);
    padding: 2.7rem 3rem 2.9rem;
    margin-bottom: 1.7rem;
    overflow: hidden;
    box-shadow: var(--shadow-xl);
}
.hero::after {
    content:'';
    position:absolute; inset:0;
    background-image:
        linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 46px 46px;
    mask-image: radial-gradient(circle at 30% 20%, black, transparent 78%);
    pointer-events:none;
}
.hero-eyebrow {
    display:inline-flex; align-items:center; gap:.5rem;
    font-size:.7rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;
    color:#C7D2FE;
    background: rgba(255,255,255,.09);
    border:1px solid rgba(255,255,255,.16);
    padding:.4rem .85rem; border-radius:100px;
    backdrop-filter: blur(8px);
    margin-bottom:1.1rem;
}
.hero-title, .hero .hero-title, .hero h1 {
    font-family:'Instrument Serif', Georgia, serif !important;
    font-size: clamp(2.3rem, 4.6vw, 3.5rem) !important;
    line-height:1.04 !important; font-weight:400 !important;
    color:#FFFFFF !important;
    margin:0 0 .85rem !important; letter-spacing:-.015em !important;
    padding:0 !important;
}
.hero-title em {
    font-style: italic;
    background: linear-gradient(100deg, #A5B4FC, #67E8F9);
    -webkit-background-clip:text; background-clip:text; color:transparent;
}
.hero-sub {
    color:#AEB9D6; font-size:1.02rem; line-height:1.65;
    max-width: 640px; margin:0; font-weight:400;
}
.hero-chips { display:flex; gap:.5rem; flex-wrap:wrap; margin-top:1.5rem; }
.hero-chip {
    font-size:.76rem; font-weight:600; color:#DDE3F5;
    background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.13);
    padding:.4rem .8rem; border-radius:8px; backdrop-filter: blur(6px);
}

/* ---------- section headings ---------- */
.section-head { display:flex; align-items:baseline; gap:.75rem; margin:.4rem 0 1.1rem; }
.section-title {
    font-family:'Instrument Serif', Georgia, serif;
    font-size:1.72rem; font-weight:400; color:var(--ink-900);
    letter-spacing:-.01em; margin:0;
}
.section-hint { font-size:.86rem; color:var(--slate-500); margin:0; }

/* ---------- cards ---------- */
.card {
    background:var(--paper);
    border:1px solid var(--slate-200);
    border-radius:var(--radius-md);
    padding:1.5rem 1.6rem;
    box-shadow:var(--shadow-sm);
    margin-bottom:1.1rem;
    transition: box-shadow .25s ease, transform .25s ease;
}
.card:hover { box-shadow:var(--shadow-md); }
.card-label {
    font-size:.68rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase;
    color:var(--violet); margin-bottom:.8rem; display:flex; align-items:center; gap:.45rem;
}

/* ---------- empty state ---------- */
.empty {
    background:var(--paper);
    border:1.5px dashed var(--slate-300);
    border-radius:var(--radius-md);
    padding:3.4rem 2rem; text-align:center;
}
.empty-icon { font-size:2.6rem; margin-bottom:.9rem; opacity:.75; }
.empty-title { font-size:1.02rem; font-weight:700; color:var(--ink-700); margin-bottom:.4rem; }
.empty-text { font-size:.88rem; color:var(--slate-500); max-width:340px; margin:0 auto; line-height:1.6; }

/* ---------- status badges ---------- */
.badge {
    display:inline-flex; align-items:center; gap:.45rem;
    font-size:.76rem; font-weight:700; padding:.42rem .85rem; border-radius:8px;
    border:1px solid transparent;
}
.badge-live   { background:var(--emerald-soft); color:#047857; border-color:#A7F3D0; }
.badge-off    { background:var(--amber-soft);   color:#B45309; border-color:#FDE68A; }
.badge-err    { background:var(--rose-soft);    color:#BE123C; border-color:#FECDD3; }
.pulse { width:7px; height:7px; border-radius:50%; background:currentColor; animation:pulseDot 2s infinite; }
@keyframes pulseDot { 0%,100%{opacity:1;} 50%{opacity:.35;} }

/* ---------- metrics ---------- */
.metric-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(96px,1fr)); gap:.7rem; margin-bottom:1.3rem; }
.metric {
    background:var(--paper); border:1px solid var(--slate-200);
    border-radius:var(--radius-sm); padding:.85rem .9rem;
    box-shadow:var(--shadow-sm); position:relative; overflow:hidden;
    transition: transform .2s ease, box-shadow .2s ease;
}
.metric:hover { transform:translateY(-2px); box-shadow:var(--shadow-md); }
.metric::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--accent-gradient); }
.metric-value {
    font-size:1.6rem; font-weight:800; color:var(--ink-900);
    line-height:1; letter-spacing:-.02em; margin-bottom:.3rem;
}
.metric-label {
    font-size:.62rem; font-weight:700; letter-spacing:.1em;
    text-transform:uppercase; color:var(--slate-500);
}

/* ---------- minutes document ---------- */
.doc {
    background:var(--paper); border:1px solid var(--slate-200);
    border-radius:var(--radius-lg); box-shadow:var(--shadow-lg); overflow:hidden;
}
.doc-header {
    background: var(--ink-900);
    background-image: radial-gradient(600px 200px at 20% 0%, rgba(109,94,248,.45), transparent 65%);
    padding:1.9rem 2.1rem 1.7rem; color:#fff;
}
.doc-title {
    font-family:'Instrument Serif', Georgia, serif;
    font-size:1.85rem; font-weight:400; margin:0 0 .9rem; line-height:1.2;
}
.doc-meta { display:flex; flex-wrap:wrap; gap:1.4rem; }
.doc-meta-item { display:flex; flex-direction:column; gap:.18rem; }
.doc-meta-key {
    font-size:.62rem; font-weight:700; letter-spacing:.13em;
    text-transform:uppercase; color:#8FA0C4;
}
.doc-meta-val { font-size:.86rem; font-weight:600; color:#E8EDF9; font-family:'JetBrains Mono', monospace; }
.doc-body { padding:1.9rem 2.1rem 2.1rem; }

.mblock { margin-bottom:2rem; }
.mblock:last-child { margin-bottom:0; }
.mblock-head {
    display:flex; align-items:center; gap:.6rem;
    padding-bottom:.6rem; margin-bottom:1rem;
    border-bottom:1px solid var(--slate-200);
}
.mblock-title {
    font-size:.76rem; font-weight:800; letter-spacing:.14em;
    text-transform:uppercase; color:var(--ink-800); margin:0;
}
.mblock-count {
    font-size:.68rem; font-weight:700; color:var(--violet);
    background:var(--violet-soft); padding:.15rem .5rem; border-radius:20px;
}

.summary-text {
    font-size:1rem; line-height:1.78; color:var(--ink-700);
    background:linear-gradient(180deg, #FBFAFF, #F6F5FF);
    border-left:3px solid var(--violet); border-radius:0 var(--radius-sm) var(--radius-sm) 0;
    padding:1.15rem 1.35rem;
}

.topic { margin-bottom:1.15rem; }
.topic-name { font-size:.97rem; font-weight:700; color:var(--ink-800); margin-bottom:.45rem; }
.topic ul { margin:0; padding-left:1.15rem; }
.topic li { font-size:.92rem; line-height:1.68; color:var(--ink-700); margin-bottom:.32rem; }

.dec {
    background:var(--emerald-soft); border:1px solid #A7F3D0;
    border-radius:var(--radius-sm); padding:.95rem 1.15rem; margin-bottom:.7rem;
    display:flex; gap:.8rem; align-items:flex-start;
}
.dec-num {
    flex-shrink:0; width:22px; height:22px; border-radius:6px;
    background:var(--emerald); color:#fff; font-size:.72rem; font-weight:800;
    display:flex; align-items:center; justify-content:center; margin-top:.1rem;
}
.dec-text { font-size:.94rem; font-weight:600; color:#064E3B; line-height:1.55; }
.dec-why { font-size:.83rem; color:#047857; margin-top:.3rem; line-height:1.5; }
.dec-owner {
    font-size:.72rem; font-weight:700; color:#065F46;
    font-family:'JetBrains Mono', monospace; margin-top:.35rem;
}

.risk {
    background:var(--rose-soft); border:1px solid #FECDD3;
    border-radius:var(--radius-sm); padding:.95rem 1.15rem; margin-bottom:.7rem;
    border-left:3px solid var(--rose);
}
.risk-text { font-size:.93rem; font-weight:600; color:#881337; line-height:1.55; }
.risk-impact { font-size:.83rem; color:#9F1239; margin-top:.3rem; }

.q {
    background:var(--slate-100); border:1px solid var(--slate-200);
    border-radius:var(--radius-sm); padding:.8rem 1.05rem; margin-bottom:.55rem;
    font-size:.92rem; color:var(--ink-700); line-height:1.55;
    display:flex; gap:.6rem;
}
.q-mark { color:var(--violet); font-weight:800; flex-shrink:0; }

.pill {
    display:inline-block; font-size:.78rem; font-weight:600;
    background:var(--slate-100); color:var(--ink-700);
    border:1px solid var(--slate-200); border-radius:100px;
    padding:.35rem .85rem; margin:0 .38rem .42rem 0;
}
.pill-out { background:var(--paper); color:var(--slate-500); }

.prio { font-size:.68rem; font-weight:800; padding:.2rem .5rem; border-radius:5px; letter-spacing:.04em; }
.prio-High   { background:#FEE2E2; color:#B91C1C; }
.prio-Medium { background:#FEF3C7; color:#B45309; }
.prio-Low    { background:#DBEAFE; color:#1D4ED8; }

/* ---------- streamlit widget overrides ---------- */
.stButton > button {
    border-radius:var(--radius-sm); font-weight:600; font-size:.89rem;
    border:1px solid var(--slate-200); background:var(--paper); color:var(--ink-700);
    padding:.6rem 1.05rem; transition:all .18s ease; box-shadow:var(--shadow-sm);
}
.stButton > button:hover {
    border-color:var(--violet); color:var(--violet);
    transform:translateY(-1px); box-shadow:var(--shadow-md);
}
.stButton > button[kind="primary"] {
    background:var(--accent-gradient); color:#fff; border:none;
    box-shadow:0 4px 14px rgba(109,94,248,.35); font-weight:700;
}
.stButton > button[kind="primary"]:hover {
    color:#fff; transform:translateY(-2px); box-shadow:0 8px 22px rgba(109,94,248,.45);
}
.stDownloadButton > button {
    border-radius:var(--radius-sm); font-weight:600; font-size:.86rem;
    border:1px solid var(--slate-200); background:var(--paper); color:var(--ink-700);
    width:100%; transition:all .18s ease;
}
.stDownloadButton > button:hover { border-color:var(--violet); color:var(--violet); }

.stTextArea textarea, .stTextInput input {
    border-radius:var(--radius-sm) !important; border:1px solid var(--slate-200) !important;
    font-size:.92rem !important; background:var(--paper) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color:var(--violet) !important; box-shadow:0 0 0 3px rgba(109,94,248,.11) !important;
}
.stTextArea textarea { font-family:'JetBrains Mono', monospace !important; font-size:.84rem !important; line-height:1.65 !important; }
.stSelectbox > div > div { border-radius:var(--radius-sm) !important; border-color:var(--slate-200) !important; }

div[data-testid="stFileUploader"] {
    background:var(--paper); border:1.5px dashed var(--slate-300);
    border-radius:var(--radius-md); padding:1rem;
}
div[data-testid="stFileUploader"]:hover { border-color:var(--violet); background:#FCFCFF; }

section[data-testid="stSidebar"] { background:var(--paper); border-right:1px solid var(--slate-200); }
section[data-testid="stSidebar"] .block-container { padding-top:1.4rem; }

.stTabs [data-baseweb="tab-list"] { gap:.3rem; border-bottom:1px solid var(--slate-200); }
.stTabs [data-baseweb="tab"] {
    font-size:.88rem; font-weight:600; color:var(--slate-500);
    border-radius:var(--radius-sm) var(--radius-sm) 0 0; padding:.55rem 1rem;
}
.stTabs [aria-selected="true"] { color:var(--violet) !important; background:var(--violet-soft) !important; }

div[data-testid="stExpander"] {
    border:1px solid var(--slate-200) !important; border-radius:var(--radius-sm) !important;
    background:var(--paper) !important; box-shadow:var(--shadow-sm);
}
.stProgress > div > div > div { background:var(--accent-gradient) !important; }
.stDataFrame { border-radius:var(--radius-sm); overflow:hidden; border:1px solid var(--slate-200); }
hr { border:none; border-top:1px solid var(--slate-200); margin:1.5rem 0; }

.sidebar-brand {
    display:flex; align-items:center; gap:.65rem;
    padding-bottom:1rem; margin-bottom:.5rem; border-bottom:1px solid var(--slate-200);
}
.sidebar-mark {
    width:34px; height:34px; border-radius:9px; background:var(--accent-gradient);
    display:flex; align-items:center; justify-content:center; font-size:1.05rem;
    box-shadow:0 3px 10px rgba(109,94,248,.32);
}
.sidebar-name { font-size:.97rem; font-weight:800; color:var(--ink-900); line-height:1.15; }
.sidebar-tag { font-size:.68rem; color:var(--slate-500); font-weight:500; }

.hist-item {
    background:var(--paper); border:1px solid var(--slate-200);
    border-radius:var(--radius-sm); padding:1rem 1.15rem; margin-bottom:.7rem;
    transition:all .18s ease;
}
.hist-item:hover { border-color:var(--violet); box-shadow:var(--shadow-md); }
.hist-title { font-size:.95rem; font-weight:700; color:var(--ink-800); margin-bottom:.3rem; }
.hist-meta { font-size:.75rem; color:var(--slate-500); font-family:'JetBrains Mono', monospace; }

.footer-note {
    text-align:center; font-size:.78rem; color:var(--slate-400);
    padding:2.5rem 0 1rem; line-height:1.7;
}
</style>
"""
