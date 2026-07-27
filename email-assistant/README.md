<<<<<<< HEAD
# ✉️ Smart Email Assistant

An AI-powered agent that composes professional emails — job applications, leave
requests, meeting invitations, customer support replies, complaints, and
follow-ups — in a tone of your choice, with regenerate / grammar-fix / tone-
change / shorten-expand controls.

Built as a **B.Tech final year project** to demonstrate prompt engineering and
context-aware natural language generation, powered by **Groq's** ultra-fast
LLM inference.

---

## ✨ Features

- **6 email categories**: job application, leave request, meeting invitation,
  customer support, complaint, follow-up (+ custom/other).
- **6 writing tones**: formal, friendly, persuasive, concise, apologetic,
  assertive.
- **Iterative refinement**: regenerate, fix grammar, shorten, expand, or
  switch tone on an already-generated email.
- **Manual editing** before export.
- **Export**: copy to clipboard, download as `.txt` or `.docx`.
- **Session history** of the last 20 generated emails, reloadable.
- **Offline demo mode**: if no API key is configured, the app still runs
  using a rule-based fallback generator, clearly labeled in the UI.
- **Custom UI**: gradient hero section, card-based layout, Google Fonts —
  built with `streamlit-option-menu` and hand-written CSS instead of the
  default Streamlit theme.

---

## 🛠️ Tech Stack

| Layer            | Technology                          |
|-------------------|--------------------------------------|
| App framework     | Streamlit                           |
| Navigation/UI kit | streamlit-option-menu               |
| Styling           | Custom CSS (Google Fonts, gradients, cards) |
| LLM               | Groq API (`groq` SDK, Llama 3.3 70B by default) |
| Document export   | python-docx                         |
| Language          | Python 3.10+                        |

---

## 📁 Project Structure

```
email-assistant/
├── app.py                      # Streamlit UI, page routing, event handlers
├── prompts.py                   # Prompt-engineering layer: categories, tones, prompt builders
├── llm.py                        # Groq API client wrapper + offline fallback generator
├── export_utils.py               # .txt / .docx export helpers
├── styles.py                      # Custom CSS injected into the app
├── requirements.txt
├── .env.example
├── .gitignore
└── .streamlit/
    ├── config.toml                # Base Streamlit theme colors
    └── secrets.toml.example        # Template for Streamlit Cloud secrets
```

---

## 🚀 Getting Started (local)

### 1. Clone the repo and install dependencies

```bash
git clone https://github.com/<your-username>/smart-email-assistant.git
cd smart-email-assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your Groq API key

Get a **free** key at https://console.groq.com/keys, then use any one of:

```bash
# Option A: environment variable
export GROQ_API_KEY=gsk_...

# Option B: local .env-style file (copy the example)
cp .env.example .env   # then edit .env with your real key
```

or just paste the key into the "Model Settings" box in the app's sidebar at
runtime (nothing is written to disk).

> **No key?** The app still works — it automatically switches to an offline
> demo mode using a rule-based template generator, clearly marked with a
> 🟡 badge in the UI, so you can demo the full UX without any API cost.

### 3. Run the app

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## ☁️ Pushing to GitHub & Deploying

### Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Smart Email Assistant"
git branch -M main
git remote add origin https://github.com/<your-username>/smart-email-assistant.git
git push -u origin main
```

The included `.gitignore` already excludes `venv/`, `__pycache__/`, `.env`,
and `.streamlit/secrets.toml` — so your real API key is never committed.

### Deploy on Streamlit Community Cloud (free)

1. Push the repo to GitHub as above.
2. Go to https://share.streamlit.io → "New app" → pick your repo/branch and
   set the main file to `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```toml
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```
4. Deploy. The app will pick up the key automatically via `st.secrets`
   (see `llm.py`'s `get_api_key()`), no code changes needed.

---

## 🧠 How the Prompt Engineering Works

All prompt logic lives in `prompts.py`:

- **`BASE_SYSTEM_PROMPT`** — a persona ("Mailwright") plus hard formatting
  rules (exact `Subject: ...` output format, no fabricated facts, no
  preamble/explanation text).
- **Category & tone dictionaries** — each category carries a description and
  a hint of what details matter (e.g. for `leave_request`: dates, reason,
  handover plan); each tone carries an explicit style guide the model must
  follow.
- **Prompt builders** — `build_generation_prompt`, `build_regenerate_prompt`,
  `build_grammar_fix_prompt`, `build_tone_change_prompt`,
  `build_length_adjust_prompt` each assemble a `(system, user)` prompt pair
  for a specific action, reusing the same output-format contract so parsing
  stays simple (`parse_subject_and_body`).
- **`llm.py`** sends these as `system` / `user` messages to Groq's OpenAI-
  compatible `chat.completions.create` endpoint.

This keeps every "AI capability" in the app traceable to a specific,
inspectable prompt — useful for a viva/demo walkthrough.

---

## 📌 Notes for Submission / Demo

- Default model is `llama-3.3-70b-versatile`. You can switch to other
  Groq-hosted models (e.g. `llama-3.1-8b-instant` for speed,
  `openai/gpt-oss-120b`, `gemma2-9b-it`) from the sidebar at runtime — see
  https://console.groq.com/docs/models for the current list.
- The offline fallback mode means the app can be demoed live even without
  internet access or an API key — just less fluent than the real model.
- History is kept only in the browser session (`st.session_state`); it is
  not persisted to disk. Adding a SQLite-backed history is listed as a
  possible extension in the in-app "About" page.
=======
# AI_Agents
>>>>>>> 0e33f19b87d3fb7e67279e080d719811948d3d40
