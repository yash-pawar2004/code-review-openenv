from pydantic import BaseModel
from typing import Optional, Any


class Observation(BaseModel):
    code: str
    task: str
    description: str
    difficulty: str
    step: int


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
    info: dict[str, Any] = {}
