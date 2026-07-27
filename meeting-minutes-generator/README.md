# 📝 AI Meeting Minutes Generator

An AI agent that converts raw, messy meeting transcripts into structured,
professional minutes — identifying key discussion points, decisions, assigned
responsibilities with deadlines, risks, and open questions.

Built as a **B.Tech final year project** to demonstrate **summarisation and
information extraction** with LLM agents, powered by **Groq's** fast inference.

---

## ✨ Features

- **Two input methods** — paste a transcript directly, or upload a file
  (`.txt`, `.md`, `.vtt`, `.srt`, `.log`, `.csv`). Subtitle files have their
  timing lines stripped automatically.
- **Structured extraction, not just a summary.** The agent returns a typed JSON
  object with separate fields for decisions, action items, risks and open
  questions — each action carrying an **owner**, **deadline** and **priority**.
- **7 meeting types** — general, stand-up, project review, client call,
  brainstorm, board meeting, 1-on-1. Each steers the model toward the
  information that matters for that format.
- **3 detail levels** — concise, standard, detailed.
- **Iterative refinement** — one-click *Make Concise*, *Add Detail*,
  *More Formal*, *Sharpen Actions*, plus a free-text custom revision box.
- **Gap detection** — the app counts action items with no owner or no deadline
  and flags them, rather than quietly inventing names.
- **5 export formats** — Word (`.docx`), Markdown, plain text, action-items CSV
  (importable into Excel/Jira/Trello), and raw JSON.
- **Long transcript support** — transcripts over ~48k characters are condensed
  segment-by-segment (map-reduce) before extraction.
- **Offline demo mode** — with no API key the app falls back to a rule-based
  keyword extractor so the interface can be demonstrated without network access.
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
| Document export   | python-docx                                       |
| Language          | Python 3.10+                                      |

---

## 📁 Project Structure

```
meeting-minutes-generator/
├── app.py               # Streamlit UI, routing, state, rendering
├── prompts.py           # Prompt-engineering layer: schema, meeting types, builders
├── llm.py               # Groq client, JSON recovery parsing, offline fallback
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
cd meeting-minutes-generator
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

> **No key?** The app still runs in offline demo mode using a rule-based
> extractor, clearly marked with a 🟡 badge.

### 3. Run

```bash
streamlit run app.py
```

Then click **Load sample** → **Generate Minutes** to see it work immediately.

### 4. Verify the AI is actually running

Click **⚡ Test connection** in the sidebar. It makes a real round-trip to Groq
and reports the exact error if anything is wrong. A 🟢 *Live* badge on the
output means the model genuinely produced the minutes; 🟡 means you are seeing
the rule-based fallback.

---

## 🧠 How It Works

### The core idea: extraction, not summarisation

Asking a model for "a summary" returns prose you must re-read. This agent asks
for a **schema** and gets back data:

```json
{
  "action_items": [
    {"task": "Write the phased migration runbook",
     "owner": "Arjun Rao",
     "deadline": "Monday",
     "priority": "High"}
  ],
  "decisions": [
    {"decision": "Adopt a phased migration instead of a single cutover",
     "rationale": "A naive migration would need ~3 hours of downtime",
     "owner": "Arjun Rao"}
  ]
}
```

Because the output is structured, action items become a sortable table and a
CSV import; unassigned owners can be *counted* and flagged; and the same
extraction renders as Word, Markdown or JSON without calling the model again.

### Prompt engineering (`prompts.py`)

- **`BASE_SYSTEM_PROMPT`** — the "Scribe" persona plus seven hard rules, most
  importantly: never fabricate, distinguish *discussion* from *decision*,
  distinguish *decision* from *action*, and prefer `"Unassigned"` over guessing.
- **Embedded JSON Schema** — the exact output shape, including fallback values
  for missing information.
- **Meeting-type and detail-level modifiers** — appended to the system prompt so
  a stand-up and a board meeting are minuted differently.
- **Revision prompts** — operate on the existing JSON, not the transcript, so
  refinement is cheap and cannot introduce new facts.

### Reliability engineering (`llm.py`)

Real LLM apps break in predictable ways, and each is handled explicitly:

| Failure mode | Mitigation |
|---|---|
| Model wraps JSON in ``` fences | 4-strategy `_extract_json`: direct parse → fence regex → brace matching (string/escape aware) → trailing-comma repair |
| Reasoning models emit a preamble | Brace matching skips it |
| Model returns wrong types (string where list expected) | `_normalise()` coerces every field |
| Invalid priority value | Coerced to `Medium` |
| Transcript exceeds context window | Map-reduce chunking on paragraph boundaries |
| Model decommissioned / bad key / rate limit | Error messages translated to plain English |
| API fails | Falls back to offline draft, badge turns 🔴 **error** (not 🟡 offline) |

### Model choice

Default is **`openai/gpt-oss-120b`**. Groq decommissioned
`llama-3.3-70b-versatile` and `llama-3.1-8b-instant` on **16 August 2026**, so
those models are deliberately not offered. See
https://console.groq.com/docs/deprecations.

---

## ☁️ Deploying on Streamlit Community Cloud

1. Push to GitHub.
2. https://share.streamlit.io → **New app** → select the repo and set the main
   file to `app.py` (or `meeting-minutes-generator/app.py` if nested).
3. **Settings → Secrets**, paste:
   ```toml
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```
4. Deploy. `get_api_key()` picks it up from `st.secrets` automatically.

---

## 📌 Notes for Submission / Demo

**A good 3-minute demo runs like this:**

1. Click **Load sample**, then **Generate Minutes** — a 473-word messy
   transcript becomes structured minutes in a few seconds.
2. Point out the **metric strip** (attendees / topics / decisions / actions /
   risks / questions) — the extraction is quantified.
3. Scroll to the **action items table** and the ⚠︎ gap warning — show that the
   agent flags what it *doesn't* know instead of hallucinating.
4. Open **🔍 Structured data** to reveal the underlying JSON. This is the
   moment to explain extraction vs. summarisation.
5. Click **Make Concise** to show iterative refinement operating on the JSON.
6. Download the **.docx** and open it.

**Anticipated viva questions:**

- *"How do you stop it inventing action items?"* → Explicit anti-fabrication
  rules, the `"Unassigned"` sentinel, and the UI counting unassigned items.
- *"What if the model returns malformed JSON?"* → Four-stage recovery parser,
  then `_normalise()`, then graceful fallback.
- *"How does it handle a two-hour meeting?"* → Map-reduce chunking.
- *"How do you know the AI is running and not the fallback?"* → Three distinct
  status badges plus the **Test connection** button.

**Known limitations (stated honestly):**

- The agent can only extract what the transcript states; implicit ownership
  surfaces as `"Unassigned"` by design.
- Offline mode is keyword-based — a UX demonstration, not a model substitute.
- History is session-only and lost on refresh. SQLite persistence is the
  obvious next extension.

---

*Built with Streamlit · Powered by Groq*
