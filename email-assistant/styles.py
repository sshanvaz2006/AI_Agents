"""
styles.py
---------
All custom CSS lives here so app.py stays focused on logic/layout.
Uses Google Fonts + hand-rolled CSS (cards, gradient hero, chips, buttons)
to move the UI away from stock Streamlit look-and-feel.
"""

CUSTOM_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

<style>
:root {
    --brand-primary: #4F46E5;
    --brand-primary-dark: #3730A3;
    --brand-accent: #22C55E;
    --brand-warn: #F59E0B;
    --brand-danger: #EF4444;
    --surface: #FFFFFF;
    --surface-muted: #F4F4FB;
    --text-main: #1E1E2E;
    --text-muted: #6B7280;
    --radius-lg: 18px;
    --radius-md: 12px;
}

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, h4, .hero-title {
    font-family: 'Poppins', sans-serif !important;
}

/* Hide default streamlit chrome for a cleaner "product" feel */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container {
    padding-top: 1.5rem;
    max-width: 1100px;
}

/* ---------------- HERO ---------------- */
.hero {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 55%, #DB2777 100%);
    padding: 2.6rem 2.4rem;
    border-radius: var(--radius-lg);
    color: white;
    margin-bottom: 1.6rem;
    box-shadow: 0 12px 30px -12px rgba(79, 70, 229, 0.55);
}
.hero-title {
    font-size: 2.1rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}
.hero-subtitle {
    font-size: 1.02rem;
    opacity: 0.92;
    max-width: 640px;
    line-height: 1.5;
}
.hero-badges {
    margin-top: 1rem;
}
.hero-badge {
    display: inline-block;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.35);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    margin-right: 8px;
    margin-bottom: 6px;
}

/* ---------------- CARDS ---------------- */
.feature-card {
    background: var(--surface);
    border: 1px solid #ECECF5;
    border-radius: var(--radius-md);
    padding: 1.1rem 1.2rem;
    height: 100%;
    box-shadow: 0 4px 14px -8px rgba(30,30,46,0.12);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 22px -10px rgba(30,30,46,0.22);
}
.feature-card .emoji {
    font-size: 1.6rem;
}
.feature-card h4 {
    margin: 0.4rem 0 0.25rem 0;
    font-size: 1.02rem;
    color: var(--text-main);
}
.feature-card p {
    color: var(--text-muted);
    font-size: 0.88rem;
    margin: 0;
    line-height: 1.4;
}

.email-card {
    background: var(--surface);
    border: 1px solid #ECECF5;
    border-left: 5px solid var(--brand-primary);
    border-radius: var(--radius-md);
    padding: 1.3rem 1.5rem;
    box-shadow: 0 6px 20px -12px rgba(30,30,46,0.18);
    margin-top: 0.6rem;
    margin-bottom: 1rem;
}
.email-subject {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    font-size: 1.05rem;
    color: var(--brand-primary-dark);
    margin-bottom: 0.6rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px dashed #E0E0EE;
}
.email-body {
    white-space: pre-wrap;
    font-size: 0.95rem;
    line-height: 1.65;
    color: var(--text-main);
}

.section-label {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.35rem;
    margin-top: 0.6rem;
}

.stat-pill {
    display: inline-block;
    background: var(--surface-muted);
    border-radius: 999px;
    padding: 3px 11px;
    font-size: 0.76rem;
    color: var(--text-muted);
    margin-right: 6px;
}

.history-item {
    background: var(--surface);
    border: 1px solid #ECECF5;
    border-radius: var(--radius-md);
    padding: 0.75rem 1rem;
    margin-bottom: 0.6rem;
}
.history-item .h-subject {
    font-weight: 600;
    font-size: 0.92rem;
    color: var(--text-main);
}
.history-item .h-meta {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 2px;
}

.footer-note {
    text-align: center;
    color: var(--text-muted);
    font-size: 0.78rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #ECECF5;
}

/* Buttons */
div.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid #E0E0EE;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-primary), #7C3AED);
    border: none;
}

.badge-offline {
    background: #FEF3C7;
    color: #92400E;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-online {
    background: #DCFCE7;
    color: #166534;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
</style>
"""
