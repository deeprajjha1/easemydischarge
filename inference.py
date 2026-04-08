"""
Inference script for easemydischarge-pm-env.

Uses the OpenAI client to call an LLM, which decides what actions to take
in the hospital discharge PM environment.

Environment variables:
    API_BASE_URL  — LLM API endpoint (default: HF router)
    MODEL_NAME    — Model identifier
    HF_TOKEN      — API key
    TASK          — Task difficulty: easy, medium, hard
"""
import asyncio
import json
import os
import textwrap
from typing import Dict, Any, List, Optional

import httpx
from openai import OpenAI

# ── Config ───────────────────────────────────────────────────────────
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
TASK = os.getenv("TASK", "easy")
MAX_STEPS = {"easy": 10, "medium": 12, "hard": 15}.get(TASK, 10)


# ── Logging ──────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    print(
        f"[STEP] step={step} action={action[:80]} reward={reward:.2f} "
        f"done={str(done).lower()} error={error or 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    r_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={r_str}",
        flush=True,
    )


# ── System prompt ────────────────────────────────────────────────────
TASK_BRIEFS = {
    "easy": "Optimize the insurance claim pre-filling pipeline. Focus on auto-extraction, templates, validation, parallelization, error reduction, and feedback loops.",
    "medium": "Resolve NOC coordination deadlocks. Focus on dependency mapping, timeouts, escalation, priority queuing, conflict resolution, parallel NOCs, and status tracking.",
    "hard": "Design a multi-hospital scaling architecture. Cover microservices, data isolation, interoperability (FHIR/HL7), compliance, monitoring, phased rollout, performance, DR, security, and change management.",
}

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert AI Product Manager at easemydischarge, a healthcare startup.
    The company uses a swarm of AI agents to automate hospital patient discharge:
    - Claim pre-fill agent: auto-fills insurance claim forms
    - NOC coordinator: gets No Objection Certificates from departments (Nursing, Pharmacy, Lab, Billing, Admin)
    - Orchestrator and Synchronizer manage the workflow

    STRATEGY (follow this order for best results):
    1. INVESTIGATE first: query_swarm and query_department to understand issues
    2. ANALYZE: analyze components (claim_pipeline, noc_pipeline, discharge_flow)
    3. PROPOSE: propose specific feature improvements with detailed descriptions
    4. SUBMIT: submit a final roadmap summarizing your plan

    RESPOND WITH EXACTLY ONE JSON OBJECT per turn. No other text. Examples:
    {{"action_type": "query_swarm"}}
    {{"action_type": "query_department", "department": "pharmacy"}}
    {{"action_type": "analyze", "component": "claim_pipeline"}}
    {{"action_type": "propose_feature", "feature_description": "Implement auto-extraction from EHR..."}}
    {{"action_type": "submit_roadmap", "roadmap": {{"phases": ["Phase 1: ...", "Phase 2: ..."]}}}}
""")


def build_user_prompt(obs: Dict[str, Any], step: int, task: str, history: List[str]) -> str:
    brief = TASK_BRIEFS.get(task, "")
    hist_block = "\n".join(history[-5:]) if history else "None"
    data_str = json.dumps(obs.get("data", {}), indent=2)[:1500]
    concepts = obs.get("concepts_covered", [])
    inv = obs.get("investigation_summary", {})

    return textwrap.dedent(f"""\
        CURRENT TASK ({task.upper()}): {brief}
        Step: {step}/{obs.get('max_steps', MAX_STEPS)}

        Environment message: {obs.get('message', '')}

        Data from last action:
        {data_str}

        Investigation progress: {json.dumps(inv)}
        Concepts already covered: {concepts}

        Recent history:
        {hist_block}

        Choose your next action (JSON only):
    """)


def parse_action(text: str, step: int, max_steps: int) -> Dict[str, Any]:
    """Parse LLM response into action dict. Falls back to sensible defaults."""
    text = text.strip()
    # Extract JSON from potential markdown code blocks
    if "```" in text:
        for line in text.split("```"):
            line = line.strip()
            if line.startswith("json"):
                line = line[4:].strip()
            if line.startswith("{"):
                text = line
                break

    # Find the JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    # Fallback strategy: investigate early, propose later
    if step == 1:
        return {"action_type": "query_swarm"}
    elif step == 2:
        return {"action_type": "analyze", "component": "claim_pipeline"}
    elif step <= 4:
        depts = ["nursing", "pharmacy", "lab", "billing", "admin"]
        return {"action_type": "query_department", "department": depts[step - 3]}
    elif step == max_steps:
        return {"action_type": "submit_roadmap", "roadmap": {"phases": ["Phase 1: Auto-extraction and templates", "Phase 2: Validation and parallelization", "Phase 3: Feedback loops and monitoring"]}}
    else:
        proposals = [
            "Implement auto-extraction from EHR systems to eliminate manual data entry for claim pre-filling",
            "Add insurance-specific claim templates with automatic payer detection and form selection",
            "Build real-time field validation with completeness checks before claim submission",
            "Parallelize independent claim sections for concurrent processing to reduce cycle time",
            "Implement error reduction through cross-referencing multiple data sources and quality checks",
            "Create a machine learning feedback loop that learns from past claim rejections to improve accuracy",
            "Add timeout mechanisms and escalation protocols for unresponsive department NOCs",
            "Build dependency mapping to identify and break circular NOC deadlocks between departments",
            "Design priority queue system for critical and delayed discharge cases",
            "Implement real-time dashboard for NOC status tracking and transparency",
        ]
        idx = (step - 5) % len(proposals)
        return {"action_type": "propose_feature", "feature_description": proposals[idx]}


def get_llm_action(client: OpenAI, obs: Dict[str, Any], step: int, task: str, history: List[str]) -> Dict[str, Any]:
    """Call LLM and parse response into an action."""
    user_prompt = build_user_prompt(obs, step, task, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        text = (completion.choices[0].message.content or "").strip()
        return parse_action(text, step, MAX_STEPS)
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return parse_action("", step, MAX_STEPS)


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    final_score = 0.0
    success = False

    log_start(task=TASK, env="easemydischarge-pm-env", model=MODEL_NAME)

    async with httpx.AsyncClient(timeout=60.0) as http:
        try:
            # Reset environment
            resp = await http.post(f"{ENV_BASE_URL}/reset", json={"task": TASK})
            result = resp.json()
            obs = result["observation"]

            for step in range(1, MAX_STEPS + 1):
                action = get_llm_action(client, obs, step, TASK, history)
                action_label = action.get("feature_description", action.get("department", action.get("component", action["action_type"])))

                resp = await http.post(f"{ENV_BASE_URL}/step", json=action)
                result = resp.json()

                obs = result["observation"]
                reward = result["reward"]
                done = result["done"]
                error = result.get("info", {}).get("error")

                rewards.append(reward)
                steps_taken = step
                log_step(step, str(action_label)[:80], reward, done, error)
                history.append(f"Step {step}: {action['action_type']} -> reward {reward:.2f}")

                if done:
                    final_score = result.get("info", {}).get("final_score", 0.0)
                    break

            success = final_score >= 0.3

        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            success = False

    log_end(success, steps_taken, final_score, rewards)


if __name__ == "__main__":
    asyncio.run(main())