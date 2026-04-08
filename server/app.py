import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from server.environment import CodeReviewEnv
from models import CodeAction, CodeObservation, CodeState, StepResult

app = FastAPI(title="Code Review Environment", version="1.0.0")
env = CodeReviewEnv()


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


class StepResponse(BaseModel):
    observation: CodeObservation
    reward: float
    done: bool
    info: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/reset", response_model=ResetResponse)
def reset():
    obs = env.reset()
    return obs


@app.post("/step", response_model=StepResponse)
def step(request: StepRequest):
    try:
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
def state():
    return env.state()


@app.get("/")
def root():
    return {"status": "ok", "service": "code_review_env"}


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
