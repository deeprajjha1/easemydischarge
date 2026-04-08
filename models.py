from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    QUERY_SWARM = "query_swarm"
    QUERY_DEPARTMENT = "query_department"
    ANALYZE = "analyze"
    PROPOSE_FEATURE = "propose_feature"
    SUBMIT_ROADMAP = "submit_roadmap"


class EasemydischargeAction(BaseModel):
    action_type: ActionType
    department: Optional[str] = None
    component: Optional[str] = None
    feature_description: Optional[str] = None
    roadmap: Optional[Dict[str, Any]] = None


class EasemydischargeObservation(BaseModel):
    task: str
    step: int
    max_steps: int
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    concepts_covered: List[str] = Field(default_factory=list)
    investigation_summary: Dict[str, Any] = Field(default_factory=dict)
    available_actions: List[str] = Field(default_factory=list)


class EasemydischargeResult(BaseModel):
    observation: EasemydischargeObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)