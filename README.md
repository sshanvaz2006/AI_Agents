<div align="center">
🤖 AI Agents
A growing collection of production-minded AI agents
Each agent is a self-contained Streamlit application built on a shared architecture —
schema-constrained LLM output, deterministic post-processing, and graceful degradation.

<br>
AgentsPythonStreamlitGroqMIT

<br>
Explore the Agents  ·  Quick Start  ·  Architecture  ·  Roadmap

</div><br>
<br>
🎯 About This Repository
This repository collects AI agents that each solve one real problem end to end.

They are deliberately not thin wrappers around a chat prompt. Every agent
follows the same discipline:

<table> <tr> <td width="50%" valign="top">
🧱 Structured output over prose

Agents request a JSON schema, not free text. The result is data — sortable,
exportable, and renderable in five formats without another API call.

</td> <td width="50%" valign="top">
🧮 Code owns the logic

Anything a language model is bad at — arithmetic, date maths, validation — is
computed in Python, never trusted to the model.

</td> </tr> <tr> <td width="50%" valign="top">
🛡️ Failure is designed for

Multi-strategy JSON recovery, type coercion on every field, plain-English error
translation, and an offline fallback so nothing ever hard-crashes.

</td> <td width="50%" valign="top">
🔍 Honest status reporting

Three distinct states — 🟢 live, 🟡 offline, 🔴 error — so a broken API call can
never masquerade as "no key configured".

</td> </tr> </table><br>
<br>
🚀 The Agents
<br><!-- ════════════════════════════════════════════════════════════ --><!-- AGENT 01 --><!-- ════════════════════════════════════════════════════════════ --><div align="center">
✉️  01 · Smart Email Assistant
Composes professional emails in the tone you choose

OpenStatusFocus

</div>
Turns a one-line intent into a polished email — job applications, leave requests,
meeting invitations, customer support replies, complaints and follow-ups — with
regenerate, grammar-fix, tone-change and length controls.

<details> <summary><b>📖 &nbsp;Details</b></summary><br>
Problem	Writing professional emails is slow, and tone is hard to get right.
Approach	Category × tone prompt matrix with a strict Subject: output contract.
Highlights	6 categories · 6 tones · iterative refinement · manual editing · session history
Exports	.txt · .docx · clipboard
Demonstrates: prompt engineering, context-aware generation, output-format contracts

</details><br><!-- ════════════════════════════════════════════════════════════ --><!-- AGENT 02 --><!-- ════════════════════════════════════════════════════════════ --><div align="center">
📝  02 · Meeting Minutes Generator
Converts messy transcripts into board-ready minutes

OpenStatusFocus

</div>
Reads a raw transcript and extracts discussion points, decisions, action items
with owners and deadlines, risks and open questions — each as a typed field,
not a paragraph.

<details> <summary><b>📖 &nbsp;Details</b></summary><br>
Problem	Meeting notes are unstructured; actions get lost and owners stay vague.
Approach	Schema-constrained extraction into typed JSON, then rendered five ways.
Highlights	7 meeting types · 3 detail levels · gap detection for unassigned owners · map-reduce chunking for long transcripts
Inputs	Paste text · upload .txt .md .vtt .srt .log .csv
Exports	.docx · Markdown · plain text · action-items .csv · JSON
The interesting bit — the agent flags what it doesn't know. Rather than
inventing an owner, it writes "Unassigned" and the UI counts and surfaces those
gaps. An honest hole beats a confident hallucination.

Demonstrates: summarisation, information extraction, structured output, defensive parsing

</details><br><!-- ════════════════════════════════════════════════════════════ --><!-- AGENT 03 --><!-- ════════════════════════════════════════════════════════════ --><div align="center">
🎉  03 · Event Planning Agent
Turns a one-line brief into a complete event plan

OpenStatusFocus

</div>
Builds venue options, a costed budget, a phased checklist with owners and real
calendar deadlines, equipment lists, an invitation strategy, a run-of-show and
a risk register — all scaled to the size and type of your event.

<details> <summary><b>📖 &nbsp;Details</b></summary><br>
Problem	Event planning is a coordination problem; generic checklists don't scale with size.
Approach	8 event types × 5 scale bands, with all arithmetic done in Python.
Highlights	Interactive tick-box checklist · live budget sliders · variance vs. target · risk register
Exports	.docx · Markdown · plain text · checklist .csv · budget .csv · JSON
The interesting bit — the model never does maths. It proposes only
unit_cost and quantity; every subtotal, contingency, per-head figure and
budget variance is computed in budget.py. The budget is therefore guaranteed
internally consistent regardless of what the model returns — and the sliders
recompute instantly with zero API calls.

Demonstrates: planning, task organisation, deterministic post-processing, scale-aware prompting

</details><br>
<br>
⚡ Quick Start
Every agent runs the same way. Replace <agent-folder> with any project above.

Bash

# 1 · Clone
git clone https://github.com/sshanvaz2006/AI_Agents.git
cd AI_Agents/<agent-folder>

# 2 · Environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3 · Key  →  free at https://console.groq.com/keys
cp .env.example .env              # then paste your key into .env

# 4 · Run
streamlit run app.py
Open http://localhost:8501.

[!TIP]
No API key? Every agent still runs in offline demo mode using a
rule-based fallback, clearly marked with a 🟡 badge — so you can explore the
full interface with zero setup and zero cost.

[!IMPORTANT]
Verify the AI is actually running. Click ⚡ Test connection in the
sidebar. A 🟢 Live badge means the model genuinely produced the output;
🟡 means you're seeing the fallback. Never assume — check the badge.

<br>
<br>
🧬 Shared Architecture
Every agent follows the same five-module layout, so learning one means knowing
them all.

text

<agent-folder>/
│
├── app.py             ·  Streamlit UI · routing · session state · rendering
├── prompts.py         ·  Prompt engineering · JSON schema · domain profiles
├── llm.py             ·  Groq client · JSON recovery · normalisation · fallback
├── export_utils.py    ·  DOCX · Markdown · TXT · CSV · JSON exporters
├── styles.py          ·  Custom CSS design system
│
├── requirements.txt   ·  Pinned to tested versions
├── .env.example       ·  Key template  (real .env is gitignored)
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
<details> <summary><b>🔧 &nbsp;The reliability layer — how these survive real LLM behaviour</b></summary><br>
LLM apps break in predictable ways. Each is handled explicitly rather than hoped away:

Failure mode	Mitigation
Model wraps JSON in ``` fences	4-strategy extraction: direct parse → fence regex → brace matching → comma repair
Reasoning models emit a <think> preamble	Brace matching skips it
Wrong types returned (string where list expected)	_normalise() coerces every field
Numbers arrive as "₹1,500" or "approx 500"	Numeric coercion strips non-numeric characters
Invalid enum values	Snapped to the nearest valid value, else a safe default
Input exceeds the context window	Map-reduce chunking on paragraph boundaries
Model decommissioned · bad key · rate limit	Errors translated into plain English
Any API failure	Falls back to offline output; badge turns 🔴 error, never 🟡 offline
</details><details> <summary><b>🎨 &nbsp;Design system — each agent has its own visual identity</b></summary><br>
Agent	Palette	Display font
✉️ Email Assistant	Violet → Indigo	Inter
📝 Minutes Generator	Violet → Cyan on slate	Instrument Serif
🎉 Event Planner	Coral → Amber on cream	Fraunces
Every UI is hand-written CSS rather than the default Streamlit theme — custom
gradients, layered shadows, hairline borders and restrained motion.

</details><details> <summary><b>🤖 &nbsp;Model configuration</b></summary><br>
All agents default to openai/gpt-oss-120b on Groq, selectable at runtime.

Model	Best for
openai/gpt-oss-120b	Highest quality — the default
openai/gpt-oss-20b	Faster, lighter
qwen/qwen3.6-27b	Alternative
moonshotai/kimi-k2-instruct-0905	Long context
[!WARNING]
llama-3.3-70b-versatile and llama-3.1-8b-instant were decommissioned by
Groq on 16 August 2026 and are deliberately not offered.
See the deprecation notice.

</details><br>
<br>
🗺️ Roadmap
Agents planned for this collection:

Agent	Focus
⬜	Resume Analyser	JD matching · gap analysis · ATS scoring
⬜	Study Planner	Syllabus → spaced-repetition schedule
⬜	Code Review Assistant	Static analysis + LLM review commentary
⬜	Research Summariser	Multi-paper synthesis with citations
⬜	Interview Prep Coach	Role-specific Q&A with feedback
Cross-cutting improvements:

 SQLite persistence for history across all agents
 Shared common/ package for the LLM client and export layer
 Unit test suite with CI
 Live deployments on Streamlit Community Cloud
 Dockerfile per agent
<br>
<br>
➕ Adding a New Agent
<details> <summary><b>Contribution pattern — click to expand</b></summary><br>
1 · Create a folder at the repository root:

Bash

mkdir my-new-agent && cd my-new-agent
2 · Follow the five-module layout (app.py, prompts.py, llm.py,
export_utils.py, styles.py) so the codebase stays predictable.

3 · Include requirements.txt, .env.example, .gitignore and a project
README.md.

4 · Confirm your key is never committed:

Bash

git check-ignore -v .env      # must print a .gitignore line
5 · Add a card to the Agents section using this template:

Markdown

<div align="center">

### 🔧 &nbsp;NN · Agent Name

**One-line description**

[![Open](https://img.shields.io/badge/📂_Open_Project-folder--name-6D5EF8?style=flat-square)](./folder-name)
![Status](https://img.shields.io/badge/status-stable-10B981?style=flat-square)
![Focus](https://img.shields.io/badge/focus-Capability-64748B?style=flat-square)

</div>

> Two-line summary of what it does and why it is useful.

<details>
<summary><b>📖 &nbsp;Details</b></summary>

<br>

|  |  |
|---|---|
| **Problem** | What real problem this solves. |
| **Approach** | The technique used. |
| **Highlights** | Key features · separated · by · dots |
| **Exports** | Formats produced |

**Demonstrates:** concepts this project showcases

</details>
6 · Bump the agent count badge at the top, and tick the roadmap entry.

</details><br>
<br>
🔐 Security
[!CAUTION]
Never commit API keys. Every agent ships with a .gitignore that excludes
.env and .streamlit/secrets.toml.

Before every push:

Bash

git status                                    # no .env, no venv/, no __pycache__
grep -rn "gsk_" . --exclude-dir=venv --exclude-dir=.git
The second command should return only .env.example placeholders. If a key
was ever exposed — in a commit, a screenshot, or a screen share — revoke it
immediately at console.groq.com/keys and
generate a new one. Deleting the file is not enough; revoking is what protects you.

<br>
<br>
🛠️ Tech Stack
<div align="center">
PythonStreamlitGroqCSS3GitVS Code

</div>
Layer	Technology
Language	Python 3.10+
UI framework	Streamlit · streamlit-option-menu
Styling	Hand-written CSS design systems · Google Fonts
LLM inference	Groq API — OpenAI-compatible endpoint
Document export	python-docx
<br>
<br>
📄 License
Released under the MIT License — free to use, modify and learn from.

<br>
<br><div align="center">
Built by Shanvaz
If any of these agents are useful to you, a ⭐ is genuinely appreciated.

<br>
GitHub

<br>
<sub>Each agent is independent — clone the whole repository or copy a single folder.</sub>

</div>
