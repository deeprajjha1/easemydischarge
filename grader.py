"""
Grader functions for the easemydischarge-pm-env OpenEnv environment.

These functions are self-contained — they instantiate the environment
directly (no HTTP server needed) and run deterministic episodes in-process.

Each function returns a score strictly in (0.01, 0.99) — never 0.0 or 1.0.
"""
import os
import sys

# Ensure the repo root is on the path so we can import server + models
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from server.environment import EasemydischargePMEnv
from models import EasemydischargeAction, ActionType


def _clamp(score: float) -> float:
    """Clamp to (0.01, 0.99) — strictly inside (0, 1) exclusive."""
    return round(max(0.01, min(0.99, score)), 3)


def _run_episode(task: str, action_dicts: list) -> float:
    """
    Instantiate the env, reset for `task`, execute the action sequence,
    and return the clamped final score.
    """
    env = EasemydischargePMEnv()
    env.reset(task=task)
    result = None
    for ad in action_dicts:
        action = EasemydischargeAction(
            action_type=ActionType(ad["action_type"]),
            department=ad.get("department"),
            component=ad.get("component"),
            feature_description=ad.get("feature_description"),
            roadmap=ad.get("roadmap"),
        )
        result = env.step(action)
        if result.done:
            break
    if result is None:
        return 0.01
    return _clamp(result.info.get("final_score", 0.0))


# ── Task action sequences ────────────────────────────────────────────

_EASY_ACTIONS = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "claim_pipeline"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "propose_feature", "feature_description":
        "Implement auto-extraction from EHR and electronic health records "
        "to eliminate manual data entry, using OCR to scan documents and "
        "auto-fill claim forms automatically."},
    {"action_type": "propose_feature", "feature_description":
        "Add payer-specific insurance claim templates with automatic "
        "template matching based on the insurance form type and claim form "
        "requirements, using pre-configured form templates."},
    {"action_type": "propose_feature", "feature_description":
        "Build real-time field validation with completeness checks, "
        "verify field data quality with pre-submission error checks "
        "to reduce the current 12% validation fail rate."},
    {"action_type": "propose_feature", "feature_description":
        "Parallelize independent claim sections for concurrent processing, "
        "using async batch multi-threaded operations to speed up processing "
        "and increase throughput from 15 to 40 claims per hour."},
    {"action_type": "propose_feature", "feature_description":
        "Implement error reduction via cross-referencing multiple data "
        "sources for verification, improving accuracy and reducing the "
        "error rate through quality assurance checks."},
    {"action_type": "propose_feature", "feature_description":
        "Create a machine learning feedback loop that learns from past "
        "claims and historical rejection patterns to improve accuracy "
        "and adapt over time, reducing future errors."},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: Auto-extraction from EHR and OCR scanning",
            "Phase 2: Payer-specific templates and real-time validation",
            "Phase 3: Parallel processing, error reduction, and ML feedback loop",
        ]
    }},
]

_MEDIUM_ACTIONS = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "noc_pipeline"},
    {"action_type": "query_department", "department": "nursing"},
    {"action_type": "query_department", "department": "pharmacy"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "propose_feature", "feature_description":
        "Map inter-department dependencies using a DAG to identify "
        "prerequisite relationships and workflow process flow between departments."},
    {"action_type": "propose_feature", "feature_description":
        "Add auto-timeout with time limits and SLA-based deadlines for "
        "each department response time, with auto-expire for unresponsive NOCs."},
    {"action_type": "propose_feature", "feature_description":
        "Implement escalation paths with supervisor override and manual "
        "intervention alerts to notify managers when NOCs are blocked."},
    {"action_type": "propose_feature", "feature_description":
        "Build a priority queue with triage and severity ranking to "
        "fast-track urgent and critical discharge cases, expediting delayed patients."},
    {"action_type": "propose_feature", "feature_description":
        "Resolve circular deadlock conflicts between departments through "
        "mediation and arbitration to break cycle dependencies."},
    {"action_type": "propose_feature", "feature_description":
        "Process independent non-dependent NOCs in parallel with concurrent "
        "batch department processing to reduce the 3.5 hour cycle time."},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: Dependency mapping and conflict resolution for deadlocks",
            "Phase 2: Timeout handling, escalation protocols, and priority queues",
            "Phase 3: Parallel NOC processing and real-time dashboard tracking",
        ]
    }},
]

_HARD_ACTIONS = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "discharge_flow"},
    {"action_type": "analyze", "component": "claim_pipeline"},
    {"action_type": "query_department", "department": "nursing"},
    {"action_type": "query_department", "department": "pharmacy"},
    {"action_type": "query_department", "department": "lab"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "query_department", "department": "admin"},
    {"action_type": "propose_feature", "feature_description":
        "Decompose the monolith into microservices with bounded context "
        "domain-driven design, service mesh, and API gateway for modular "
        "service-oriented architecture."},
    {"action_type": "propose_feature", "feature_description":
        "Implement multi-tenant data isolation with database per tenant, "
        "schema per hospital, and data segregation to keep patient data isolated."},
    {"action_type": "propose_feature", "feature_description":
        "Adopt HL7 FHIR R4 interoperability standards with a unified API "
        "and common REST API standard for healthcare integration."},
    {"action_type": "propose_feature", "feature_description":
        "Ensure HIPAA compliance and regulatory data protection across "
        "hospitals with PHI audit trails and HITRUST certification for "
        "protected health information privacy."},
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
            "Phase 6: Change management training adoption onboarding documentation support staff transition",
        ]
    }},
]


# ── Public grader functions (called by the validator) ────────────────

def grade_easy() -> float:
    """Grade the easy task. Returns score in (0, 1) exclusive."""
    return _run_episode("easy", _EASY_ACTIONS)


def grade_medium() -> float:
    """Grade the medium task. Returns score in (0, 1) exclusive."""
    return _run_episode("medium", _MEDIUM_ACTIONS)


def grade_hard() -> float:
    """Grade the hard task. Returns score in (0, 1) exclusive."""
    return _run_episode("hard", _HARD_ACTIONS)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "easy"
    fn = {"easy": grade_easy, "medium": grade_medium, "hard": grade_hard}[task]
    score = fn()
    print(f"[GRADER] {task} score: {score:.3f}")
