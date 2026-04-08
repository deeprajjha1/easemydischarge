from fastapi import FastAPI, Request
from models import EasemydischargeAction
from server.environment import EasemydischargePMEnv

app = FastAPI(title="easemydischarge-pm-env")
env = EasemydischargePMEnv()


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


@app.get("/")
async def health():
    return {"status": "ok", "env": "easemydischarge-pm-env"}