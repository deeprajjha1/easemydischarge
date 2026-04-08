---
title: easemydischarge-pm-env
emoji: 🏥
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
---

# easemydischarge-pm-env

**OpenEnv environment** simulating a **Product Manager** at easemydischarge, a healthcare startup that uses a **swarm of AI agents** to automate hospital patient discharge.

## Motivation

Hospital discharge averages **8.5 hours** per patient. The bottlenecks:

1. **Insurance claim pre-filling** — Manual data entry, template mismatches, 12% validation fail rate
2. **NOC coordination** — Five departments (Nursing, Pharmacy, Lab, Billing, Admin) must clear the patient, with circular dependencies causing deadlocks
3. **Scaling** — Works for 1 hospital but breaks at multi-hospital scale

An AI agent acting as PM must investigate the system, identify root causes, propose improvements, and submit a roadmap.

---

## Tasks

| Task | Difficulty | Max Steps | Objective |
|------|-----------|-----------|-----------|
| `easy` | Easy | 10 | Optimize insurance claim pre-filling pipeline |
| `medium` | Medium | 12 | Resolve NOC coordination deadlocks |
| `hard` | Hard | 15 | Design multi-hospital scaling architecture |

Each task has **6-10 concepts** the agent should discover and address.

---

## Action Space

| Action | Parameters | Description |
|--------|-----------|-------------|
| `query_swarm` | — | Get status of all swarm agents |
| `query_department` | `department` | Query a department (nursing/pharmacy/lab/billing/admin) |
| `analyze` | `component` | Analyze a component (claim_pipeline/noc_pipeline/discharge_flow) |
| `propose_feature` | `feature_description` | Propose a feature improvement |
| `submit_roadmap` | `roadmap` | Submit final roadmap (ends episode) |

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `task` | string | Current task name |
| `step` / `max_steps` | int | Current and maximum steps |
| `message` | string | Environment feedback |
| `data` | dict | Response data from last action |
| `concepts_covered` | list | Concepts addressed so far |
| `investigation_summary` | dict | What has been queried/analyzed |
| `available_actions` | list | Valid action types |

## Reward Design

- **First query** of swarm/department/component: 0.25-0.30
- **Re-query**: 0.05 (diminishing returns)
- **Good proposal** (new concepts): up to 0.70
- **Proposing without investigating first**: 50% penalty
- **Exact repeat**: 75% penalty
- **Final score**: coverage (40%) + investigation (25%) + strategy (20%) + completeness (15%)

---

## Setup

```bash
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

```bash
export HF_TOKEN="your-token"
TASK=easy python3 inference.py
TASK=medium python3 inference.py
TASK=hard python3 inference.py
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | No | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | No | `Qwen/Qwen2.5-72B-Instruct` | Model identifier |
| `HF_TOKEN` | Yes | — | API key for LLM calls |
| `ENV_BASE_URL` | No | `http://localhost:8000` | Environment server URL |
| `TASK` | No | `easy` | Task to run |

## Baseline Scores

| Task | Score |
|------|-------|
| easy | ~0.85-1.00 |
| medium | ~0.60-0.80 |
| hard | ~0.45-0.60 |
