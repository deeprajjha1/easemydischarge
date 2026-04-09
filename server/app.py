from fastapi import FastAPI, Request
from typing import Dict, List, Optional, Any
import uvicorn
from models import EasemydischargeAction
from server.environment import EasemydischargePMEnv
from pydantic import BaseModel

app = FastAPI(title="easemydischarge-pm-env")
env = EasemydischargePMEnv()


# ── Models for /tasks and /grader ────────────────────────────────────

class TaskInfo(BaseModel):
    id: str
    name: str
    difficulty: str
    description: str
    grader: str


class GraderResponse(BaseModel):
    task_scores: Dict[str, float]


# ── Task definitions ──────────────────────────────────────────────────

TASKS = [
    TaskInfo(
        id="easy",
        name="Claim Pipeline Optimization",
        difficulty="easy",
        description=(
            "Optimize the insurance claim pre-filling pipeline. Investigate "
            "the swarm agents and propose improvements to reduce errors and "
            "speed up claim processing."
        ),
        grader="EasemydischargeGrader.grade_easy",
    ),
    TaskInfo(
        id="medium",
        name="NOC Coordination Resolution",
        difficulty="medium",
        description=(
            "Resolve NOC coordination deadlocks between hospital departments. "
            "Investigate inter-department conflicts, propose timeout and escalation "
            "mechanisms, and improve parallel coordination."
        ),
        grader="EasemydischargeGrader.grade_medium",
    ),
    TaskInfo(
        id="hard",
        name="Multi-Hospital Scaling Architecture",
        difficulty="hard",
        description=(
            "Design a scaling architecture to expand from 1 hospital to 50. "
            "Address multi-tenancy, compliance, interoperability, monitoring, "
            "and phased rollout."
        ),
        grader="EasemydischargeGrader.grade_hard",
    ),
]


# ── Grader class ──────────────────────────────────────────────────────

class EasemydischargeGrader:
    """Runs deterministic episodes and returns scores in (0.01, 0.99)."""

    def __init__(self):
        self.env = EasemydischargePMEnv()

    @staticmethod
    def _clamp(score: float) -> float:
        return max(0.01, min(0.99, score))

    def _run_episode(self, task: str, actions: list) -> float:
        self.env.reset(task=task)
        result = None
        for action in actions:
            from models import EasemydischargeAction, ActionType
            act = EasemydischargeAction(
                action_type=ActionType(action["action_type"]),
                department=action.get("department"),
                component=action.get("component"),
                feature_description=action.get("feature_description"),
                roadmap=action.get("roadmap"),
            )
            result = self.env.step(act)
            if result.done:
                break
        if result is None:
            return 0.01
        final_score = result.info.get("final_score", 0.0)
        return self._clamp(final_score)

    def grade_easy(self) -> float:
        actions = [
            {"action_type": "query_swarm"},
            {"action_type": "analyze", "component": "claim_pipeline"},
            {"action_type": "query_department", "department": "billing"},
            {"action_type": "propose_feature", "feature_description":
                "Implement auto-extraction from EHR and electronic health records "
                "to eliminate manual data entry, using OCR to scan documents and auto-fill claim forms."},
            {"action_type": "propose_feature", "feature_description":
                "Add payer-specific insurance claim templates with automatic template matching "
                "based on claim form type and insurance form requirements, using pre-configured form templates."},
            {"action_type": "propose_feature", "feature_description":
                "Build real-time field validation with completeness checks, verify field data quality "
                "with pre-submission error checks to reduce the 12% validation fail rate."},
            {"action_type": "propose_feature", "feature_description":
                "Parallelize independent claim sections for concurrent processing, "
                "using async batch multi-threaded operations to speed up processing throughput."},
            {"action_type": "propose_feature", "feature_description":
                "Implement error reduction via cross-referencing multiple data sources "
                "for verification, improving accuracy through quality assurance."},
            {"action_type": "propose_feature", "feature_description":
                "Create a machine learning feedback loop that learns from past claims "
                "and historical rejection patterns to improve accuracy and adapt over time."},
            {"action_type": "submit_roadmap", "roadmap": {
                "phases": [
                    "Phase 1: Auto-extraction from EHR and OCR scanning",
                    "Phase 2: Payer-specific templates and real-time validation",
                    "Phase 3: Parallel processing, error reduction, and ML feedback loop"
                ]
            }},
        ]
        return self._run_episode("easy", actions)

    def grade_medium(self) -> float:
        actions = [
            {"action_type": "query_swarm"},
            {"action_type": "analyze", "component": "noc_pipeline"},
            {"action_type": "query_department", "department": "nursing"},
            {"action_type": "query_department", "department": "pharmacy"},
            {"action_type": "query_department", "department": "billing"},
            {"action_type": "propose_feature", "feature_description":
                "Map inter-department dependencies using a DAG to identify "
                "prerequisite relationships and workflow process flow between departments."},
            {"action_type": "propose_feature", "feature_description":
                "Add auto-timeout with time limits and SLA-based deadlines for each department, "
                "with auto-expire mechanism for unresponsive NOCs."},
            {"action_type": "propose_feature", "feature_description":
                "Implement escalation paths with supervisor override and manual intervention "
                "alerts to notify managers when NOCs are blocked."},
            {"action_type": "propose_feature", "feature_description":
                "Build a priority queue with triage and severity ranking to fast-track "
                "urgent and critical discharge cases, expediting delayed patients."},
            {"action_type": "propose_feature", "feature_description":
                "Resolve circular deadlock conflicts between departments through "
                "mediation and arbitration to break the cycle dependency."},
            {"action_type": "propose_feature", "feature_description":
                "Process independent non-dependent NOCs in parallel with concurrent "
                "batch department processing to reduce the 3.5 hour NOC cycle time."},
            {"action_type": "submit_roadmap", "roadmap": {
                "phases": [
                    "Phase 1: Dependency mapping and conflict resolution for deadlocks",
                    "Phase 2: Timeout handling, escalation protocols, and priority queues",
                    "Phase 3: Parallel NOC processing and real-time dashboard tracking"
                ]
            }},
        ]
        return self._run_episode("medium", actions)

    def grade_hard(self) -> float:
        actions = [
            {"action_type": "query_swarm"},
            {"action_type": "analyze", "component": "discharge_flow"},
            {"action_type": "analyze", "component": "claim_pipeline"},
            {"action_type": "query_department", "department": "nursing"},
            {"action_type": "query_department", "department": "pharmacy"},
            {"action_type": "query_department", "department": "lab"},
            {"action_type": "query_department", "department": "billing"},
            {"action_type": "query_department", "department": "admin"},
            {"action_type": "propose_feature", "feature_description":
                "Decompose the monolith into microservices with bounded context domain-driven design, "
                "service mesh, and API gateway for modular service-oriented architecture."},
            {"action_type": "propose_feature", "feature_description":
                "Implement multi-tenant data isolation with database per tenant, schema per hospital, "
                "and data segregation to keep patient data isolated."},
            {"action_type": "propose_feature", "feature_description":
                "Adopt HL7 FHIR R4 interoperability standards with a unified API and "
                "common REST API standard for healthcare integration."},
            {"action_type": "propose_feature", "feature_description":
                "Ensure HIPAA compliance and regulatory data protection across hospitals "
                "with PHI audit trails and HITRUST certification for protected health information privacy."},
            {"action_type": "propose_feature", "feature_description":
                "Build centralized monitoring with distributed tracing, observability, "
                "logging, metrics, Prometheus, Grafana, alerts, and APM across all sites."},
            {"action_type": "submit_roadmap", "roadmap": {
                "phases": [
                    "Phase 1: Microservices decomposition, multi-tenant data isolation, and FHIR interoperability",
                    "Phase 2: HIPAA compliance, security with SSO SAML OAuth RBAC access control encryption zero trust",
                    "Phase 3: Incremental phased rollout with pilot canary blue-green migration onboarding plan",
                    "Phase 4: Performance optimization with latency throughput load balancing caching horizontal auto-scaling",
                    "Phase 5: Disaster recovery backup failover redundancy high availability replication hot standby",
                    "Phase 6: Change management training adoption onboarding documentation support staff transition"
                ]
            }},
        ]
        return self._run_episode("hard", actions)


# ── Standard gym-style routes ─────────────────────────────────────────

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


# ── Hackathon grader routes ───────────────────────────────────────────

@app.get("/tasks", response_model=List[TaskInfo])
async def list_tasks():
    """Return task definitions with grader references."""
    return TASKS


@app.get("/grader", response_model=GraderResponse)
async def get_grader_scores():
    """Run deterministic grading episodes for all tasks and return scores."""
    grader = EasemydischargeGrader()
    return GraderResponse(
        task_scores={
            "easy": grader.grade_easy(),
            "medium": grader.grade_medium(),
            "hard": grader.grade_hard(),
        }
    )


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()