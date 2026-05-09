# Debugra — System Architecture (v1)

## Overview

```
Dashboard (Next.js 15)
    │  WebSocket (RunEvent stream)
    │  REST (runs, findings, agents, artifacts)
    ▼
Orchestrator (FastAPI + LangGraph)         ← Central brain
    │  subprocess + stdout NDJSON
    ▼
Agent Runner (Playwright, Python)          ← Browser workers
    │  Playwright CDP
    ▼
SUT Containers (lms/shop via Docker)
```

## Data Flow (single run)

1. User clicks "New Run" → POST /api/runs → DB record created, background task queued.
2. LangGraph graph starts:  
   a. **plan** node → Claude reads README → `PlannerOutput` JSON  
   b. **spawn_agents** node → one subprocess per role (dependency-ordered)  
   c. **detect** node → aggregate logs + assertion failures → `Finding[]`  
   d. **report** node → Claude synthesizes executive summary  
3. Each agent subprocess streams NDJSON events to stdout → orchestrator reads and re-publishes to Redis pub/sub + in-memory WS subscribers.
4. Dashboard WS client receives events → updates agent tiles, logs panel, findings panel in real-time.

## Key Design Decisions

### LangGraph over raw asyncio
Explicit state graph makes the run lifecycle replayable, debuggable, and serializable. Each node is a pure async function with typed `RunState`.

### Subprocess-based agent runner
Agent processes are isolated from the orchestrator process:
- Playwright browser crash can't kill orchestrator.
- Per-agent resource limits enforced at OS level.
- Easy to scale horizontally (remote workers in Phase 2).

### Hybrid LLM routing
| Task | Model | Reason |
|------|-------|--------|
| Planning (README → plan) | Claude Sonnet 4.5 | Best instruction following + JSON output |
| Action selection (per step) | Ollama Llama 3.1 8B | 40 steps/agent × 3 agents = ~120 LLM calls; local = free + fast |
| Report synthesis | Claude Sonnet 4.5 | Needs prose quality for judge takeaway |

### Oracle-first finding verification
Every "headline" finding must be backed by a deterministic oracle (HTTP code, console log pattern, DOM assertion failure). LLM-only findings are marked `oracle_type=llm_unverified` and excluded from benchmark metrics. This makes the system scientifically defensible.

### In-memory WS fallback
`event_bus.py` maintains an in-memory `dict[run_id → list[WebSocket]]` as a fallback when Redis is unavailable (e.g., dev mode). Redis pub/sub is used in production for multi-process fan-out.

## Component Interfaces

### Orchestrator → Agent Runner (stdin/stdout)
Agent runner receives configuration as CLI args:
```
python -m runner.main --run-id X --agent-id Y --sut lms --base-url http://... --objective '{"role":"teacher",...}' --artifact-dir ./runs/X/Y
```
Agent emits NDJSON events to stdout:
```json
{"type": "agent_step", "payload": {...}, "ts": "..."}
{"type": "agent_screenshot", "payload": {"path": "...", "role": "..."}, "ts": "..."}
{"type": "log_line", "payload": {"line": "...", "source": "console"}, "ts": "..."}
{"type": "agent_complete", "payload": {"step_count": 23}, "ts": "..."}
```

### WebSocket Event Types
See `packages/schemas/src/index.ts → RunEventType`.
