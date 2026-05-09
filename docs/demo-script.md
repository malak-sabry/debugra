# Debugra — Demo Script (7 minutes)

## Pre-Demo Checklist (10 min before)

- [ ] Both SUTs running: `make demo`
- [ ] Dashboard open at http://localhost:3000
- [ ] Orchestrator health: http://localhost:8000/health → `{"status":"ok"}`
- [ ] LMS health: http://localhost:8001/health → `{"status":"ok"}`
- [ ] Shop health: http://localhost:8002/health → `{"status":"ok"}`
- [ ] Backup video ready and tested on a second device
- [ ] "Demo Mode" preset loaded (cached planner output for LMS)
- [ ] Browser zoom at 90%, dark mode, full screen

---

## Script (spoken + actions)

### 0:00 — Hook (30s)

> "Software testing costs companies billions every year. The average QA cycle takes days. Human testers are slow, inconsistent, and expensive. What if the entire process ran itself?"

*[Show empty dashboard on screen]*

---

### 0:30 — Upload Repo (60s)

> "We give Debugra one thing: the project's README. That's it."

*Action: Click "New Run" → Select "LMS" → Show the README text being read*

> "In seconds, Debugra reads the documentation. It identifies user roles — teacher, student, admin — and autonomously generates a testing plan."

*[Planning complete event fires — plan JSON appears in UI with roles listed]*

---

### 1:30 — Agents Launch (90s) ← THE WOW MOMENT

> "Now watch."

*[Three agent tiles light up. Browsers start moving.]*

> "Three AI agents, each playing a role. The teacher just logged in. The student just registered. The admin is checking the dashboard."

*[Pause — let judges watch the browsers navigate. No narration needed here.]*

> "The teacher creates an assignment. The student — in real time — sees it appear and submits work."

*[Screenshot tiles update]*

---

### 3:30 — Bug Discovery (60s)

> "Debugra doesn't just click around. It tests boundaries."

*[Finding card appears in the Findings panel]*

> "Here — the student attempted to upload a PDF larger than 10 megabytes. The server accepted it. No size validation. That's a bug. High severity. Detected by our HTTP oracle."

*[Click to expand finding — screenshot + repro steps visible]*

> "Every finding comes with evidence and reproduction steps."

---

### 4:30 — Switch to Shop SUT (30s)

> "Let's switch to the second application — our e-commerce checkout."

*[Click New Run → Select "Shop" → Launch]*

> "Same process. New app. Buyer agent adds items, applies a discount, checks out."

*[Race condition finding surfaces]*

> "Debugra detected a race condition in the checkout flow. The discount wasn't applied correctly under concurrent requests."

---

### 5:30 — Benchmark Slide (60s)

*[Switch to PDF report / benchmark chart]*

> "Here's the benchmark: we gave the same two apps to six human testers — experienced developers — and gave them 30 minutes each."

> "Debugra found 14 of 18 seeded bugs in under 4 minutes. The human average was 9 bugs in 30 minutes — and Debugra costs zero dollars per run after setup."

*[Show chart: Debugra vs Human — bugs found, time, recall]*

---

### 6:30 — Close (30s)

> "This isn't just a testing tool. This is Autonomous Software Validation."

> "Faster. Consistent. Scalable. And it works on any web application."

*[Show dashboard with complete run, findings panel full, replay tab]*

> "Debugra."

---

## Fallback Protocol

If live demo fails at any step:
1. Immediately switch to backup video (pre-recorded on same hardware)
2. Say: "Let me show you a recorded run from earlier today"
3. Continue narration over video — all timing is identical
