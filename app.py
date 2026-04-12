"""
Code Review OpenEnv - main FastAPI application.
Single-file server: all routes, models, and environment logic here.
"""
import os, random, sys, uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import FastAPI, HTTPException, Body, Header
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graders import GRADERS, run as run_grader

app = FastAPI(title="Code Review Environment", version="1.0.0")

# ---------------------------------------------------------------------------
# Dataset - 9 code snippets (3 per category)
# ---------------------------------------------------------------------------
TASKS = [
    # --- STYLE (easy) ---
    {
        "id": "style_review", "type": "style", "difficulty": "easy",
        "code": "for i in range(len(items)):\n    print(items[i])",
        "keywords": ["enumerate", "range(len", "manual indexing"],
    },
    {
        "id": "style_review", "type": "style", "difficulty": "easy",
        "code": "if is_valid == True:\n    process()",
        "keywords": ["boolean comparison", "== true", "truthy"],
    },
    {
        "id": "style_review", "type": "style", "difficulty": "easy",
        "code": "result = []\nfor x in data:\n    result.append(x * 2)",
        "keywords": ["list comprehension", "append loop"],
    },
    # --- BUG (medium) ---
    {
        "id": "bug_review", "type": "bug", "difficulty": "medium",
        "code": "def divide(a, b):\n    return a / b",
        "keywords": ["division by zero", "zero division", "zerodivisionerror"],
    },
    {
        "id": "bug_review", "type": "bug", "difficulty": "medium",
        "code": "def add_item(item, items=[]):\n    items.append(item)\n    return items",
        "keywords": ["mutable default", "shared default", "default list"],
    },
    {
        "id": "bug_review", "type": "bug", "difficulty": "medium",
        "code": "count = 0\nwhile count < 10:\n    print(count)",
        "keywords": ["infinite loop", "never increments", "count += 1"],
    },
    # --- SECURITY (hard) ---
    {
        "id": "security_review", "type": "security", "difficulty": "hard",
        "code": "query = \"SELECT * FROM users WHERE name='\" + username + \"'\"",
        "keywords": ["sql injection", "parameterized query", "prepared statement"],
    },
    {
        "id": "security_review", "type": "security", "difficulty": "hard",
        "code": "os.system('tar -czf backup.tar.gz ' + user_input)",
        "keywords": ["command injection", "shell injection", "os.system"],
    },
    {
        "id": "security_review", "type": "security", "difficulty": "hard",
        "code": "DB_PASSWORD = 'super-secret-password'",
        "keywords": ["hardcoded password", "credential", "secret"],
    },
]

STEP_INSTRUCTIONS = {
    1: "Step 1: Identify the main issue in the code.",
    2: "Step 2: Explain why this issue is problematic.",
    3: "Step 3: Suggest a concrete fix for the issue.",
}

STEP_REWARDS = {1: 0.30, 2: 0.30, 3: 0.40}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class Observation(BaseModel):
    code: str
    task_type: str
    difficulty: str
    step: int
    description: str
    history: list[str] = Field(default_factory=list)

class Action(BaseModel):
    review: str

class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any] = {}

class State(BaseModel):
    episode_id: str
    step: int
    done: bool

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
class CodeReviewEnv:
    def __init__(self):
        self.episode_id = ""
        self.step = 0
        self.done = True
        self.task: Optional[dict] = None
        self.history: list[str] = []

    def reset(self, task_id: Optional[str] = None) -> Observation:
        self.episode_id = str(uuid.uuid4())[:8]
        self.step = 0
        self.done = False
        self.history = []
        pool = [t for t in TASKS if t["id"] == task_id] if task_id else TASKS
        if not pool:
            raise ValueError(f"Unknown task_id: {task_id!r}")
        self.task = random.choice(pool)
        return self._obs()

    def step_env(self, action: Action) -> StepResult:
        if self.done or not self.task:
            raise RuntimeError("Call reset() first.")
        self.step += 1
        kws = self.task["keywords"]
        from graders import _has
        exact = any(_has(action.review, kw) for kw in kws)
        partial = any(w in action.review.lower() for w in
                      ["bug", "error", "issue", "security", "style", "problem", "fix", "vulnerability"])
        reward = STEP_REWARDS[self.step] if exact else (STEP_REWARDS[self.step] * 0.5 if partial else 0.01)
        self.history.append(action.review)
        self.done = self.step >= 3
        return StepResult(
            observation=self._obs(),
            reward=round(reward, 4),
            done=self.done,
            info={"step": self.step, "exact": exact, "partial": partial},
        )

    def _obs(self) -> Observation:
        step = min(self.step + 1, 3)
        return Observation(
            code=self.task["code"],
            task_type=self.task["type"],
            difficulty=self.task["difficulty"],
            step=step,
            description=STEP_INSTRUCTIONS[step],
            history=self.history.copy(),
        )

    def get_state(self) -> State:
        return State(episode_id=self.episode_id, step=self.step, done=self.done)

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------
_sessions: dict[str, CodeReviewEnv] = {}

def _env(session_id: Optional[str]) -> CodeReviewEnv:
    sid = (session_id or "default").strip() or "default"
    if sid not in _sessions:
        _sessions[sid] = CodeReviewEnv()
    return _sessions[sid]

# ---------------------------------------------------------------------------
# Request/response models for routes
# ---------------------------------------------------------------------------
class ResetRequest(BaseModel):
    task_id: Optional[str] = None

class StepRequest(BaseModel):
    review: str

class GradeRequest(BaseModel):
    task_id: str
    response: str

class GradeResponse(BaseModel):
    task_id: str
    score: float

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "env": "code_review_env"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/reset")
def reset(
    body: Optional[ResetRequest] = Body(default=None),
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
):
    env = _env(x_session_id)
    task_id = body.task_id if body else None
    try:
        obs = env.reset(task_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return obs

@app.post("/step")
def step(
    body: StepRequest,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
):
    env = _env(x_session_id)
    try:
        result = env.step_env(Action(review=body.review))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return result

@app.get("/state")
def state(x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
    return _env(x_session_id).get_state()

@app.post("/grade", response_model=GradeResponse)
def grade(body: GradeRequest):
    """
    Grader endpoint. POST {"task_id": "style_review", "response": "agent text"}
    Returns {"task_id": "...", "score": 0.0-1.0}
    Valid task_ids: style_review, bug_review, security_review
    """
    if body.task_id not in GRADERS:
        raise HTTPException(404, f"Unknown task_id: {body.task_id!r}. Valid: {list(GRADERS)}")
    score = run_grader(body.task_id, body.response)
    return GradeResponse(task_id=body.task_id, score=score)

@app.get("/tasks")
def tasks():
    """List all tasks with grader references."""
    spec = _load_spec()
    return {"tasks": spec.get("tasks", [])}

@app.get("/metadata")
def metadata():
    spec = _load_spec()
    return {
        "name": spec.get("name"),
        "version": spec.get("version"),
        "description": spec.get("description"),
        "tasks": spec.get("tasks", []),
    }

@lru_cache(maxsize=1)
def _load_spec() -> dict:
    p = Path(__file__).parent / "openenv.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else {}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)
