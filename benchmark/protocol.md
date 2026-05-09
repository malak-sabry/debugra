# Debugra Benchmark — Human Tester Protocol (v1)

## Study Purpose

Compare bug detection performance between **Debugra (autonomous AI)** and **human testers** across two web applications.

## Participant Requirements

- Has basic web development or QA experience
- Comfortable using a browser
- Has NOT seen the application source code
- Available for 60–90 minutes

## What You Will Do

You will manually test two web applications and try to find as many bugs as you can.

## Instructions

1. You will be given access credentials and a URL for each application.
2. For **each application**, spend **30 minutes** trying to find bugs.
3. Log each bug you find using the [Bug Report Form](#bug-report-form-link).
4. Do NOT look at the source code.
5. Do NOT use automated tools.

## Application 1: School LMS

**URL:** http://localhost:3001  
**Time:** 30 minutes  
**Test accounts provided:** (see facilitator)

Try to:
- Register and log in as different roles (teacher, student, admin)
- Perform typical user flows (create course, submit assignment, grade work, view dashboard)
- Look for things that behave unexpectedly

## Application 2: E-commerce Shop

**URL:** http://localhost:3002  
**Time:** 30 minutes  
**Test accounts provided:** (see facilitator)

Try to:
- Browse products
- Add items to cart
- Try checkout with different inputs
- Try edge cases (empty fields, boundary values, rapid clicks)

## Bug Report Form Fields

For each bug found:
1. **Application** (LMS / Shop)
2. **Bug title** (short description)
3. **Steps to reproduce** (numbered list)
4. **Expected behavior**
5. **Actual behavior**
6. **Severity estimate** (Critical / High / Medium / Low)
7. **Time found** (minutes elapsed since start)

## Scoring

Each reported bug will be matched against the ground-truth catalog (`bugs.yaml`).

| Metric | Description |
|--------|-------------|
| `bugs_found` | # of ground-truth bugs correctly identified |
| `recall` | bugs_found / total_seeded_bugs |
| `false_positive_rate` | reported bugs not in catalog / total reported |
| `time_to_first_bug` | minutes until first valid bug reported |
| `mean_time_per_bug` | total_time / bugs_found |

## Facilitator Notes

- Assign each tester a random 4-digit ID (e.g., T001).
- Give fresh accounts for each tester (pre-create via seed script).
- Record start/end time precisely.
- Do not hint or guide.
- After session: map each report to `bugs.yaml` ID or mark as false positive.
- Enter results in `benchmark/results/` as `results_T001.csv`.

## Ethical Note

This study is for academic/competition purposes only. Data is anonymized. Participants may withdraw at any time.
