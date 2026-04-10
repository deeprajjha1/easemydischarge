"""
Grader functions for easemydischarge-pm-env (OpenEnv Hackathon).

COMPLETELY SELF-CONTAINED — uses only Python standard library.
No dependencies on server/, models/, pydantic, httpx, or any local modules.

The validator imports this file and calls grade_easy(), grade_medium(),
or grade_hard() directly without a running environment server.

Each function returns a float strictly in (0.0, 1.0) exclusive.
"""


# ── Task concept definitions ─────────────────────────────────────────
# Mirrors server/data.py TASK_CONCEPTS without the import

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
    return round(max(0.01, min(0.99, score)), 3)


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


def _simulate_episode(task: str, actions: list) -> float:
    """
    Pure-Python in-process simulation — no external calls, no imports.
    Mirrors the reward/scoring logic in server/environment.py exactly.
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

    final_score = 0.01

    for ad in actions:
        if step_count >= max_steps:
            break
        step_count += 1
        atype = ad["action_type"]
        action_str = str(ad)
        is_repeat = action_str == last_action_str
        last_action_str = action_str

        # --- Reward ---
        base = 0.0
        if atype == "query_swarm":
            base = 0.30 if not queried_swarm else 0.05
            queried_swarm = True

        elif atype == "query_department":
            dept = (ad.get("department") or "").lower().strip()
            if dept in VALID_DEPARTMENTS and dept not in queried_depts:
                base = 0.25
                queried_depts.add(dept)
            else:
                base = 0.05

        elif atype == "analyze":
            comp = (ad.get("component") or "").lower().strip()
            if comp in VALID_COMPONENTS and comp not in analyzed:
                base = 0.30
                analyzed.add(comp)
            else:
                base = 0.08

        elif atype == "propose_feature":
            text = (ad.get("feature_description") or "").lower()
            new_concepts = _match_concepts(text, task, covered)
            if new_concepts:
                cw = _concept_weights(new_concepts, task)
                base = 0.15 + min(cw, 0.55)
                covered.update(new_concepts)
            else:
                base = 0.10
            if not queried_swarm and not queried_depts:
                base *= 0.5

        elif atype == "submit_roadmap":
            # Also check roadmap text for concepts
            roadmap_text = str(ad.get("roadmap", "")).lower()
            new_concepts = _match_concepts(roadmap_text, task, covered)
            covered.update(new_concepts)
            has_submitted = True
            coverage = _coverage_ratio(covered, task)
            base = 0.20 + (coverage * 0.60)

        if is_repeat:
            base *= 0.25

        actions_taken.append({"action_type": atype, **{k: v for k, v in ad.items() if k != "action_type"}})

        # Check done
        done = (atype == "submit_roadmap") or (step_count >= max_steps)
        if done:
            # Final score
            coverage = _coverage_ratio(covered, task)

            # Investigation score
            inv_pts = 0.0
            if queried_swarm:
                inv_pts += 1.0
            req_depts = REQUIRED_DEPTS[task]
            inv_pts += min(len(queried_depts) / req_depts, 1.0)
            if analyzed:
                inv_pts += 1.0
            investigation = inv_pts / 3.0

            # Strategy score
            first_investigate = first_propose = None
            for i, a in enumerate(actions_taken):
                at = a["action_type"]
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

            types_used = {a["action_type"] for a in actions_taken}
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
            break

    return _clamp(final_score)


# ── Action sequences ─────────────────────────────────────────────────

_EASY_ACTIONS = [
    {"action_type": "query_swarm"},
    {"action_type": "analyze", "component": "claim_pipeline"},
    {"action_type": "query_department", "department": "billing"},
    {"action_type": "propose_feature", "feature_description":
        "auto-extraction from ehr electronic health records ocr scan documents auto-fill claim forms"},
    {"action_type": "propose_feature", "feature_description":
        "payer-specific insurance claim templates template matching based claim form requirements pre-configured form templates"},
    {"action_type": "propose_feature", "feature_description":
        "real-time field validation completeness checks pre-submission error check reduce 12pct validation fail rate"},
    {"action_type": "propose_feature", "feature_description":
        "parallelize concurrent async batch multi-thread throughput speed up processing from 15 to 40 claims per hour"},
    {"action_type": "propose_feature", "feature_description":
        "error reduction cross-reference accuracy quality assurance reduce error rate verification"},
    {"action_type": "propose_feature", "feature_description":
        "machine learning feedback loop historical rejection pattern accuracy adapt over time"},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: auto-extraction ehr ocr scan",
            "Phase 2: payer-specific templates field validation",
            "Phase 3: parallel concurrent async batch processing error reduction feedback loop ml",
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
        "dependency dag prerequisite workflow process flow between departments map"},
    {"action_type": "propose_feature", "feature_description":
        "timeout time limit sla deadline auto-expire expire unresponsive noc"},
    {"action_type": "propose_feature", "feature_description":
        "escalation supervisor override manager alert intervene when noc blocked"},
    {"action_type": "propose_feature", "feature_description":
        "priority queue triage severity urgent critical fast-track delayed discharge"},
    {"action_type": "propose_feature", "feature_description":
        "deadlock circular conflict mediation arbitration cycle resolution"},
    {"action_type": "propose_feature", "feature_description":
        "parallel concurrent batch independent non-dependent noc processing"},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: dependency dag conflict deadlock circular cycle resolution",
            "Phase 2: timeout sla deadline escalation priority queue triage",
            "Phase 3: parallel concurrent batch non-dependent noc processing dashboard",
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
        "microservice monolith bounded context service mesh api gateway domain-driven decompose"},
    {"action_type": "propose_feature", "feature_description":
        "multi-tenant data isolation schema per hospital database per tenant segregation"},
    {"action_type": "propose_feature", "feature_description":
        "hl7 fhir r4 interoperab api standard integration healthcare"},
    {"action_type": "propose_feature", "feature_description":
        "hipaa hitrust compliance phi audit trail regulatory protected health information"},
    {"action_type": "propose_feature", "feature_description":
        "monitoring prometheus grafana tracing observability apm logging metrics distributed"},
    {"action_type": "propose_feature", "feature_description":
        "sso saml oauth rbac encryption zero trust access control security"},
    {"action_type": "submit_roadmap", "roadmap": {
        "phases": [
            "Phase 1: microservice monolith bounded context domain-driven service mesh api gateway multi-tenant data isolation hl7 fhir r4 interoperab",
            "Phase 2: hipaa hitrust phi audit compliance sso saml oauth rbac encryption zero trust rollout canary blue-green pilot phased incremental migration",
            "Phase 3: performance latency throughput load balanc caching auto-scal horizontal",
            "Phase 4: disaster backup failover redundancy high availability replication hot standby",
            "Phase 5: change management training adoption onboarding documentation transition",
        ]
    }},
]


# ── Public API (called by the validator) ─────────────────────────────

def grade_easy() -> float:
    """
    Grade the easy task: Claim Pipeline Optimization.
    Deterministic, no external calls. Returns score in (0.0, 1.0).
    """
    return _simulate_episode("easy", _EASY_ACTIONS)


def grade_medium() -> float:
    """
    Grade the medium task: NOC Coordination Resolution.
    Deterministic, no external calls. Returns score in (0.0, 1.0).
    """
    return _simulate_episode("medium", _MEDIUM_ACTIONS)


def grade_hard() -> float:
    """
    Grade the hard task: Multi-Hospital Scaling Architecture.
    Deterministic, no external calls. Returns score in (0.0, 1.0).
    """
    return _simulate_episode("hard", _HARD_ACTIONS)


if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "all"
    if task in ("all", "easy"):
        print(f"easy:   {grade_easy():.3f}")
    if task in ("all", "medium"):
        print(f"medium: {grade_medium():.3f}")
    if task in ("all", "hard"):
        print(f"hard:   {grade_hard():.3f}")
