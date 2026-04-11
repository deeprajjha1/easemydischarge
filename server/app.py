"""FastAPI server for easemydischarge-pm-env OpenEnv hackathon environment."""
from fastapi import FastAPI, Request
from typing import Dict, List, Any, Optional
import uvicorn
from models import EasemydischargeAction
from server.environment import EasemydischargePMEnv

app = FastAPI(title="easemydischarge-pm-env", version="1.0.0")
env = EasemydischargePMEnv()


# ── Task definitions ──────────────────────────────────────────────────

TASKS = [
    {
        "id": "easy",
        "name": "Claim Pipeline Optimization",
        "difficulty": "easy",
        "max_steps": 10,
        "description": (
            "Optimize the insurance claim pre-filling pipeline. Investigate "
            "the swarm agents and propose improvements to reduce errors and "
            "speed up claim processing."
        ),
        "grader": "grader:grade_easy",
        "score_range": [0.0, 1.0],
    },
    {
        "id": "medium",
        "name": "NOC Coordination Resolution",
        "difficulty": "medium",
        "max_steps": 12,
        "description": (
            "Resolve NOC coordination deadlocks between hospital departments. "
            "Investigate inter-department conflicts, propose timeout and escalation "
            "mechanisms, and improve parallel coordination."
        ),
        "grader": "grader:grade_medium",
        "score_range": [0.0, 1.0],
    },
    {
        "id": "hard",
        "name": "Multi-Hospital Scaling Architecture",
        "difficulty": "hard",
        "max_steps": 15,
        "description": (
            "Design a scaling architecture to expand from 1 hospital to 50. "
            "Address multi-tenancy, compliance, interoperability, monitoring, "
            "and phased rollout."
        ),
        "grader": "grader:grade_hard",
        "score_range": [0.0, 1.0],
    },
]


# ── In-process grader (no HTTP, no dependencies) ──────────────────────

def _run_grader(task_id: str) -> float:
    """Import and call the grader, passing the current environment state."""
    import sys
    import os
    import importlib
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, "/app")
    mod = importlib.import_module("grader")
    fn_map = {
        "easy": mod.grade_easy,
        "medium": mod.grade_medium,
        "hard": mod.grade_hard,
    }
    fn = fn_map.get(task_id, mod.grade_easy)
    env_state = env.grading_state()
    if env_state.get("actions_taken") and env_state.get("task") == task_id:
        return fn(env_state)
    return fn()


def _all_scores() -> Dict[str, float]:
    return {
        "easy": _run_grader("easy"),
        "medium": _run_grader("medium"),
        "hard": _run_grader("hard"),
    }


# ── Core environment routes ───────────────────────────────────────────

@app.get("/health")
@app.get("/")
async def health():
    return {"status": "ok", "env": "easemydischarge-pm-env", "version": "1.0.0"}


@app.post("/reset")
async def reset(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    task = payload.get("task", "easy") if isinstance(payload, dict) else "easy"
    obs = env.reset(task=task)
    return {"observation": obs.model_dump(), "reward": 0.0, "done": False, "info": {}}


@app.post("/step")
async def step(action: EasemydischargeAction):
    result = env.step(action)
    return result.model_dump()


@app.get("/state")
async def get_state():
    return env.state()


# ── Hackathon routes — every format the validator might try ──────────

@app.get("/tasks")
async def list_tasks():
    """Task list — used by validator to discover graders."""
    return {"tasks": TASKS}


@app.get("/grader")
@app.post("/grader")
async def grader_all():
    """All task scores. Format matches multiple validator schemas."""
    scores = _all_scores()
    return {
        "task_scores": scores,
        "scores": scores,
        "results": [{"task_id": k, "id": k, "score": v, "reward": v} for k, v in scores.items()],
    }


@app.get("/grader/{task_id}")
@app.post("/grader/{task_id}")
async def grader_by_task(task_id: str):
    """Per-task grader — called as /grader/easy, /grader/medium, /grader/hard."""
    score = _run_grader(task_id)
    return {"task_id": task_id, "id": task_id, "score": score, "reward": score}


@app.get("/grade")
async def grade_all():
    """Alias /grade → /grader."""
    scores = _all_scores()
    return {"task_scores": scores, "scores": scores}


@app.get("/grade/{task_id}")
async def grade_by_task(task_id: str):
    """Alias /grade/{id} → /grader/{id}."""
    score = _run_grader(task_id)
    return {"task_id": task_id, "score": score}


@app.get("/baseline")
async def baseline():
    """Baseline scores for reference."""
    scores = _all_scores()
    return {"task_scores": scores, "total_reward": sum(scores.values()), "steps_taken": 30}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()