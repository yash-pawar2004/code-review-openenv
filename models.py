from pydantic import BaseModel, Field
from typing import Optional, Any


class Observation(BaseModel):
    code: str
    task: str
    description: str
    difficulty: str
    step: int
    history: list[str] = Field(default_factory=list)
    lines_of_code: int = 0
    issue_type: str = ""
    hint_level: int = 0


class Action(BaseModel):
    pass


class State(BaseModel):
    pass


class Reward(BaseModel):
    value: float


class CodeObservation(Observation):
    pass


class CodeAction(Action):
    review: str


class CodeState(State):
    episode_id: str
    step_count: int


class StepResult(BaseModel):
    observation: Optional[CodeObservation]
    reward: float
    done: bool
    task_scores: dict[str, float] = Field(default_factory=dict)
    info: dict[str, Any] = {}
