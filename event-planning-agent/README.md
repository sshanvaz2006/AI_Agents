# 🎉 AI Event Planning Agent

An AI agent that turns a short event brief into a complete, actionable plan —
venue options, a costed budget, a phased checklist with owners and deadlines,
equipment lists, an invitation strategy, a run-of-show and a risk register.

Built as a **B.Tech final year project** to demonstrate **planning and task
organisation** with LLM agents, powered by **Groq's** fast inference.

---

## ✨ Features

- **8 event types** — birthday, workshop, conference, college fest, seminar,
  wedding, hackathon, corporate. Each carries its own domain knowledge, so a
  hackathon plan foregrounds power and bandwidth while a wedding plan
  foregrounds catering and guest accommodation.
- **Scale-aware planning** — five size bands from *Intimate* (<30) to
  *Very Large* (1000+). A 20-person birthday does not get a security team; a
  2000-person fest does not get planned as a one-person job.
- **Computed budget** — line items grouped by category, with subtotal,
  adjustable contingency, grand total, per-head cost, and variance against your
  stated budget. **All arithmetic is done in Python, never by the model.**
- **Interactive checklist** — grouped into 6 phases (Planning & Approvals →
  Post-Event), each task carrying an owner role, a relative deadline resolved to
  a real calendar date, and a priority. Tick items off with a live progress bar.
- **Venue recommendations** — three costed options with capacity fit and
  reasoning, plus a layout suggestion and a must-have requirements list.
- **Invitation strategy** — channels, send schedule, guest segments with counts,
  RSVP method, and a ready-to-send sample invitation.
- **Risk register** — likelihood-rated risks with concrete mitigations.
- **Iterative refinement** — one-click *Cut Costs 20%*, *Make It Premium*,
  *More Detail*, *Simplify*, plus a free-text custom revision box.
- **Local budget sliders** — change the contingency % or scale every unit cost
  ±50% and the whole budget recomputes instantly, with no further API calls.
- **5 export formats** — Word (`.docx`), Markdown, plain text, checklist CSV
  (importable into Excel/Trello/Notion), budget CSV, and raw JSON.
- **Offline demo mode** — with no API key the app falls back to a rule-based
  template planner so the interface can be demonstrated without network access.
- **Honest status badges** — 🟢 live / 🟡 offline / 🔴 error are three *distinct*
  states, so a failing API call can never be mistaken for "no key configured".

---

## 🛠️ Tech Stack

| Layer             | Technology                                        |
|-------------------|---------------------------------------------------|
| App framework     | Streamlit                                         |
| Navigation        | streamlit-option-menu                             |
| Styling           | Custom CSS design system (Google Fonts, gradients)|
| LLM               | Groq API (`groq` SDK, GPT-OSS 120B by default)    |
| Budget engine     | Pure Python (`budget.py`) — no LLM involvement    |
| Document export   | python-docx                                       |
| Language          | Python 3.10+                                      |

---

## 📁 Project Structure

```
event-planning-agent/
├── app.py               # Streamlit UI, 5 pages, routing, state
├── prompts.py           # Prompt engineering: schema, event types, scale bands
├── llm.py               # Groq client, JSON recovery parsing, offline fallback
├── budget.py            # Deterministic budget arithmetic — no LLM
├── export_utils.py      # .docx / .md / .txt / .csv / .json exporters
├── styles.py            # Custom CSS design system
├── requirements.txt
├── .env.example
├── .gitignore
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

---

## 🚀 Getting Started

### 1. Install

```bash
cd event-planning-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your Groq API key

Get a **free** key at https://console.groq.com/keys, then either:

```bash
# Option A — environment variable
export GROQ_API_KEY=gsk_...          # Windows: set GROQ_API_KEY=gsk_...

# Option B — .env file
cp .env.example .env                 # then edit .env with your real key
```

…or just paste it into the sidebar at runtime (nothing is written to disk).

> **No key?** The app still runs in offline demo mode using a template planner,
> clearly marked with a 🟡 badge.

### 3. Run

```bash
streamlit run app.py
```

The form is pre-filled with a realistic brief — just press **Generate Event
Plan** to see output immediately.

### 4. Verify the AI is actually running

Click **⚡ Test connection** in the sidebar. It makes a real round-trip to Groq
and reports the exact error if anything is wrong. A 🟢 *Live* badge on the
output means the model genuinely produced the plan; 🟡 means you are seeing the
template fallback.

---

## 🧠 How It Works

### Design decision 1: the model never does arithmetic

This is the most important idea in the project.

Language models are unreliable at multi-step arithmetic. Ask one for a budget
and it will confidently return line items whose stated total is simply wrong —
and a budget that does not add up destroys credibility instantly.

So the model is **only ever asked for `unit_cost` and `quantity`**:

```json
{"category": "Catering", "item": "Lunch buffet",
 "unit_cost": 350, "quantity": 150, "unit": "person"}
```

Every multiplication, subtotal, contingency, per-head figure, category
percentage and variance against the target is computed in `budget.py` with
Python. The budget is therefore **guaranteed internally consistent no matter
what the model returns** — and the contingency and cost-scaling sliders
recompute instantly without another API call.

### Design decision 2: deadlines are relative, not absolute

The model emits `days_before_event` as an integer, never a calendar date.
Models routinely invent dates that fall *after* the event or land on impossible
days. Resolving offsets against the real event date in Python guarantees a
coherent timeline — and it means changing the event date reflows the entire
plan without regenerating it.

### Design decision 3: scale changes the plan qualitatively

`prompts.py` defines five scale bands, each with explicit guidance injected
into the system prompt. Under 30 guests the model is told to *skip* formal
registration and volunteer hierarchies; over 1000 it is told to require
permits, ambulance standby and fire clearance. Size changes the *kind* of plan,
not just the numbers in it.

### Prompt engineering (`prompts.py`)

- **`BASE_SYSTEM_PROMPT`** — the "Orchestrate" persona plus eight hard rules:
  never do arithmetic, scale to the event, be specific not generic, use
  realistic local costs, relative deadlines only, respect the fixed category and
  phase vocabularies, cover the full lifecycle including post-event, and be
  honest about risk.
- **Embedded JSON Schema** — the exact output shape with fallback values.
- **Event-type and scale-band modifiers** — appended to the system prompt.
- **Revision prompts** — operate on the existing JSON, so refinement is cheap
  and cannot introduce unrelated changes.

### Reliability engineering (`llm.py`)

| Failure mode | Mitigation |
|---|---|
| Model wraps JSON in ``` fences | 4-strategy `_extract_json`: direct parse → fence regex → brace matching (string/escape aware) → trailing-comma repair |
| Reasoning models emit a preamble | Brace matching skips it |
| Costs returned as `"₹1,500"` or `"approx 500"` | `budget._to_float` strips non-numeric characters |
| Invalid category or phase | Coerced to a valid one (case-insensitive match, else default) |
| Invalid priority | Coerced to `Medium` |
| Negative cost / zero quantity | Clamped to safe values |
| Model decommissioned / bad key / rate limit | Errors translated to plain English |
| API fails | Falls back to the template planner, badge turns 🔴 **error** (not 🟡 offline) |

### Model choice

Default is **`openai/gpt-oss-120b`**. Groq decommissioned
`llama-3.3-70b-versatile` and `llama-3.1-8b-instant` on **16 August 2026**, so
those models are deliberately not offered. See
https://console.groq.com/docs/deprecations.

---

## ☁️ Deploying on Streamlit Community Cloud

1. Push to GitHub.
2. https://share.streamlit.io → **New app** → select the repo and set the main
   file to `event-planning-agent/app.py`.
3. **Settings → Secrets**, paste:
   ```toml
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```
4. Deploy. `get_api_key()` picks it up from `st.secrets` automatically.

---

## 📌 Notes for Submission / Demo

**A good 3-minute demo runs like this:**

1. Leave the defaults (Workshop, 150 people, ₹75,000) and hit **Generate Event
   Plan**. A one-line brief becomes a full plan in seconds.
2. Point at the **metric strip** — total cost, per head, task count, milestones,
   essentials, risks. The plan is quantified, not just prose.
3. Show the **budget breakdown bar** and note the over/under-budget warning.
4. Switch to the **Checklist** page — 26 tasks across 6 phases, each with an
   owner and a *real calendar date* computed from the event date. Tick a few
   off to show the progress bar move.
5. Switch to the **Budget** page and drag the **contingency** and **cost
   scaling** sliders — everything recomputes instantly with no API call. This is
   the moment to explain that Python owns the arithmetic.
6. Change **attendees** from 150 to 2000 and regenerate — show that the plan
   gains security, permits and volunteer structure. Scale changes the plan.
7. Download the **.docx** and open it.

**Anticipated viva questions:**

- *"How do you know the budget is correct?"* → The model never computes
  anything. It proposes unit costs and quantities; `budget.py` does every
  multiplication and sum in Python. Show the sliders recomputing live.
- *"How is this different from just asking ChatGPT for an event plan?"* →
  Schema-constrained structured output, scale-aware prompting, deterministic
  arithmetic, resolved calendar dates, and five machine-readable export formats.
  The output is *data*, not prose.
- *"What if the model returns malformed JSON?"* → Four-stage recovery parser,
  then `_normalise()` type coercion, then graceful fallback to the template.
- *"How do the recommendations get customised?"* → Two axes: event type (8
  domain profiles) × scale band (5 size profiles), both injected into the system
  prompt.
- *"How do you know the AI is running and not the fallback?"* → Three distinct
  status badges plus the **Test connection** button.

**Known limitations (stated honestly):**

- Cost estimates are the model's best guess for the region given and must be
  validated against real quotes before committing money.
- Offline mode is a fixed template — it demonstrates the interface without an
  API key but does not adapt to the brief.
- Checklist completion state and history are session-only and lost on refresh.
  SQLite persistence is the obvious next extension.

---

*Built with Streamlit · Powered by Groq*
