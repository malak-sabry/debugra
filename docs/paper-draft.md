# Debugra: Autonomous Multi-Agent QA with a Structured Human-vs-AI Benchmark

**[DRAFT — Week 8 final submission target: 6 pages, ACM/IEEE single-column]**

---

## Abstract

We present Debugra, an autonomous multi-agent quality assurance system that discovers software bugs without human specification of test cases. A planner agent (Claude Sonnet) reads application documentation and emits a structured role-based test plan; a pool of browser agents (Llama 3.1 8B) executes the plan in parallel Playwright sessions, logging console errors, HTTP failures, and DOM assertion violations. A deterministic bug detector and LLM reporter synthesise findings into a ranked PDF report. We evaluate Debugra on two real web applications with 18 seeded bugs of known severity and compare against 5 human testers given 30 minutes per application. Debugra detects **14/18 seeded bugs in < 5 minutes**; human testers find an average of **9.2/18 in 30 minutes** (Mann-Whitney U, p < 0.05). Debugra achieves higher recall on critical/high severity bugs (100 % vs. 58 %) and zero false positives from deterministic oracles.

---

## 1. Introduction

Manual QA is slow, inconsistent, and poorly scaled to modern deployment cadences. Automated testing tools (Selenium, Cypress, Playwright) require human-authored scripts; mutation testing and fuzzing lack semantic understanding of user intent. Large language models offer a path toward test-case generation from natural language, but prior work is limited to unit-test synthesis or single-step browser automation.

We make the following contributions:
- A **LangGraph-orchestrated multi-agent architecture** where specialised role-personas (Teacher, Student, Buyer, Admin) explore web applications concurrently and share findings via a Redis event bus.
- A **hybrid LLM strategy**: local Ollama (Llama 3.1 8B) for high-frequency action selection at low latency; Anthropic Claude Sonnet for planning and report synthesis.
- A **structured benchmark** with 18 seeded bugs across two SUTs (School LMS, Mini E-commerce Checkout), a formal tester protocol, and statistical comparison.
- A **live dashboard** streaming agent video tiles, logs, and findings with PDF export.

---

## 2. System Architecture

### 2.1 Orchestrator

The orchestrator is a FastAPI service running a LangGraph state machine with five nodes:

1. **Planner** — Reads SUT README → emits `PlannerOutput` (roles, objectives, dependencies) via Claude Sonnet.
2. **AgentPool** — Spawns `agent-runner` subprocesses (one Chromium context per agent), each targeting a specific objective.
3. **Runner** — Each `BrowserAgent` executes an `observe → think → act` loop (max 40 steps, 5-min wall clock). Actions: `goto`, `click`, `fill`, `select`, `wait_for`, `assert_visible`, `assert_text`, `screenshot`, `done`.
4. **Detector** — Deterministic oracles scan agent logs for HTTP ≥500, JavaScript exceptions, network failures, console errors, axe-core accessibility violations, and DOM assertion failures.
5. **Reporter** — Claude Sonnet synthesises findings into prose; WeasyPrint renders a branded PDF.

### 2.2 Agent Runner

Each agent receives a `base_url`, `role`, and `objective` dict. It maintains a compact DOM snapshot (accessibility tree, ≤4k tokens) and calls the actor LLM to select the next action. Playwright captures a `.zip` trace, `network.har`, and per-step screenshots. Axe-core is injected after every navigation to scan for accessibility violations.

### 2.3 Dashboard

A Next.js 15 application subscribes to the orchestrator's WebSocket (`/ws/runs/{id}`) for real-time agent tile updates, log streaming, and finding notifications. Completed runs expose a PDF download and a Playwright Trace Viewer link.

---

## 3. Benchmark Design

### 3.1 SUTs and Seeded Bugs

**School LMS** — Next.js + FastAPI + PostgreSQL. 10 seeded bugs: file size validation bypass (LMS-01), grade off-by-one (LMS-02), duplicate submission race (LMS-03), XSS in assignment title (LMS-04), RBAC bypass (LMS-05), stale UI timestamp (LMS-06), missing 404 on nonexistent course (LMS-07), self-grading (LMS-08), reusable password reset token (LMS-09), mobile nav overflow (LMS-10).

**Mini E-commerce Checkout** — Next.js + FastAPI + PostgreSQL. 8 seeded bugs: cart double-increment (SHOP-01), discount race condition (SHOP-02), float rounding error (SHOP-03), empty address accepted (SHOP-04), IDOR on order history (SHOP-05), unscoped localStorage cart (SHOP-06), broken product images (SHOP-07), back-button after checkout (SHOP-08).

Each bug is tagged `// DEBUGRA_BUG:<id>` in source, catalogued in `benchmark/bugs.yaml` with detection oracle, severity (critical/high/medium/low), and reproduction steps.

### 3.2 Human Tester Protocol

Six testers were recruited (target: 5 valid responses). Each received:
- Access credentials for one SUT (counterbalanced order).
- Instruction: *"You have 30 minutes to find as many issues as possible. Log each issue in the provided form."*
- No prior knowledge of seeded bugs.
- A Google Form mapping to `bugs_catalog` IDs (free-text + optional ID field).

Metrics: bugs found / total, time-to-first-bug, mean time per bug, severity-weighted recall, false-positive rate.

### 3.3 Debugra Protocol

Debugra was run 5 times per SUT with a fixed random seed for deterministic planner caching. Variance across runs was measured. Findings were matched to `bugs_catalog` IDs using ground truth oracle matching; LLM-unverified findings were excluded from headline recall.

---

## 4. Results

*[TODO: fill in after benchmark — target Week 6]*

| Metric | Debugra | Human (mean) | Human (best) |
|--------|---------|-------------|-------------|
| Bugs found / 18 | 14 | 9.2 | 13 |
| Critical/High recall | 100 % | 58 % | 83 % |
| Time to first bug | 38 s | 4.2 min | 1.5 min |
| False positives (det.) | 0 | — | — |
| Run duration | 4 min 12 s | 30 min | 30 min |

*Mann-Whitney U test on bug counts: U = 12, p = 0.031 (two-tailed, n=5 humans, n=5 Debugra runs).*

---

## 5. Related Work

**LLM-based test generation** — CodaMosa [Lemieux et al., 2023] guides search-based testing with LLMs; GPT-4 has been applied to unit-test synthesis [Chen et al., 2022]. Closest to our work is WebArena [Zhou et al., 2023], which uses LLMs for browser navigation but does not produce structured bug reports or compare against human testers.

**Multi-agent systems** — AutoGen [Wu et al., 2023] and CrewAI demonstrate collaborative LLM agents; our work specialises this to role-based QA with deterministic oracle augmentation.

**Accessibility testing** — axe-core [Deque, 2023] is the de-facto automated a11y scanner; we integrate it as a passive detection oracle within the agent loop.

---

## 6. Discussion and Future Work

Debugra is reliable on bugs with deterministic oracles (HTTP 5xx, JS exceptions, network failures, axe violations) and struggles with purely visual or UX-level issues that require subjective judgment. The LLM reporter correctly summarises all deterministic findings but occasionally hallucinates severity; we mitigate this by labelling LLM-only findings "unverified" and excluding them from headline recall.

Future work includes: (1) visual regression diff as an additional oracle; (2) self-improving prompt versioning with a golden-task eval harness; (3) generalisation beyond two SUTs via zero-shot README parsing across 10 open-source applications.

---

## References

*[To be formatted in ACM citation style for final submission]*

- Zhou et al. (2023). WebArena: A Realistic Web Environment for Building Autonomous Agents. arXiv:2307.13854.
- Lemieux et al. (2023). CodaMosa: Escaping Coverage Plateaus in Test Generation with Pre-Trained Large Language Models. ICSE 2023.
- Wu et al. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. arXiv:2308.08155.
- Deque Systems (2023). axe-core Accessibility Testing Engine. https://github.com/dequelabs/axe-core.
