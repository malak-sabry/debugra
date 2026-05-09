# Debugra — 8-Week Competition Plan

A locked-scope, 8-week, 2-developer plan to ship Debugra as an autonomous multi-agent QA system with a structured human-vs-AI benchmark, polished live dashboard, PDF reports, and session replay — judged demo-ready by Week 8.

---

## 1. Locked Decisions

| Area | Decision |
|------|----------|
| Timeline | **8 weeks**, 2 devs |
| SUTs | **Two**: (A) School LMS, (B) Mini E-commerce Checkout |
| LLM strategy | **Hybrid**: local Ollama (Llama 3.1 8B) for high-frequency action selection; **Anthropic Claude Sonnet 4.5** (primary) + OpenAI GPT-4.1 (fallback) for planning + report synthesis |
| Orchestration | **LangGraph** (deterministic state graph, replayable, best fit for multi-agent demo) |
| Bootstrapping | **Pre-baked docker-compose** per SUT (honest, reliable on stage) |
| Benchmark | **Structured study**: 15–20 seeded bugs across both SUTs, 5+ human testers, formal protocol |
| Output | **Live dashboard + PDF report + Playwright trace replay** |
| Repo layout | Monorepo, pnpm + uv workspaces |

Out of scope (do not build): mobile/APK, universal framework support, custom LLM, custom CV, CI/CD product, auth/billing.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js Dashboard (live tiles, logs, findings, replay)     │
└──────────────▲────────────────────────────────▲─────────────┘
               │ WebSocket (run events)         │ REST (history)
┌──────────────┴────────────────────────────────┴─────────────┐
│  FastAPI Orchestrator  ──  LangGraph state machine          │
│   ├─ Planner Node      (Claude: README → roles + flows)     │
│   ├─ Agent Pool        (Teacher / Student / Admin / Buyer)  │
│   ├─ Action Selector   (Ollama: DOM snapshot → next action) │
│   ├─ Log Monitor       (browser console + network + server) │
│   ├─ Bug Detector      (heuristics + LLM verifier)          │
│   └─ Reporter          (Claude: findings → PDF)             │
└──────────────▲────────────────────────────────▲─────────────┘
               │ Playwright CDP                 │ Docker SDK
┌──────────────┴────────────┐    ┌──────────────┴─────────────┐
│  Browser Agent Workers    │    │  SUT Containers            │
│  (1 Chromium ctx / agent, │    │  - lms-web, lms-api, db    │
│   trace + video on)       │    │  - shop-web, shop-api, db  │
└───────────────────────────┘    └────────────────────────────┘
                Postgres (runs, findings, traces)  +  Redis (pub/sub)
```

### Component contracts

- **Planner → Agents**: JSON `{roles[], objectives[], success_criteria[], dependencies[]}`
- **Agent step loop**: `observe(DOM+a11y tree) → think(LLM) → act(Playwright) → log` with hard step cap (40) and wall clock (5 min)
- **Bug Detector inputs**: console errors, HTTP ≥500, unhandled rejections, accessibility violations (axe-core), assertion failures, visual regression diffs
- **Trace artifact**: Playwright `.zip` trace + screenshots + HAR per agent session, stored in `runs/<run_id>/<agent_id>/`

---

## 3. Repository Layout

```
debugra/
  apps/
    dashboard/              Next.js 15 + Tailwind + shadcn/ui
    orchestrator/           FastAPI + LangGraph (Python 3.12, uv)
    agent-runner/           Playwright worker (Python, async)
  packages/
    schemas/                Pydantic + zod-mirrored types (run, finding, action)
    prompts/                Versioned prompt files (planner, actor, reporter)
  suts/
    lms/                    Next.js + FastAPI + Postgres, seeded bugs flagged in code
    shop/                   Next.js + FastAPI + Postgres, seeded bugs flagged
  benchmark/
    protocol.md             Tester instructions, consent form, scoring rubric
    bugs.yaml               Ground-truth bug catalog (id, severity, repro, location)
    results/                CSV + notebooks
  infra/
    docker-compose.lms.yml
    docker-compose.shop.yml
    docker-compose.debugra.yml
  docs/
    architecture.md
    demo-script.md
    paper-draft.md
```

---

## 4. Data Model (Postgres)

- `runs` (id, sut, started_at, ended_at, status, config_json)
- `agents` (id, run_id, role, model, status, trace_path, video_path)
- `actions` (id, agent_id, step, observation_hash, thought, tool, args, result, ts)
- `findings` (id, run_id, agent_id, severity, title, repro_steps_json, evidence_paths, ground_truth_bug_id NULL, llm_summary)
- `bugs_catalog` (id, sut, title, severity, location, repro, seeded_in_commit) — ground truth

---

## 5. Seeded Bug Catalog (target: 18 total)

LMS (10): broken file size validation (>10MB PDF), teacher can grade own student account (RBAC), grade calculation off-by-one, race on concurrent submission, XSS in assignment title, stale dashboard cache, mobile nav overflow at 375px, missing aria-labels on grade table, 500 on empty submission list, password reset token reuse.

Shop (8): cart total ignores discount on race, stock decrements twice on double-click, checkout proceeds with empty address, currency rounding, broken back-button after payment, GET on /checkout exposes other user's session via query param, cart persists across logout, 404 image breaks PDP layout.

Each bug: tagged in source with `// DEBUGRA_BUG:<id>`, listed in `benchmark/bugs.yaml` with severity (critical/high/med/low) and detection oracle (console regex / HTTP code / DOM assertion / visual diff).

---

## 6. 8-Week Schedule

Two devs: **D1 = Systems/Backend/Agents**, **D2 = Frontend/SUTs/Demo**. Daily standup, weekly Friday demo internal.

### Week 1 — Foundations
- D1: monorepo, uv + pnpm workspaces, Postgres+Redis docker, FastAPI skeleton, schemas package, LangGraph hello-world graph, Playwright headed worker that records trace.
- D2: Next.js dashboard skeleton (run list, run detail with empty tiles), shadcn theme, WebSocket client, scaffold both SUTs (auth + 1 happy-path flow each).
- Exit criteria: orchestrator can spawn a Playwright worker on a static page, dashboard shows live screenshot stream.

### Week 2 — Single-agent loop
- D1: observe→think→act loop with Ollama action selector, action toolset (`click`, `fill`, `select`, `goto`, `wait_for`, `assert_visible`), DOM+a11y snapshotter (compact serialization, ≤4k tokens).
- D2: finish LMS happy paths (register, login, create assignment, submit, grade); seed bugs LMS-1..LMS-5.
- Exit: 1 StudentAgent autonomously logs in and submits an assignment on LMS.

### Week 3 — Planner + multi-agent
- D1: Planner node (Claude) consuming README → roles + flows JSON; agent pool with role memory; cross-agent rendezvous via Redis pub/sub (Teacher posts assignment → Student observes).
- D2: Shop SUT happy paths + seed Shop-1..Shop-4; dashboard agent-tile grid with live video.
- Exit: Teacher + Student concurrent run on LMS demonstrates the canonical "create→submit" cinematic.

### Week 4 — Bug detection + reporting v1
- D1: Log Monitor (console, network, server logs aggregated to Redis), Bug Detector (rules + LLM verifier producing `findings`), evidence capture (screenshot + DOM + trace pointer).
- D2: dashboard Findings panel with severity badges, evidence carousel; PDF report v1 (WeasyPrint, branded template).
- Exit: full LMS run produces a PDF listing ≥3 real findings with screenshots.

### Week 5 — Second SUT + remaining bugs + replay
- D1: generalize agent prompts/tools to Shop; Admin/Buyer roles; finalize seeding LMS-6..10, Shop-5..8.
- D2: Playwright trace viewer embedded in dashboard ("Replay" tab, opens `trace.zip` in iframe via `npx playwright show-trace --port`); run history page.
- Exit: Debugra runs end-to-end on both SUTs from a single "Start Run" click.

### Week 6 — Benchmark study
- Protocol freeze (D1+D2 jointly): each tester gets 30 min/SUT, no prior knowledge, instructed to "find as many issues as possible," logs bugs in Google Form mapped to `bugs_catalog`.
- Recruit 6 testers (target 5 valid). Run Debugra 5x per SUT for variance.
- Metrics: bugs_found/total, time_to_first_bug, mean_time_per_bug, severity-weighted recall, false-positive rate.
- Deliverable: `benchmark/results/report.ipynb` with plots + significance test (Mann-Whitney U on bug counts).

### Week 7 — Polish
- D1: stability hardening (retry/backoff, step caps, deterministic seeds for demo), prompt versioning + eval harness (10 golden tasks).
- D2: dashboard polish (motion, empty states, dark mode, "Demo Mode" preset), demo script rehearsal, fallback recordings for every step.
- Exit: 3 successful end-to-end dry runs without intervention.

### Week 8 — Demo + writeup
- Day 1–2: paper-style writeup (`docs/paper-draft.md`, 6 pages: problem, system, benchmark, results, related work, future).
- Day 3–4: demo dress rehearsals (timed 7-min pitch + 3-min Q&A), record backup video.
- Day 5: submit / present.

---

## 7. Demo Script (7 minutes)

1. **0:00** Hook: "QA is the bottleneck of modern software. What if it ran itself?"
2. **0:30** Upload LMS repo → Debugra parses README, prints detected roles live.
3. **1:30** Click Run. 3 browser tiles light up. Teacher posts assignment → Student tile reacts in real time. Judges visibly react.
4. **3:30** Bug surfaces in Findings panel: "Student cannot upload PDF >10MB" with screenshot + repro.
5. **4:30** Switch to Shop SUT, single click, race condition surfaces.
6. **5:30** Open PDF report → benchmark slide: "Debugra found 14/18 seeded bugs in 4 min; 5 humans averaged 9/18 in 30 min."
7. **6:30** Close: "Autonomous Software Validation. Debugra."

Backup: pre-recorded video of identical run, played if live fails.

---

## 8. Risk Register

| Risk | Mitigation |
|------|------------|
| Live LLM latency kills demo pacing | Local Ollama for action loop; cache planner output for known SUTs; "Demo Mode" uses recorded planner response |
| Playwright flakes on stage | Pinned browser, fixed viewport, deterministic seed, 3 dry runs/day in week 7, video fallback |
| Benchmark testers unreliable | Recruit 6 to land 5; over-instrument the form; pre-test protocol on 1 pilot tester in week 5 |
| LLM hallucinates findings | Every finding must cite a deterministic oracle (HTTP code, console line, DOM assertion); LLM-only findings tagged "unverified" and excluded from headline metric |
| Scope creep | This document is the contract. Any new feature requires removing one. |

---

## 9. Definition of Done (Week 8)

- [ ] One-command `make demo` brings up Debugra + both SUTs locally
- [ ] Two SUTs with 18 seeded, catalogued bugs
- [ ] Multi-agent run on LMS visibly coordinates Teacher↔Student
- [ ] Dashboard streams live tiles, logs, findings; replay tab works on any past run
- [ ] Branded PDF report auto-generated per run
- [ ] Benchmark notebook with ≥5 human testers, statistical comparison, plots
- [ ] 6-page writeup + 7-min demo + backup video
- [ ] 3 consecutive successful dry runs recorded

---

## 10. Open Items (none blocking)

- Hosting for live demo: local laptop is canonical; cloud (Fly.io) only as backup if venue forbids local servers.
- Tester compensation: $20 gift card each (budget $120) — confirm before Week 6.
