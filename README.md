# ClausIQ — Governed Agentic Contract Intelligence

An end-to-end, multi-agent CLM platform that ingests a commercial contract and takes it
through the full agentic pipeline: **clause extraction → playbook-based risk
classification → justified redline drafting → agent-vs-agent negotiation → a
human-in-the-loop action gate with a tamper-evident audit trail**.

Built for an Agentic AI coursework demonstration, but designed as a product: a polished,
offline-capable UI, a governed architecture, and a model layer that runs on **Groq's free
LLM API** when a key is present and falls back to a deterministic demo engine when it is
not — so the live demo can never fail silently.

---

## The five tasks (T1 → T5)

| # | Task | Agentic skill demonstrated | Where |
|---|---|---|---|
| T1 | Clause extraction & structuring | Structured extraction, tool use | `app/agents/extractor.py` |
| T2 | Playbook-based risk classification | Rule grounding, traceable verdicts | `app/agents/risk.py` |
| T3 | Justified redline generation | Multi-step drafting, citation to rule | `app/agents/redline.py` |
| T4 | Simulated negotiation (agent vs agent) | Multi-agent orchestration, turn-taking | `app/agents/negotiation.py` |
| T5 | Action gate + audit trail | Policy enforcement, chain-hashed logging | `app/agents/gate.py`, `app/audit.py` |

Every verdict is traceable: **risk flag → exact clause → exact playbook rule**. Every
consequential action (send to counterparty, accept terms, escalate) stops at the approval
gate. Every event lands in an append-only log where each entry commits to the hash of its
predecessor, making the chain tamper-evident.

## Quick start

```powershell
cd clausiq

# 1) Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

# 2) Install dependencies
pip install -r requirements.txt

# 3) (Optional) connect Groq — see below

# 4) Run
python run.py
```

Open **http://localhost:8000**. Interactive API docs live at
**http://localhost:8000/api/docs**.

### Alternative with `uv` (faster)

```powershell
uv venv
uv pip install -r requirements.txt
uv run python run.py
```

## Connect Groq (free LLM API) from the terminal

1. Create a free key at <https://console.groq.com/keys>.
2. Set it from the terminal **before starting the server**:

**Windows PowerShell**

```powershell
$env:GROQ_API_KEY="gsk_your_key_here"          # current session only
setx GROQ_API_KEY "gsk_your_key_here"          # persist across restarts
```

**Windows cmd**

```cmd
set GROQ_API_KEY=gsk_your_key_here
setx GROQ_API_KEY "gsk_your_key_here"
```

**macOS / Linux**

```bash
export GROQ_API_KEY="gsk_your_key_here"
echo 'export GROQ_API_KEY="gsk_your_key_here"' >> ~/.bashrc
```

Or copy `.env.example` to `.env` and set `GROQ_API_KEY` there — the app reads `.env`
automatically. Optional overrides: `GROQ_MODEL` (default `llama-3.3-70b-versatile`),
`MAX_NEGOTIATION_ROUNDS`, `SESSION_TTL_SECONDS`.

Helper: `.\scripts\set_groq.ps1` prompts for the key and writes it into `.env` for you.

> No key? The platform still runs completely — every agent falls back to a deterministic
> rule engine, so extraction, risk scoring, redlines, negotiation and the gate all work
> for offline demos. The Settings page shows which mode you are in.

## Dummy login (seeded accounts)

| Name | Email | Password | Role |
|---|---|---|---|
| Yashwanth Reddy | `yash@nimbus.app` | `demo123` | Founder |
| Maya Krishnan | `maya@nimbus.app` | `demo123` | Legal Reviewer |
| ClausIQ Admin | `admin@clausiq.io` | `admin123` | Administrator |

The login screen has one-click autofill chips for all three.

## Demo in 60 seconds

1. Sign in with any account above.
2. **Contracts → load the "CloudBase vendor agreement" sample** (or upload your own
   PDF / DOCX / TXT).
3. Click **Run AI Review** — watch the four-stage pipeline complete.
4. Open **Review Studio**: see the clause list, the risk verdict for each clause (click
   through them), the rule that triggered it, and the diffed redline. Accept or reject
   redlines.
5. Click **Start Negotiation** — the company agent and the CloudBase agent exchange
   proposals round by round until they converge.
6. Open **Approval Gate** — approve or reject the queued real-world actions
   (send package, accept terms, escalate).
7. Run the **Red-Team Test** — 10 unsafe agent actions, 100% gated.
8. Inspect the **Audit Trail** — full chain-verified history of every step.

The bundled samples are `cloudbase-vendor-agreement`, `mutual-nda`,
`employment-offer` and `event-management-agreement` (a real PDF) in
`data/sample_contracts/`. `scripts/generate_sample_contract.py` regenerates the PDF.

## Architecture

```
Contract (PDF / DOCX / TXT)
        │
        ▼
┌──────────────────────┐
│ T1  Extractor agent  │──► clauses table (source-tracked)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐      ┌──────────────────┐
│ T2  Risk classifier  │◄────►│ Playbook store    │
│     (rule-grounded)  │      │ (YAML, per side)  │
└──────────────────────┘      └──────────────────┘
        │
        ▼
┌──────────────────────┐
│ T3  Redline drafter  │──► minimal, diffable rewrites + justification
└──────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│ T4  Negotiation controller    │◄──► Counterparty agent (own playbook)
│     turn-taking, convergence  │
└──────────────────────────────┘
        │
        ▼
┌──────────────────────────────┐
│ T5  Action gate + audit log   │──► Human approval UI (auto / approval / block)
└──────────────────────────────┘
        │
        ▼
 Final negotiated contract + complete audit trail
```

- **Backend:** FastAPI + SQLite (WAL), background jobs with stage progress.
- **Frontend:** hand-crafted single-page app (vanilla JS, no build step, no CDN) —
  dashboard, review studio with word-level diff viewer, live negotiation transcript,
  approval queue, red-team test, chain-verified audit table.
- **LLM layer:** Groq (OpenAI-compatible) with automatic fallback to the local engine.
- **Governance:** deterministic policy table (auto / requires-approval / hard-block),
  fail-closed for unknown actions, chain-hashed append-only audit log.

## Project layout

```
clausiq/
├── app/
│   ├── agents/          # extractor, risk, redline, negotiation, gate
│   ├── playbooks/       # startup-friendly, vendor-friendly, balanced (YAML)
│   ├── routes/          # auth, contracts, governance, meta
│   ├── audit.py         # chain-hashed append-only log
│   ├── db.py            # SQLite schema + seeds
│   ├── pipeline.py      # T1→T2→T3 orchestration with progress
│   ├── llm.py           # Groq client + fallback contract
│   └── main.py          # FastAPI app
├── data/sample_contracts/  # CloudBase MSA, mutual NDA, employment offer
├── static/              # SPA (css + js, fully offline)
├── scripts/             # helper scripts
├── requirements.txt
└── .env.example
```

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Dummy login → bearer token |
| POST | `/api/contracts/upload` | Upload + ingest PDF/DOCX/TXT |
| POST | `/api/samples/{name}/load` | Load a bundled sample |
| POST | `/api/contracts/{id}/review` | Start T1→T2→T3 (returns job id) |
| GET | `/api/jobs/{job_id}` | Poll pipeline progress |
| POST | `/api/contracts/{id}/negotiate` | Start T4 agent negotiation |
| GET | `/api/contracts/{id}/negotiation` | Transcript + outcome |
| GET/POST | `/api/approvals`, `/api/approvals/{id}/decision` | Human approval gate |
| GET | `/api/audit` | Chain-verified audit trail |
| POST | `/api/redteam` | 10-action gate red-team test |
| GET | `/api/playbooks`, `/api/dashboard`, `/api/settings` | Meta endpoints |
