# ClausIQ — Panel Presentation Speaker Script

How to use this: practice out loud twice, with the app open on a second screen.
Lines in quotes are spoken. Lines in `[brackets]` are actions. Keep the whole demo
to 12 minutes and leave 5 for questions.

---

## 1. Opening — the problem (2 min)

> "Good morning. I'd like to start with a company, not a slide. Imagine a 12-person
> startup called Nimbus Labs. They're about to sign a 14-page agreement with their
> cloud vendor, CloudBase. Nimbus has no lawyer on staff, and outside counsel costs
> three to six hundred dollars just to review one contract. So like most small
> companies, they'll either sign it blind or pay for a review they can't afford.
> And when something in that contract goes wrong later, it's a fifty-thousand-dollar
> problem, not a five-hundred-dollar one."

> "The tools that fix this for big companies already exist — Harvey, Ironclad,
> Legora. But they're built and priced for Am Law 100 firms and enterprise legal
> departments. Small companies get no AI help at all. That gap — between an elite
> firm with a custom Harvey deployment and a two-person startup reviewing contracts
> in Google Docs — is exactly what ClausIQ is built to close."

## 2. The pitch in one breath

> "ClausIQ is a governed, agentic contract-intelligence platform. It reads an
> unreviewed contract, breaks it into clauses, scores every clause against a
> playbook of rules, drafts surgical redlines, simulates the negotiation against
> the counterparty — and then refuses to take any real-world action until a human
> approves it, with every single step written into a tamper-evident audit trail."

## 3. Why "agentic" — say this explicitly, panels grade for it

> "A chatbot answers one question and stops. An agent plans and carries out a chain
> of connected steps. ClausIQ is a team of five cooperating agents. The extractor
> segments the document. The risk classifier judges each clause against rules. The
> drafter rewrites only what's flagged. The negotiation controller runs two
> independent agents against each other. And the action gate enforces policy on
> everything that follows. Each agent's output is the next agent's input, they all
> share one data model and one audit log — and that chain, not any single model
> call, is the product."

## 4. Architecture in 60 seconds

[Point at the pipeline diagram or draw the five boxes.]

> "Five tasks, one pipeline. Ingestion accepts PDF, DOCX and TXT. T1 — clause
> extraction with source references. T2 — playbook-based risk classification into
> green, yellow and red, where every flag must cite the exact rule that fired.
> T3 — justified redlines: minimal, diffable rewrites. T4 — the negotiation loop
> between two agents with opposing playbooks. T5 — the human-in-the-loop action
> gate, backed by an append-only audit log where every entry is chained with
> SHA-256. If a malicious actor edits any past entry, every hash after it breaks."

## 5. Live demo (7 min)

### 5.1 Login and dashboard

[Sign in with the demo account — yash@nimbus.app / demo123.]

> "Login is intentionally a dummy local account — this is coursework, no external
> identity provider. The dashboard shows real telemetry: contracts, clauses
> analyzed, high-risk clauses, and pending approvals. The pill in the corner tells
> you whether the agents are running on Groq's free LLM tier or the built-in demo
> engine."

[Open Contracts → load the CloudBase vendor agreement sample.]

> "This sample is deliberately written the way a vendor would: uncapped liability,
> seven days' termination notice, one-sided indemnity. Let's see the pipeline catch
> all of it."

### 5.2 T1–T3: Run AI Review

[Click "Run AI Review" and let the progress bar run through its four stages.]

> "Watch the stages: extracting clauses, classifying risks, drafting redlines,
> summarizing. This is a job with visible progress, not a static classifier."

[Open the clause list, then click the LIMITATION OF LIABILITY clause.]

> "Eleven clauses, each tagged by type and source location. Let me open the one
> that matters most. The original says aggregate liability is uncapped. The
> verdict is red — and look at what comes with it: rule LC-1, the full rule text,
> a one-sentence explanation, and a confidence score. You can check every flag
> against the source sentence and the rule. That traceability is exactly Gap One
> from our market research — verification debt. Most tools say 'this looks risky'
> and ask you to trust them. Here nothing is a black box."

[Scroll to the redline and show the word-level diff.]

> "Here's the proposed fix: a twelve-month fee cap with carve-outs for gross
> negligence and confidentiality breaches — shown as a diff, like track changes,
> with the justification attached. The edit is surgical; we keep changes minimal
> by construction. Accept or reject — and if I do, my decision is logged with my
> name and timestamp."

[Accept the redline.]

### 5.3 T4: Start the negotiation

[Click "Start Negotiation" and narrate the transcript.]

> "This is the part affordable tools don't have. Two independent agents negotiate,
> each bound by its own playbook. Nimbus's agent opens with all nine proposed
> changes. CloudBase's agent — given the vendor-friendly playbook — accepts seven
> and counters two: the liability cap and payment terms. Nimbus's agent holds the
> line on both. CloudBase concedes. Agreement in two rounds. The full transcript
> is preserved, so a reviewer can audit what each side conceded and why — that's
> the difference between a simulated negotiation and a chatbot pretending to
> negotiate."

### 5.4 T5: The approval gate

[Open Approval Gate; show the pending actions.]

> "Negotiation done — now the governance layer. Three actions were generated. The
> internal summary? Auto-approved by policy. But 'send the package to CloudBase'
> and 'accept final terms' are approval-tier: they sit here, pending, until a
> human decides. The AI prepared everything — it did not pull the trigger."

[Approve one with a note.]

> "Watch: approve, with a note. That note, my name, and the timestamp are now in
> the audit trail. This is Gap Two from our research — ungated autonomous action.
> In our system, the agent never acts alone where it matters."

### 5.5 Red-team test — prove the gate isn't theater

[Run the red-team test.]

> "To prove the gate is real, we attack it. Ten attempts, including auto-accepting
> a red-flagged clause, e-signing the contract on the company's behalf, and
> deleting the audit log. Ten out of ten correctly gated — the dangerous actions
> hard-blocked, the consequential ones queued for approval. The policy engine is
> deterministic and fail-closed: an action it doesn't recognize requires approval
> by default."

### 5.6 Audit trail

[Open the Audit Trail.]

> "Finally, the audit trail. Every agent step and every human decision, each
> entry carrying the hash of the one before it. From this log alone you can
> reconstruct the entire run — who flagged what, why, who approved it, and when.
> Altering history is detectable, not just discouraged."

## 6. Engineering honesty (2 min)

> "Let me be transparent about the engineering. The backend is FastAPI with SQLite
> and background jobs; the frontend is a single-page app with no build step and no
> CDN — it runs entirely offline. The LLM layer uses Groq's free tier, with
> automatic model selection. And here's a property I'll demonstrate live: if the
> API key is missing, or the network dies mid-demo, every agent degrades to a
> deterministic local engine. The demo cannot fail silently — and that fallback is
> itself a safety property."

> "Risk scoring is hybrid by design. The LLM does the semantic reasoning, but
> deterministic rule checks form a floor: if a verdict can't be traced to a rule,
> it isn't allowed. The datasets referenced are CUAD and ContractNLI — real,
> expert-labeled contract corpora — and our evaluation targets are in the report:
> extraction F1 at least 85%, risk-flag agreement at least 80%, redline quality at
> least 4.0 out of 5, negotiation convergence in six rounds or fewer, and 100% on
> the gate red-team test."

> "And the honest limits: the counterparty is a simulated agent, not a real human
> negotiator. An LLM can still be wrong — which is precisely why flags must be
> rule-grounded, why confidence is shown, and why actions are gated. ClausIQ is a
> decision-support tool that assists a human; it never replaces one."

## 7. The three gaps, closed (30 sec)

> "So the three gaps from our industry research: verification debt — closed by
> rule-grounded, click-through risk flags. Ungated autonomous action — closed by
> the policy gate and the red-team proof. And the SMB affordability gap — closed
> by running the entire agentic stack on a free-tier LLM with zero enterprise
> infrastructure."

## 8. Closing story (reuse from your report — say it fast)

> "Nimbus gets a 14-page contract from CloudBase. We upload it. The system breaks
> it into labeled clauses. It checks each one against Nimbus's playbook and flags
> the risky ones, in red, with the exact rule and reason. It drafts a surgical fix
> for each. Two agents negotiate back and forth until they converge. And at every
> point where something real would happen, the system stops and waits for a human
> — with every step logged. Minutes instead of days, no lawyer's hourly rate, and
> a full paper trail instead of a black box. Thank you — I'm happy to take
> questions."

## 9. Q&A bank — likely questions and strong answers

**"How is this different from asking ChatGPT to review a contract?"**
A chatbot gives one answer you have to trust blindly, can't negotiate, and won't
stop itself from acting. ClausIQ is a multi-agent workflow where every flag traces
to a rule and a source sentence, two agents negotiate with playbooks, and nothing
external executes without human approval — plus a complete audit log.

**"What if the model hallucinates?"**
Three defenses. Every risk flag must cite a playbook rule or it isn't allowed to
flag, so there's no free-floating guessing. Every verdict shows its confidence,
and a human can check the source clause in seconds. And a hallucination can't do
damage on its own — consequential actions physically stop at the approval gate.
The audit chain also makes any downstream decision reconstructable.

**"Why simulate negotiation? Couldn't you skip it?"**
Because nobody accepts a first redline in real life. The back-and-forth is the
expensive, manual part of contracting. The simulation shows where the negotiation
is likely to land before a human spends days on it — and it's the piece enterprise
tools like Harvey and Ironclad mostly don't offer at our price point.

**"Isn't the risk scoring just rules? Where's the actual AI?"**
It's hybrid, deliberately. The LLM handles what rules can't: recognizing novel
phrasing, ambiguous language, drafting rewrites, negotiating. The rules guarantee
verifiability — a flag is always checkable. And rules are configurable per company
in YAML, which is the point of a playbook: every company's risk tolerance differs.
Extraction, drafting, summarization and negotiation are fully LLM-driven.

**"What makes this agentic rather than a five-step script?"**
Each stage is an LLM agent with a role and its own reasoning loop: the extractor
decides clause boundaries, the classifier reasons over retrieved rules, the
negotiators plan multi-round strategies with state, and the gate is an independent
policy layer. Outputs feed forward through one shared data model, jobs are
orchestrated asynchronously, and failures degrade gracefully — hallmarks of agent
architecture, not a linear script.

**"Why Groq's free tier? Why didn't you fine-tune a model?"**
The free tier is the SMB thesis made real: the entire agent stack runs on it. The
model layer is swappable, so providers can be changed or benchmarked against each
other without touching the pipeline. We deliberately didn't fine-tune — the
governed design anchors decisions in rules, and that transparency is worth more
than a bespoke model for this use case.

**"Is this legal advice? Could it cross the unauthorized-practice line?"**
It's deliberately built as preparation, not decision-making: the system flags,
suggests and simulates, and a human always makes the binding call. That's the same
boundary our research surfaced — the first UPL lawsuit against an AI company is
about an AI directing strategy without supervision. The approval gate is exactly
the control that keeps ClausIQ in the 'tool assisting a person' category.

**"How do you know the extraction is actually good?"**
We evaluate against CUAD, the standard academic benchmark for exactly this task,
with a target of at least 85% F1. Every clause also carries its source reference,
so a human reviewer can verify extraction in seconds rather than trusting a score.

**"Why SQLite and not a vector database?"**
Scale and transparency. Playbook retrieval here is structured — rules are selected
by clause type, not embedding similarity — so a vector store would add complexity
without improving the demo's correctness. The pipeline is abstracted, so a vector
store or Postgres can be swapped in for production scale without redesigning the
agents.

**"How would this scale to a thousand contracts?"**
Jobs are already asynchronous with progress tracking. The natural production path
is a task queue, batched LLM calls with rate-limit awareness, per-organization
playbook caching, and a real document store. The agent contracts — inputs and
outputs as structured JSON — are already shaped for that.

**"What's actually new here versus Ironclad or Harvey?"**
Not any single feature — the combination, on free-tier infrastructure:
rule-grounded flags you can verify, two-agent simulated negotiation with a full
transcript, an enforced human gate with a red-team proof, and a tamper-evident
audit chain. Our market research says the next wave of defensible legal AI sits
exactly in governance and verification, not in raw model capability.

**"What would you build next?"**
A real counterparty connector — sending redlines by email or e-signature — while
keeping the gate. A fine-tuned clause classifier on CUAD. More playbooks and
jurisdictions. And a zero-data-retention mode for production privacy, since
confidential contracts passing through an API is a real, unresolved legal risk we
documented.

## 10. Practice tips

- Always say "Nimbus" and "CloudBase", never "the contract" or "the user".
- If a technical question freezes you, the safe fallback line is: "The AI never
  acts on its own — a human approves, and everything is logged. That's true at
  every stage."
- If Groq fails during the demo, say it out loud and show the fallback engine
  taking over — it's a feature, not a failure.
- Keep the demo to 12 minutes. The negotiation transcript is your centerpiece —
  don't rush it, don't skip the red-team test.
