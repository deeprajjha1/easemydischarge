"""
Grader functions for easemydischarge-pm-env (OpenEnv Hackathon).

Each grader runs a baseline agent trajectory through the environment
and returns a deterministic score in [0.0, 1.0].

The graders are self-contained — they replicate the environment's
scoring logic without importing server modules, so the validator
can call them directly from the repo root.

Two calling conventions are supported:
  1. grade_easy()           — standalone, runs internal baseline trajectory
  2. grade_easy(env_state)  — evaluates a live environment's final state
"""


# ── Task concept definitions ─────────────────────────────────────────

TASK_CONCEPTS = {
    "easy": {
        "auto_extraction": {
            "keywords": ["auto-extraction", "auto extraction", "ehr", "ocr", "electronic health", "auto-fill", "autofill", "scan"],
            "weight": 0.18,
        },
        "templates": {
            "keywords": ["template", "payer-specific", "form template", "claim form", "insurance form"],
            "weight": 0.14,
        },
        "validation": {
            "keywords": ["validation", "validate", "completeness", "error check", "pre-submission", "field check"],
            "weight": 0.14,
        },
        "parallelization": {
            "keywords": ["parallel", "concurrent", "async", "batch", "multi-thread", "throughput", "speed up"],
            "weight": 0.14,
        },
        "error_reduction": {
            "keywords": ["error reduction", "cross-reference", "accuracy", "quality assurance", "reduce error"],
            "weight": 0.12,
        },
        "feedback_loop": {
            "keywords": ["feedback loop", "machine learning", "ml", "historical", "rejection pattern", "adapt"],
            "weight": 0.14,
        },
        "roadmap": {
            "keywords": ["roadmap", "phase", "rollout", "plan"],
            "weight": 0.14,
        },
    },
    "medium": {
        "dependency_mapping": {
            "keywords": ["dependency", "dag", "prerequisite", "process flow", "workflow"],
            "weight": 0.14,
        },
        "timeout": {
            "keywords": ["timeout", "time limit", "sla", "deadline", "auto-expire", "expire"],
            "weight": 0.14,
        },
        "escalation": {
            "keywords": ["escalation", "supervisor", "override", "manager", "alert", "intervene"],
            "weight": 0.14,
        },
        "priority_queue": {
            "keywords": ["priority", "queue", "triage", "severity", "critical", "urgent", "fast-track"],
            "weight": 0.14,
        },
        "deadlock_resolution": {
            "keywords": ["deadlock", "circular", "conflict", "mediation", "arbitration", "cycle"],
            "weight": 0.16,
        },
        "parallel_noc": {
            "keywords": ["parallel", "concurrent", "batch", "independent", "non-dependent"],
            "weight": 0.14,
        },
        "roadmap": {
            "keywords": ["roadmap", "phase", "plan"],
            "weight": 0.14,
        },
    },
    "hard": {
        "microservices": {
            "keywords": ["microservice", "monolith", "bounded context", "service mesh", "api gateway", "domain-driven"],
            "weight": 0.12,
        },
        "multi_tenancy": {
            "keywords": ["multi-tenant", "data isolation", "schema per", "database per", "segregation"],
            "weight": 0.12,
        },
        "interoperability": {
            "keywords": ["hl7", "fhir", "interoperab", "api standard", "integration", "r4"],
            "weight": 0.12,
        },
        "compliance": {
            "keywords": ["hipaa", "hitrust", "compliance", "phi", "audit trail", "regulatory", "protected health"],
            "weight": 0.13,
        },
        "monitoring": {
            "keywords": ["monitoring", "prometheus", "grafana", "tracing", "observability", "apm", "logging", "metrics"],
            "weight": 0.11,
        },
        "security": {
            "keywords": ["sso", "saml", "oauth", "rbac", "encryption", "zero trust", "access control"],
            "weight": 0.10,
        },
        "rollout": {
            "keywords": ["rollout", "canary", "blue-green", "pilot", "migration", "phased", "incremental"],
            "weight": 0.10,
        },
        "performance": {
            "keywords": ["performance", "latency", "throughput", "load balanc", "caching", "auto-scal", "horizontal"],
            "weight": 0.08,
        },
        "disaster_recovery": {
            "keywords": ["disaster", "backup", "failover", "redundancy", "high availability", "replication", "hot standby"],
            "weight": 0.07,
        },
        "change_management": {
            "keywords": ["change management", "training", "adoption", "onboarding", "documentation", "transition"],
            "weight": 0.05,
        },
    },
}

VALID_DEPARTMENTS = {"nursing", "pharmacy", "lab", "billing", "admin"}
VALID_COMPONENTS = {"claim_pipeline", "noc_pipeline", "discharge_flow"}
REQUIRED_DEPTS = {"easy": 1, "medium": 3, "hard": 5}
MAX_STEPS = {"easy": 10, "medium": 12, "hard": 15}


# ── Scoring helpers ──────────────────────────────────────────────────

def _clamp(score: float) -> float:
    return round(max(0.01, min(0.99, score)), 4)


def _match_concepts(text: str, task: str, covered: set) -> set:
    matched = set()
    for cid, cdef in TASK_CONCEPTS.get(task, {}).items():
        if cid in covered:
            continue
        if any(kw in text for kw in cdef["keywords"]):
            matched.add(cid)
    return matched


def _concept_weights(concept_ids: set, task: str) -> float:
    concepts = TASK_CONCEPTS.get(task, {})
    return sum(concepts[c]["weight"] for c in concept_ids if c in concepts)


def _coverage_ratio(covered: set, task: str) -> float:
    total = len(TASK_CONCEPTS.get(task, {}))
    return len(covered) / total if total > 0 else 0.0


def _score_trajectory(task: str, actions: list) -> float:
    """
    Score a sequence of actions for a given task.
    Mirrors server/environment.py scoring logic exactly.
    """
    max_steps = MAX_STEPS[task]
    step_count = 0
    queried_swarm = False
    queried_depts: set = set()
    analyzed: set = set()
    covered: set = set()
    has_submitted = False
    actions_taken = []
    last_action_str = ""

    for ad in actions:
        if step_count >= max_steps:
            break
        step_count += 1
        atype = ad.get("action_type", "")
        action_str = str(ad)
        is_repeat = action_str == last_action_str
        last_action_str = action_str

        if atype == "query_swarm":
            queried_swarm = True
        elif atype == "query_department":
            dept = (ad.get("department") or "").lower().strip()
            if dept in VALID_DEPARTMENTS:
                queried_depts.add(dept)
        elif atype == "analyze":
            comp = (ad.get("component") or "").lower().strip()
            if comp in VALID_COMPONENTS:
                analyzed.add(comp)
        elif atype == "propose_feature":
            text = (ad.get("feature_description") or "").lower()
            new_concepts = _match_concepts(text, task, covered)
            covered.update(new_concepts)
        elif atype == "submit_roadmap":
            roadmap_text = str(ad.get("roadmap", "")).lower()
            new_concepts = _match_concepts(roadmap_text, task, covered)
            covered.update(new_concepts)
            has_submitted = True

        actions_taken.append(ad)

        done = (atype == "submit_roadmap") or (step_count >= max_steps)
        if done:
            break

    if not actions_taken:
        return 0.01

    coverage = _coverage_ratio(covered, task)

    inv_pts = 0.0
    if queried_swarm:
        inv_pts += 1.0
    req_depts = REQUIRED_DEPTS[task]
    inv_pts += min(len(queried_depts) / req_depts, 1.0)
    if analyzed:
        inv_pts += 1.0
    investigation = inv_pts / 3.0

    first_investigate = first_propose = None
    for i, a in enumerate(actions_taken):
        at = a.get("action_type", "")
        if at in ("query_swarm", "query_department", "analyze") and first_investigate is None:
            first_investigate = i
        if at in ("propose_feature", "submit_roadmap") and first_propose is None:
            first_propose = i

    if first_investigate is not None and first_propose is not None:
        order = 0.4 if first_investigate < first_propose else 0.1
    elif first_investigate is not None:
        order = 0.3
    else:
        order = 0.0

    types_used = {a.get("action_type", "") for a in actions_taken}
    diversity = min(len(types_used) / 4.0, 1.0) * 0.3

    strs = [str(a) for a in actions_taken]
    unique_ratio = len(set(strs)) / len(strs) if strs else 1.0
    repetition = unique_ratio * 0.3

    strategy = order + diversity + repetition
    completeness = 1.0 if has_submitted else 0.5

    final_score = (
        coverage * 0.40
        + investigation * 0.25
        + strategy * 0.20
        + completeness * 0.15
    )
    return _clamp(final_score)


# ── Baseline trajectories (what a competent agent would do) ──────────
# These represent realistic baseline performance, NOT perfect play.

_EASY_BASELINE = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "claim_pipeline"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "propose_feature", "feature_description":
        "auto-extraction from ehr electronic health records ocr scan documents auto-fill claim forms"},
    {"action_type": "propose_feature", "feature_description":
        "payer-specific insurance claim templates template matching based claim form requirements"},
    {"action_type": "propose_feature", "feature_description":
        "real-time field validation completeness checks pre-submission error check"},
    {"action_type": "propose_feature", "feature_description":
        "parallelize concurrent async batch multi-thread throughput speed up processing"},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: auto-extraction ehr ocr",
            "Phase 2: templates and validation",
            "Phase 3: parallel processing rollout plan",
        ]
    }},
]

_MEDIUM_BASELINE = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "noc_pipeline"},
    {"action_type": "query_department", "department": "nursing"},
    {"action_type": "query_department", "department": "pharmacy"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "propose_feature", "feature_description":
        "dependency dag prerequisite workflow process flow between departments"},
    {"action_type": "propose_feature", "feature_description":
        "timeout time limit sla deadline auto-expire for unresponsive departments"},
    {"action_type": "propose_feature", "feature_description":
        "escalation supervisor override manager alert when noc blocked"},
    {"action_type": "propose_feature", "feature_description":
        "deadlock circular conflict mediation arbitration cycle resolution"},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: dependency mapping and deadlock resolution",
            "Phase 2: timeout sla and escalation",
            "Phase 3: parallel noc processing roadmap plan",
        ]
    }},
]

_HARD_BASELINE = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "discharge_flow"},
    {"action_type": "query_department", "department": "nursing"},
    {"action_type": "query_department", "department": "pharmacy"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "propose_feature", "feature_description":
        "microservice bounded context service mesh api gateway domain-driven"},
    {"action_type": "propose_feature", "feature_description":
        "multi-tenant data isolation schema per hospital database per tenant"},
    {"action_type": "propose_feature", "feature_description":
        "hl7 fhir r4 interoperab api standard integration healthcare"},
    {"action_type": "propose_feature", "feature_description":
        "hipaa hitrust compliance phi audit trail regulatory"},
    {"action_type": "propose_feature", "feature_description":
        "monitoring prometheus grafana tracing observability apm logging"},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: microservices and multi-tenancy",
            "Phase 2: compliance and interoperability",
            "Phase 3: monitoring and phased rollout plan",
        ]
    }},
]


# ── Public API ────────────────────────────────────────────────────────

def grade_easy(env_state=None) -> float:
    """
    Grade the easy task: Claim Pipeline Optimization.

    If env_state is provided (dict with 'concepts_covered', 'actions_taken', etc.),
    scores the actual agent trajectory. Otherwise runs the baseline.

    Returns: float in [0.01, 0.99]
    """
    if env_state and isinstance(env_state, dict):
        actions = env_state.get("actions_taken")
        if actions is not None:
            return _score_trajectory("easy", actions)
    return _score_trajectory("easy", _EASY_BASELINE)


def grade_medium(env_state=None) -> float:
    """
    Grade the medium task: NOC Coordination Resolution.
    Returns: float in [0.01, 0.99]
    """
    if env_state and isinstance(env_state, dict):
        actions = env_state.get("actions_taken")
        if actions is not None:
            return _score_trajectory("medium", actions)
    return _score_trajectory("medium", _MEDIUM_BASELINE)


def grade_hard(env_state=None) -> float:
    """
    Grade the hard task: Multi-Hospital Scaling Architecture.
    Returns: float in [0.01, 0.99]
    """
    if env_state and isinstance(env_state, dict):
        actions = env_state.get("actions_taken")
        if actions is not None:
            return _score_trajectory("hard", actions)
    return _score_trajectory("hard", _HARD_BASELINE)


if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "all"
    if task in ("all", "easy"):
        print(f"easy:   {grade_easy():.4f}")
    if task in ("all", "medium"):
        print(f"medium: {grade_medium():.4f}")
    if task in ("all", "hard"):
        print(f"hard:   {grade_hard():.4f}")
