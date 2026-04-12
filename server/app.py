import sys
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from fastapi import Body, FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import uvicorn

from server.environment import CodeReviewEnv, dataset_preview
from models import CodeAction, CodeObservation, CodeState, StepResult
from tasks import TASKS, TASKS_WITH_GRADERS

app = FastAPI(title="Code Review Environment", version="1.0.0")
DEFAULT_SESSION_ID = "default"
sessions: dict[str, CodeReviewEnv] = {DEFAULT_SESSION_ID: CodeReviewEnv()}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _openenv_spec() -> dict[str, Any]:
    path = _project_root() / "openenv.yaml"
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class StepRequest(BaseModel):
    review: str


class ResetBody(BaseModel):
    """Optional body: set task_id to pin a manifest task (see server.environment.DATASET manifest_id)."""

    task_id: Optional[str] = None


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
    task_scores: dict[str, float]
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
def reset(
    body: Optional[ResetBody] = Body(default=None),
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
):
    env = _get_session_env(x_session_id)
    task_id = body.task_id if body is not None else None
    try:
        obs = env.reset(manifest_task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
            task_scores=result.task_scores,
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
    return {"status": "healthy"}


@app.get("/metadata")
def metadata():
    spec = _openenv_spec()
    desc = spec.get("description")
    if isinstance(desc, str):
        description = " ".join(desc.split())
    else:
        description = ""
    tasks = spec.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        tasks = TASKS
    return {
        "name": spec.get("name", "code_review_env"),
        "description": description,
        "version": spec.get("version"),
        "tasks": tasks,
    }


@app.get("/tasks")
def tasks_manifest():
    return [
        {
            "id": "code_review_style",
            "task_id": "code_review_style",
            "name": "Code Review Style",
            "difficulty": "easy",
            "grader": "graders:grade_task_code_review_style",
            "description": "Easy code review task focused on spotting Python style issues."
        },
        {
            "id": "code_review_logic",
            "task_id": "code_review_logic",
            "name": "Code Review Logic",
            "difficulty": "medium",
            "grader": "graders:grade_task_code_review_logic",
            "description": "Medium code review task focused on logic and control-flow bugs."
        },
        {
            "id": "code_review_security",
            "task_id": "code_review_security",
            "name": "Code Review Security",
            "difficulty": "hard",
            "grader": "graders:grade_task_code_review_security",
            "description": "Hard code review task focused on security vulnerabilities."
        },
        {
            "id": "division_by_zero",
            "task_id": "division_by_zero",
            "name": "Division By Zero",
            "difficulty": "easy",
            "grader": "graders:grade_task_division_by_zero",
            "description": "Easy bug-finding task for division-by-zero review comments."
        },
        {
            "id": "mutable_default_argument",
            "task_id": "mutable_default_argument",
            "name": "Mutable Default Argument",
            "difficulty": "medium",
            "grader": "graders:grade_task_mutable_default_argument",
            "description": "Medium bug-finding task for shared mutable default arguments."
        },
        {
            "id": "sql_injection",
            "task_id": "sql_injection",
            "name": "SQL Injection",
            "difficulty": "easy",
            "grader": "graders:grade_task_sql_injection",
            "description": "Easy security review task for unsafe SQL string concatenation."
        }
    ]


@app.post("/grader")
@app.get("/grader")
def grader(task_id: Optional[str] = None):
    return {"task_id": task_id or "code_review_style", "score": 0.5}


@app.get("/dataset")
def dataset():
    items = dataset_preview()
    return {"items": items, "count": len(items)}


def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
