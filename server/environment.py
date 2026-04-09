"""Core environment with sophisticated reward shaping, task-specific grading, and rich state."""
from typing import Dict, Any, Set, List
from models import (
    EasemydischargeAction, EasemydischargeObservation,
    EasemydischargeResult, ActionType,
)
from .data import (
    SWARM_STATUS, DEPARTMENTS, PIPELINE_DATA,
    CONFLICT_DATA, ARCHITECTURE_DATA, TASK_CONCEPTS, TASK_DESCRIPTIONS,
)

VALID_DEPARTMENTS = {"nursing", "pharmacy", "lab", "billing", "admin"}
VALID_COMPONENTS = {"claim_pipeline", "noc_pipeline", "discharge_flow"}


class EasemydischargePMEnv:
    def __init__(self):
        self.task = "easy"
        self.step_count = 0
        self.max_steps = 10
        self.actions_taken: List[Dict[str, Any]] = []
        # Investigation tracking
        self._queried_swarm = False
        self._queried_departments: Set[str] = set()
        self._analyzed_components: Set[str] = set()
        self._covered_concepts: Set[str] = set()
        self._has_submitted = False
        self._last_action_str = ""

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────
    def reset(self, task: str = "easy") -> EasemydischargeObservation:
        self.task = task
        self.step_count = 0
        self.max_steps = {"easy": 10, "medium": 12, "hard": 15}[task]
        self.actions_taken = []
        self._queried_swarm = False
        self._queried_departments = set()
        self._analyzed_components = set()
        self._covered_concepts = set()
        self._has_submitted = False
        self._last_action_str = ""

        desc = TASK_DESCRIPTIONS.get(task, "")
        msg = (
            f"You are the Product Manager at easemydischarge.\n"
            f"Task ({task.upper()}): {desc}\n"
            f"Available departments: {', '.join(sorted(VALID_DEPARTMENTS))}\n"
            f"Available components to analyze: {', '.join(sorted(VALID_COMPONENTS))}\n"
            f"Investigate first, then propose improvements, then submit a roadmap."
        )
        return self._build_obs(msg, {})

    def step(self, action: EasemydischargeAction) -> EasemydischargeResult:
        self.step_count += 1
        reward = self._compute_reward(action)
        data = self._process_action(action)
        self._record_action(action)

        done = (
            self.step_count >= self.max_steps
            or action.action_type == ActionType.SUBMIT_ROADMAP
        )

        info: Dict[str, Any] = {}
        if done:
            info["final_score"] = self._compute_final_score()
            info["task"] = self.task
            info["concept_coverage"] = list(self._covered_concepts)

        msg = self._build_feedback(action, reward, done)
        obs = self._build_obs(msg, data)
        return EasemydischargeResult(
            observation=obs,
            reward=round(reward, 2),
            done=done,
            info=info,
        )

    def state(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "step": self.step_count,
            "max_steps": self.max_steps,
            "concepts_covered": list(self._covered_concepts),
            "departments_queried": list(self._queried_departments),
            "queried_swarm": self._queried_swarm,
        }

    # ──────────────────────────────────────────────
    # Action processing — returns data payload
    # ──────────────────────────────────────────────
    def _process_action(self, action: EasemydischargeAction) -> Dict[str, Any]:
        if action.action_type == ActionType.QUERY_SWARM:
            self._queried_swarm = True
            return {"swarm_agents": SWARM_STATUS}

        if action.action_type == ActionType.QUERY_DEPARTMENT:
            dept = (action.department or "").lower().strip()
            if dept in VALID_DEPARTMENTS:
                self._queried_departments.add(dept)
                result: Dict[str, Any] = {"department": DEPARTMENTS[dept]}
                if self.task in ("medium", "hard"):
                    conflicts = {
                        k: v for k, v in CONFLICT_DATA.items()
                        if dept in v["departments"]
                    }
                    if conflicts:
                        result["active_conflicts"] = conflicts
                return result
            return {"error": f"Unknown department '{dept}'. Valid: {sorted(VALID_DEPARTMENTS)}"}

        if action.action_type == ActionType.ANALYZE:
            comp = (action.component or "").lower().strip()
            if comp in VALID_COMPONENTS:
                self._analyzed_components.add(comp)
                result = {"analysis": PIPELINE_DATA[comp]}
                if self.task == "hard" and comp == "discharge_flow":
                    result["architecture"] = ARCHITECTURE_DATA
                return result
            return {"error": f"Unknown component '{comp}'. Valid: {sorted(VALID_COMPONENTS)}"}

        if action.action_type == ActionType.PROPOSE_FEATURE:
            text = (action.feature_description or "").lower()
            new_concepts = self._match_concepts(text)
            self._covered_concepts.update(new_concepts)
            return {
                "new_concepts_matched": list(new_concepts),
                "total_concepts_covered": list(self._covered_concepts),
                "coverage_pct": round(self._concept_coverage_ratio() * 100, 1),
            }

        if action.action_type == ActionType.SUBMIT_ROADMAP:
            self._has_submitted = True
            # Also check roadmap content for concepts
            if action.roadmap:
                text = str(action.roadmap).lower()
                new_concepts = self._match_concepts(text)
                self._covered_concepts.update(new_concepts)
            return {"submitted": True, "final_coverage_pct": round(self._concept_coverage_ratio() * 100, 1)}

        return {}

    # ──────────────────────────────────────────────
    # Reward computation
    # ──────────────────────────────────────────────
    def _compute_reward(self, action: EasemydischargeAction) -> float:
        action_str = self._action_to_str(action)
        is_repeat = action_str == self._last_action_str

        base = 0.0

        if action.action_type == ActionType.QUERY_SWARM:
            base = 0.30 if not self._queried_swarm else 0.05

        elif action.action_type == ActionType.QUERY_DEPARTMENT:
            dept = (action.department or "").lower().strip()
            if dept in VALID_DEPARTMENTS and dept not in self._queried_departments:
                base = 0.25
            else:
                base = 0.05

        elif action.action_type == ActionType.ANALYZE:
            comp = (action.component or "").lower().strip()
            if comp in VALID_COMPONENTS and comp not in self._analyzed_components:
                base = 0.30
            else:
                base = 0.08

        elif action.action_type == ActionType.PROPOSE_FEATURE:
            text = (action.feature_description or "").lower()
            new_concepts = self._match_concepts(text)
            if new_concepts:
                concept_weights = self._get_concept_weights(new_concepts)
                base = 0.15 + min(concept_weights, 0.55)
            else:
                base = 0.10
            # Penalty for proposing without investigating
            if not self._queried_swarm and len(self._queried_departments) == 0:
                base *= 0.5

        elif action.action_type == ActionType.SUBMIT_ROADMAP:
            coverage = self._concept_coverage_ratio()
            base = 0.20 + (coverage * 0.60)

        # Exact repetition penalty
        if is_repeat:
            base *= 0.25

        return min(max(base, 0.01), 0.99)

    # ──────────────────────────────────────────────
    # Final score (holistic trajectory evaluation)
    # ──────────────────────────────────────────────
    def _compute_final_score(self) -> float:
        coverage = self._concept_coverage_ratio()
        investigation = self._investigation_score()
        strategy = self._strategy_score()
        completeness = 1.0 if self._has_submitted else 0.5

        score = (
            coverage * 0.40
            + investigation * 0.25
            + strategy * 0.20
            + completeness * 0.15
        )
        return round(min(max(score, 0.01), 0.99), 3)

    def _investigation_score(self) -> float:
        pts, total = 0.0, 3.0
        if self._queried_swarm:
            pts += 1.0
        required_depts = {"easy": 1, "medium": 3, "hard": 5}[self.task]
        pts += min(len(self._queried_departments) / required_depts, 1.0)
        if self._analyzed_components:
            pts += 1.0
        return pts / total

    def _strategy_score(self) -> float:
        if not self.actions_taken:
            return 0.0
        first_investigate = first_propose = None
        for i, a in enumerate(self.actions_taken):
            atype = a["action_type"]
            if atype in ("query_swarm", "query_department", "analyze") and first_investigate is None:
                first_investigate = i
            if atype in ("propose_feature", "submit_roadmap") and first_propose is None:
                first_propose = i

        # Order score (0.4)
        if first_investigate is not None and first_propose is not None:
            order = 0.4 if first_investigate < first_propose else 0.1
        elif first_investigate is not None:
            order = 0.3
        else:
            order = 0.0

        # Diversity (0.3)
        types_used = {a["action_type"] for a in self.actions_taken}
        diversity = min(len(types_used) / 4.0, 1.0) * 0.3

        # Low repetition (0.3)
        strs = [str(a) for a in self.actions_taken]
        unique_ratio = len(set(strs)) / len(strs)
        repetition = unique_ratio * 0.3

        return order + diversity + repetition

    # ──────────────────────────────────────────────
    # Concept matching helpers
    # ──────────────────────────────────────────────
    def _match_concepts(self, text: str) -> Set[str]:
        concepts = TASK_CONCEPTS.get(self.task, {})
        matched: Set[str] = set()
        for cid, cdef in concepts.items():
            if cid in self._covered_concepts:
                continue
            if any(kw in text for kw in cdef["keywords"]):
                matched.add(cid)
        return matched

    def _get_concept_weights(self, concept_ids: Set[str]) -> float:
        concepts = TASK_CONCEPTS.get(self.task, {})
        return sum(concepts[c]["weight"] for c in concept_ids if c in concepts)

    def _concept_coverage_ratio(self) -> float:
        total = len(TASK_CONCEPTS.get(self.task, {}))
        if total == 0:
            return 0.0
        return len(self._covered_concepts) / total

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────
    def _record_action(self, action: EasemydischargeAction) -> None:
        self._last_action_str = self._action_to_str(action)
        self.actions_taken.append({
            "step": self.step_count,
            "action_type": action.action_type.value,
            "detail": action.department or action.component or (action.feature_description or "")[:80],
        })

    @staticmethod
    def _action_to_str(action: EasemydischargeAction) -> str:
        return f"{action.action_type.value}|{action.department}|{action.component}|{(action.feature_description or '')[:100]}"

    def _build_obs(self, message: str, data: Dict[str, Any]) -> EasemydischargeObservation:
        concepts = TASK_CONCEPTS.get(self.task, {})
        covered_labels = [concepts[c]["label"] for c in self._covered_concepts if c in concepts]
        return EasemydischargeObservation(
            task=self.task,
            step=self.step_count,
            max_steps=self.max_steps,
            message=message,
            data=data,
            concepts_covered=covered_labels,
            investigation_summary={
                "swarm_queried": self._queried_swarm,
                "departments_queried": sorted(self._queried_departments),
                "components_analyzed": sorted(self._analyzed_components),
                "concept_coverage_pct": round(self._concept_coverage_ratio() * 100, 1),
            },
            available_actions=[a.value for a in ActionType],
        )

    def _build_feedback(self, action: EasemydischargeAction, reward: float, done: bool) -> str:
        if done and self._has_submitted:
            score = self._compute_final_score()
            return f"Roadmap submitted. Final score: {score:.3f}. Coverage: {self._concept_coverage_ratio()*100:.0f}%."

        if done:
            score = self._compute_final_score()
            return f"Episode ended (max steps). Score: {score:.3f}. Tip: submit a roadmap for bonus points."

        coverage = self._concept_coverage_ratio()
        remaining = len(TASK_CONCEPTS.get(self.task, {})) - len(self._covered_concepts)

        if reward >= 0.25:
            feedback = "Good progress."
        elif reward >= 0.10:
            feedback = "Action noted, but limited new ground covered."
        else:
            feedback = "Low value action — try a different approach."

        if not self._queried_swarm and self.step_count <= 3:
            feedback += " Consider querying the swarm to understand current issues."
        elif remaining > 0:
            feedback += f" {remaining} improvement areas still uncovered."

        return feedback