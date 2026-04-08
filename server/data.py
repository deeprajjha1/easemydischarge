"""Rich simulation data for the easemydischarge PM environment."""

SWARM_STATUS = {
    "orchestrator": {
        "status": "operational",
        "queue_depth": 47,
        "avg_task_time_sec": 180,
        "error_rate": 0.03,
        "notes": "Stable but downstream claim agent is a bottleneck",
    },
    "claim_prefill_agent": {
        "status": "degraded",
        "queue_depth": 23,
        "avg_task_time_sec": 340,
        "error_rate": 0.12,
        "issues": [
            "Sequential processing of claim fields — no parallelization",
            "Manual template selection required for 40% of claims",
            "No auto-extraction from scanned documents",
            "Validation errors caught only at final submission",
        ],
    },
    "noc_coordinator_agent": {
        "status": "operational",
        "queue_depth": 31,
        "avg_task_time_sec": 720,
        "error_rate": 0.08,
        "issues": [
            "Sequential NOC requests — departments processed one by one",
            "No timeout mechanism — blocked NOC halts entire discharge",
            "No escalation path for overdue NOCs",
            "Average 3.5 hours per complete NOC cycle",
        ],
    },
    "synchronizer": {
        "status": "operational",
        "queue_depth": 12,
        "avg_task_time_sec": 60,
        "error_rate": 0.01,
        "notes": "Waits for all signals before final discharge clearance",
    },
}

DEPARTMENTS = {
    "nursing": {
        "name": "Nursing Department",
        "pending_nocs": 15,
        "avg_response_time_hours": 2.1,
        "approval_rate": 0.92,
        "blockers": [
            "Waiting for Pharmacy medication reconciliation before final nursing assessment",
            "Shift handover delays cause 1-2 hour gaps in NOC processing",
        ],
        "capacity": {"current_staff": 4, "max_staff": 6, "utilization": 0.67},
        "rejection_reasons": ["Incomplete wound care docs", "Missing vital signs trend"],
    },
    "pharmacy": {
        "name": "Pharmacy Department",
        "pending_nocs": 22,
        "avg_response_time_hours": 3.8,
        "approval_rate": 0.85,
        "blockers": [
            "Waiting for Nursing final assessment to confirm medication list",
            "Controlled substance reconciliation requires manual pharmacist sign-off",
            "Insurance formulary checks take 45 min average",
        ],
        "capacity": {"current_staff": 2, "max_staff": 3, "utilization": 0.67},
        "rejection_reasons": ["Drug interaction flagged", "Insurance formulary mismatch"],
    },
    "lab": {
        "name": "Laboratory",
        "pending_nocs": 8,
        "avg_response_time_hours": 1.5,
        "approval_rate": 0.97,
        "blockers": [
            "Pending test results for 3 patients (blood work)",
            "STAT orders from ED monopolizing lab capacity",
        ],
        "capacity": {"current_staff": 3, "max_staff": 4, "utilization": 0.75},
        "rejection_reasons": ["Pending lab results", "Abnormal values needing physician review"],
    },
    "billing": {
        "name": "Billing & Insurance",
        "pending_nocs": 19,
        "avg_response_time_hours": 4.2,
        "approval_rate": 0.78,
        "blockers": [
            "Insurance pre-authorization delays (average 2.5 hours)",
            "Claim coding errors requiring re-submission (12% rate)",
            "Missing documentation from clinical departments",
        ],
        "capacity": {"current_staff": 3, "max_staff": 5, "utilization": 0.60},
        "rejection_reasons": ["Pre-auth not obtained", "Incorrect ICD codes", "Missing supporting docs"],
    },
    "admin": {
        "name": "Hospital Administration",
        "pending_nocs": 5,
        "avg_response_time_hours": 1.0,
        "approval_rate": 0.99,
        "blockers": ["Dependent on all other department NOCs before final sign-off"],
        "capacity": {"current_staff": 2, "max_staff": 3, "utilization": 0.67},
        "rejection_reasons": ["Incomplete department clearances"],
    },
}

PIPELINE_DATA = {
    "claim_pipeline": {
        "stages": ["Patient intake", "Data extraction", "Template selection", "Field population", "Validation", "Submission"],
        "bottleneck": "Data extraction — avg 45 min per patient, all manual",
        "error_hotspots": [
            "Template selection: 40% require manual intervention",
            "Validation: 12% fail first attempt due to missing fields",
        ],
        "throughput": "15 claims/hour (target: 40)",
        "improvement_areas": ["Auto-extract from EHR", "ML-based template matching", "Real-time field validation"],
    },
    "noc_pipeline": {
        "current_flow": "Sequential: Nursing -> Pharmacy -> Lab -> Billing -> Admin",
        "avg_cycle_time_hours": 3.5,
        "bottleneck_dept": "Pharmacy (avg 3.8 hours response)",
        "dependencies": {
            "nursing": ["pharmacy"],
            "pharmacy": ["nursing"],
            "lab": [],
            "billing": ["lab"],
            "admin": ["nursing", "pharmacy", "lab", "billing"],
        },
        "circular_dependency_detected": True,
        "independent_nocs": ["lab"],
    },
    "discharge_flow": {
        "stages": ["Physician order", "NOC collection", "Insurance claim", "Final clearance", "Patient education", "Physical discharge"],
        "avg_total_time_hours": 8.5,
        "target_time_hours": 3.0,
        "main_delays": ["NOC collection (3.5h)", "Insurance claim (2.5h)", "Documentation gaps (1.5h)"],
        "patient_satisfaction": 3.2,
        "readmission_rate_pct": 8,
    },
}

CONFLICT_DATA = {
    "nursing_pharmacy_deadlock": {
        "type": "circular_dependency",
        "departments": ["nursing", "pharmacy"],
        "description": "Nursing waits for Pharmacy medication reconciliation; Pharmacy waits for Nursing final assessment. 8 patients deadlocked.",
        "affected_patients": 8,
        "avg_delay_hours": 6.5,
        "severity": "critical",
    },
    "lab_billing_bottleneck": {
        "type": "sequential_bottleneck",
        "departments": ["lab", "billing"],
        "description": "Billing cannot process claims until Lab confirms results are final. Lab has 4-hour backlog. 11 patients impacted.",
        "affected_patients": 11,
        "avg_delay_hours": 4.0,
        "severity": "high",
    },
    "admin_cascade": {
        "type": "cascade_failure",
        "departments": ["admin"],
        "description": "Admin NOC is last — any upstream delay cascades. 5 patients waiting 8+ hours for Admin sign-off.",
        "affected_patients": 5,
        "avg_delay_hours": 8.0,
        "severity": "high",
    },
}

ARCHITECTURE_DATA = {
    "current": {
        "type": "monolith",
        "hospitals": 1,
        "daily_discharges": 85,
        "peak_concurrent": 120,
        "database": "Single PostgreSQL instance",
        "deployment": "Single VM on AWS",
        "api_standard": "Custom REST API (no industry standard)",
        "compliance": "HIPAA compliant for single hospital only",
        "monitoring": "Basic CloudWatch logs",
        "disaster_recovery": "Nightly DB backups, no hot standby",
    },
    "scaling_target": {
        "hospitals": 50,
        "daily_discharges": 4250,
        "peak_concurrent": 6000,
        "sla_latency_p99_ms": 500,
        "uptime_pct": 99.9,
        "regulatory": ["HIPAA per hospital", "State insurance regulations", "Data residency", "HITRUST certification"],
        "integration": ["HL7 FHIR R4", "12+ insurance systems", "SAML/OAuth SSO", "Real-time BI dashboards"],
    },
    "known_issues": [
        "Single DB cannot handle 50x load",
        "No multi-tenancy — patient data not isolated",
        "Swarm agents share global state — will conflict across hospitals",
        "No standardized onboarding for new hospitals",
        "Monitoring insufficient for multi-site ops",
    ],
}

# ─── Task concept checklists for grading ──────────────────────────────

TASK_CONCEPTS = {
    "easy": {
        "auto_extraction": {
            "weight": 0.18,
            "keywords": ["auto-extract", "auto extract", "extraction", "ehr", "electronic health", "medical record", "ocr", "scan", "automated data", "auto-fill", "pull data"],
            "label": "Auto-extract patient data from EHR",
        },
        "template_matching": {
            "weight": 0.18,
            "keywords": ["template", "payer-specific", "payer specific", "insurance form", "claim form", "pre-configured", "claim template", "form template"],
            "label": "Insurance-specific claim templates",
        },
        "field_validation": {
            "weight": 0.18,
            "keywords": ["validation", "validate", "real-time check", "verify field", "field check", "error check", "pre-submission", "data quality", "completeness"],
            "label": "Real-time field validation",
        },
        "parallel_processing": {
            "weight": 0.18,
            "keywords": ["parallel", "concurrent", "simultaneously", "async", "batch", "multi-thread", "parallelize", "speed up processing"],
            "label": "Parallel claim section processing",
        },
        "error_reduction": {
            "weight": 0.15,
            "keywords": ["error rate", "error reduction", "accuracy", "cross-reference", "cross reference", "verification", "reduce errors", "quality assurance"],
            "label": "Error reduction via cross-referencing",
        },
        "feedback_loop": {
            "weight": 0.13,
            "keywords": ["feedback", "learn from", "historical", "past claims", "rejection pattern", "learning", "improve over time", "adaptive", "machine learning"],
            "label": "Learning from past claim rejections",
        },
    },
    "medium": {
        "dependency_mapping": {
            "weight": 0.14,
            "keywords": ["dependency", "depend", "prerequisite", "inter-department", "relationship", "mapping", "workflow map", "process flow", "dag"],
            "label": "Map inter-department dependencies",
        },
        "timeout_handling": {
            "weight": 0.15,
            "keywords": ["timeout", "time out", "time limit", "deadline", "sla", "response time", "auto-expire", "max wait", "time bound"],
            "label": "Auto-timeout for unresponsive departments",
        },
        "escalation_protocol": {
            "weight": 0.15,
            "keywords": ["escalat", "supervisor", "override", "manual intervention", "alert", "notify", "manager", "authority", "approval chain"],
            "label": "Escalation paths for blocked NOCs",
        },
        "priority_queue": {
            "weight": 0.12,
            "keywords": ["priority", "urgent", "critical", "triage", "queue", "ranking", "severity", "fast track", "expedite"],
            "label": "Priority queue for critical discharges",
        },
        "conflict_resolution": {
            "weight": 0.15,
            "keywords": ["conflict", "deadlock", "circular", "mutual block", "resolution", "resolve", "break cycle", "mediat", "arbitrat"],
            "label": "Resolve circular department dependencies",
        },
        "parallel_noc": {
            "weight": 0.14,
            "keywords": ["parallel noc", "concurrent noc", "simultaneous", "independent noc", "non-dependent", "process together", "batch noc", "parallel department"],
            "label": "Process independent NOCs in parallel",
        },
        "status_tracking": {
            "weight": 0.15,
            "keywords": ["dashboard", "tracking", "real-time", "real time", "monitor", "visibility", "status board", "progress", "transparency", "notification"],
            "label": "Real-time NOC status tracking",
        },
    },
    "hard": {
        "microservices": {
            "weight": 0.11,
            "keywords": ["microservice", "micro-service", "service-oriented", "decompose", "decouple", "bounded context", "domain-driven", "service mesh", "api gateway", "modular"],
            "label": "Microservices architecture",
        },
        "data_isolation": {
            "weight": 0.11,
            "keywords": ["data isolation", "multi-tenant", "multi tenant", "tenant", "data partition", "schema per", "database per", "data segregat", "isolated data"],
            "label": "Multi-tenant data isolation",
        },
        "standard_api": {
            "weight": 0.10,
            "keywords": ["fhir", "hl7", "interoperab", "common api", "unified api", "api standard", "open api", "rest standard", "integration standard"],
            "label": "Healthcare interoperability standards",
        },
        "compliance": {
            "weight": 0.11,
            "keywords": ["hipaa", "compliance", "regulatory", "regulation", "privacy", "phi", "protected health", "hitrust", "audit trail", "data protection"],
            "label": "Regulatory compliance across hospitals",
        },
        "monitoring": {
            "weight": 0.10,
            "keywords": ["monitor", "observab", "alert", "logging", "metrics", "grafana", "prometheus", "apm", "tracing", "distributed tracing"],
            "label": "Centralized monitoring and alerting",
        },
        "incremental_rollout": {
            "weight": 0.10,
            "keywords": ["incremental", "phased", "rollout", "gradual", "pilot", "staged", "canary", "blue-green", "migration plan", "onboarding plan"],
            "label": "Phased rollout strategy",
        },
        "performance": {
            "weight": 0.10,
            "keywords": ["performance", "latency", "throughput", "load balance", "caching", "horizontal scal", "auto-scal", "benchmark", "stress test"],
            "label": "Performance and scaling strategy",
        },
        "disaster_recovery": {
            "weight": 0.09,
            "keywords": ["disaster", "recovery", "backup", "failover", "redundan", "high availability", "replication", "hot standby", "fault toleran"],
            "label": "Disaster recovery and HA",
        },
        "security": {
            "weight": 0.09,
            "keywords": ["security", "encrypt", "sso", "saml", "oauth", "rbac", "access control", "zero trust", "penetration", "vulnerability"],
            "label": "Security architecture",
        },
        "change_management": {
            "weight": 0.09,
            "keywords": ["training", "change management", "adoption", "onboard", "documentation", "support", "help desk", "staff training", "transition"],
            "label": "Change management and training",
        },
    },
}

TASK_DESCRIPTIONS = {
    "easy": "Optimize the insurance claim pre-filling pipeline. Investigate the swarm agents and propose improvements to reduce errors and speed up claim processing.",
    "medium": "Resolve NOC coordination deadlocks between hospital departments. Investigate inter-department conflicts, propose timeout/escalation mechanisms, and improve parallel coordination.",
    "hard": "Design a scaling architecture to expand from 1 hospital to 50. Address multi-tenancy, compliance, interoperability, monitoring, and phased rollout.",
}