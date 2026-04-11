import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import uvicorn

from server.environment import CodeReviewEnv, dataset_preview
from models import CodeAction, CodeObservation, CodeState, StepResult

app = FastAPI(title="Code Review Environment", version="1.0.0")
DEFAULT_SESSION_ID = "default"
sessions: dict[str, CodeReviewEnv] = {DEFAULT_SESSION_ID: CodeReviewEnv()}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class StepRequest(BaseModel):
    review: str


class ResetResponse(BaseModel):
    code: str
    task: str
    description: str
    difficulty: str
    step: int
    history: list[str] = Field(default_factory=list)
    lines_of_code: int = 0
    issue_type: str = ""
    hint_level: int = 0


class StepResponse(BaseModel):
    observation: CodeObservation
    reward: float
    done: bool
    info: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _resolve_session_id(session_header: Optional[str]) -> str:
    session_id = (session_header or DEFAULT_SESSION_ID).strip()
    return session_id or DEFAULT_SESSION_ID


def _get_session_env(session_header: Optional[str]) -> CodeReviewEnv:
    session_id = _resolve_session_id(session_header)
    if session_id not in sessions:
        sessions[session_id] = CodeReviewEnv()
    return sessions[session_id]


@app.post("/reset", response_model=ResetResponse)
def reset(x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
    env = _get_session_env(x_session_id)
    obs = env.reset()
    return obs


@app.post("/step", response_model=StepResponse)
def step(request: StepRequest, x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
    try:
        env = _get_session_env(x_session_id)
        action = CodeAction(review=request.review)
        result = env.step(action)
        return StepResponse(
            observation=result.observation,
            reward=result.reward,
            done=result.done,
            info=result.info,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=CodeState)
def state(x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
    env = _get_session_env(x_session_id)
    return env.state()


@app.get("/")
def root():
    return {"status": "ok", "service": "code_review_env"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dataset")
def dataset():
    items = dataset_preview()
    return {"items": items, "count": len(items)}


def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
