# Debugra — Competition-Winning Prototype Plan

## Vision

> An autonomous AI QA system that understands software projects, launches required environments, simulates realistic users, explores applications like a human tester, detects issues automatically, and generates intelligent QA reports.

This is not “another testing tool.”

This is:

# **AI Autonomous Software Validation**

That positioning matters a LOT.

---

# 1. Competition Strategy (Very Important)

Your goal is NOT:

```text
build a perfect testing platform
```

Your goal IS:

```text
demonstrate a believable future of autonomous QA
```

That changes everything.

Judges care about:

* innovation
* technical complexity
* research depth
* demonstration quality
* scalability potential
* real-world impact

NOT production perfection.

---

# 2. What Will Make You Win

Most teams build:

* chatbots
* AI wrappers
* dashboards

You need:

# **An AI system that ACTS autonomously**

That instantly separates you.

The demo should feel like:

```text
“Wait… the AI is actually using the app?”
```

That emotional reaction matters.

---

# 3. The Winning Prototype Scope

DO NOT attempt:

* full Android support
* all frameworks
* universal compatibility
* advanced DevOps

You will drown.

Instead:

# Build a CONTROLLED but EXTREMELY POLISHED prototype.

---

# 4. The Core Demo Scenario

This is the secret.

Create ONE highly polished ecosystem.

Example:

## Demo System

A mini school platform:

* web app
* teacher
* student
* admin

Flows:

* register
* login
* assignment creation
* submissions
* grading
* dashboard

Then Debugra autonomously:

* reads docs
* understands roles
* launches testing agents
* performs actions
* finds intentional bugs
* generates reports

This gives:

* multi-role testing
* concurrent testing
* realistic workflows
* AI reasoning

WITHOUT needing universal support.

This is how competition prototypes are won.

---

# 5. Architecture Plan

# Phase 1 — MVP Core (2–4 weeks)

## Goal

Make judges SEE autonomous behavior.

---

## Components

### A. Orchestrator

Central brain.

Responsibilities:

* assign tasks
* manage agents
* track sessions
* aggregate findings

Tech:

```text
Python FastAPI
```

---

### B. LLM Planning Engine

Responsibilities:

* parse README
* understand roles
* generate testing flows

Input:

```text
README.md
```

Output:

```json
{
  "roles": ["teacher", "student"],
  "flows": [
    "teacher creates assignment",
    "student submits assignment"
  ]
}
```

Use:

* OpenAI API initially
* Claude optionally

---

### C. Browser Agent System

This is the WOW factor.

Use:

# Playwright

NOT Selenium.

Playwright is:

* modern
* stable
* faster
* AI-agent friendly

Agents:

```text
TeacherAgent
StudentAgent
AdminAgent
```

Each has:

* session
* memory
* objectives

---

### D. UI Understanding Layer

Initially:
DO NOT build computer vision.

Use:

```text
DOM
accessibility tree
labels
```

Much easier.

The AI can still appear intelligent.

---

### E. Log Monitor

Collect:

* browser console errors
* network failures
* backend logs

Simple regex detection:

```text
ERROR
Exception
Unhandled
500
```

Then LLM summarizes findings.

---

### F. QA Report Generator

Output:

* screenshots
* issue summaries
* severity
* reproduction steps

Export:

```text
PDF + beautiful dashboard
```

This matters MASSIVELY in competitions.

Polish wins.

---

# 6. Phase 2 — “Research-Level Features”

Only AFTER MVP works.

---

## Feature A — Multi-Agent Coordination

This is your strongest differentiator.

Example:

```text
Teacher creates assignment
↓
Student sees it instantly
↓
Admin verifies analytics
```

Real concurrent testing.

Most tools do NOT do this well.

---

## Feature B — Environment Bootstrapping

Input:

```text
GitHub repo
README
```

AI:

* detects stack
* generates docker-compose
* launches services

Initially fake some parts if needed.

Competition demos can be semi-controlled.

That’s normal.

---

## Feature C — Intentional Bug Discovery

VERY IMPORTANT.

Create intentional bugs:

* broken responsive UI
* race conditions
* permission issues
* API failure

Then Debugra “discovers” them.

This makes the demo unforgettable.

---

# 7. Recommended Tech Stack

## Backend

* FastAPI
* Python

---

## Agent System

* LangGraph OR CrewAI
* simple custom orchestration

Avoid overengineering initially.

---

## Browser Automation

* Playwright

---

## Frontend Dashboard

* Next.js
* Tailwind
* shadcn/ui

Needs to look WORLD CLASS.

---

## Storage

* PostgreSQL
* Redis optionally

---

## AI APIs

Initially:

* GPT-4.1 / GPT-5
* Claude

---

# 8. What NOT To Build

DO NOT:

* support every framework
* support real APK testing first
* create your own LLM
* create computer vision from scratch
* build advanced CI/CD

Those are traps.

---

# 9. The Competition Presentation Strategy

This matters more than code sometimes.

---

## Your Narrative

NOT:

```text
AI testing app
```

BUT:

# “The Future of Autonomous Software Validation”

You are:

* reducing QA costs
* accelerating deployment
* increasing software reliability

---

# 10. The Demo Flow

This should feel cinematic.

---

## Live Demo

### Step 1

Upload repo:

```text
School LMS Demo
```

---

### Step 2

Debugra reads:

```text
README detected:
Roles:
- teacher
- student
- admin
```

---

### Step 3

Agents launch live.

Judges WATCH:

* browsers moving
* forms filled
* users interacting

This is GOLD.

---

### Step 4

Bug discovered:

```text
Student cannot upload PDF >10MB
```

---

### Step 5

Beautiful report generated.

Boom.

---

# 11. The Secret Weapon

Here’s what will ACTUALLY make this project elite:

# Build a benchmark.

Meaning:

You intentionally compare:

```text
human testers
vs
Debugra
```

Metrics:

* time
* bugs found
* workflow coverage
* repeated execution speed

THIS turns it from:

```text
cool tool
```

into:

```text
scientific research project
```

THAT is what wins ISEF-level judging.

---

# 12. The Teammate Reality

Since the teammate will mostly vibe-code initially:

## Your role should be:

* architecture
* system design
* presentation strategy
* UX direction
* AI workflow planning
* competition framing

Their role:

* implementation speed
* prototypes
* integrations

That division works VERY well.

---

# 13. Final Advice

Your biggest risk is:

```text
trying to build too much
```

The winning version is:

```text
small scope
+
extremely polished
+
highly autonomous-looking
+
excellent presentation
```

That combination beats giant unfinished systems every time.
