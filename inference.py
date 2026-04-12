"""
OpenEnv-compliant inference runner for CodeReviewEnv.

Stdout is intentionally restricted to:
[START], [STEP], [END]
"""

import os
import sys
from collections import defaultdict
from openai import OpenAI

from client import CodeReviewClient

TASK_NAME = "code_review"
ENV_NAME = "code_review_env"
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_TOKEN = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
BENCHMARK_MODE = os.getenv("BENCHMARK_MODE", "false").lower() == "true"

SYSTEM_PROMPT = (
    "You are an expert code reviewer. "
    "Answer concisely and only for the current step."
)


def clamp_task_score(score: float) -> float:
    return max(0.01, min(float(score), 0.99))


def _sanitize(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ").strip()


def _as_observation_dict(obs: object) -> dict:
    if isinstance(obs, dict):
        return obs
    if hasattr(obs, "model_dump"):
        return obs.model_dump()
    if hasattr(obs, "dict"):
        return obs.dict()
    raise TypeError("Observation payload is not dict-like")


def build_user_message(obs: dict) -> str:
    step_number = obs.get("step", 1)
    return (
        "You are performing a code review.\n\n"
        f"Task Type: {obs['task']}\n"
        f"Difficulty: {obs['difficulty']}\n\n"
        "Code to review:\n"
        f"{obs['code']}\n\n"
        "Current Review Phase:\n"
        f"Step {step_number} of 3\n\n"
        "Instructions:\n\n"
        "Step 1 -> Identify the main issue in the code.\n"
        "Describe what the problem is.\n\n"
        "Step 2 -> Explain why this issue is problematic.\n"
        "Explain what could go wrong.\n\n"
        "Step 3 -> Suggest a fix for the issue.\n"
        "Explain how the code should be corrected.\n\n"
        "Return a short review (1-3 sentences).\n\n"
        "Only perform the task for the current step."
    )


def run_inference() -> float:
    print(f"[START] task={TASK_NAME} env={ENV_NAME} model={MODEL_NAME}")

    rewards: list[float] = []
    done = False
    step_no = 0
    had_error = False
    obs: dict = {}
    failure_by_task = defaultdict(int)
    failure_by_difficulty = defaultdict(int)

    try:
        env_client = CodeReviewClient(base_url=ENV_URL)
        obs = _as_observation_dict(env_client.reset())
        obs.setdefault("step", 1)
    except Exception as exc:
        error = _sanitize(str(exc)) or "environment_init_failed"
        print(
            f"[STEP] step=1 action=null reward=0.00 done=true error={error}"
        )
        init_score = clamp_task_score(0.0)
        print(f"[END] success=false steps=1 score={init_score:.2f} rewards=0.00")
        return init_score

    openai_client = None
    openai_init_error = "null"
    try:
        openai_client = OpenAI(api_key=API_TOKEN, base_url=API_BASE_URL)
    except Exception as exc:
        openai_init_error = _sanitize(str(exc))

    while not done:
        step_no += 1
        action = ""
        reward = 0.0
        error = "null"
        step_done = False
        current_task = str(obs.get("task", "unknown"))
        current_difficulty = str(obs.get("difficulty", "unknown"))

        if openai_client is None:
            error = openai_init_error
            step_done = True
            had_error = True
        else:
            try:
                response = openai_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_user_message(obs)},
                    ],
                    max_tokens=120,
                    temperature=0.0,
                )
                action = response.choices[0].message.content.strip()
            except Exception as exc:
                error = _sanitize(str(exc))
                step_done = True
                had_error = True

        if error == "null":
            try:
                result = env_client.step(action)
                reward = float(result["reward"])
                step_done = bool(result["done"])
                if not step_done and result.get("observation"):
                    obs = _as_observation_dict(result["observation"])
                    obs.setdefault("step", step_no + 1)
            except Exception as exc:
                error = _sanitize(str(exc))
                step_done = True
                had_error = True

        action_out = _sanitize(action) if action.strip() else "null"
        done_out = str(step_done).lower()
        print(
            f"[STEP] step={step_no} action={action_out} reward={reward:.2f} "
            f"done={done_out} error={error}"
        )

        if reward == 0.0 and step_done:
            failure_by_task[current_task] += 1
            failure_by_difficulty[current_difficulty] += 1

        rewards.append(reward)
        done = step_done

    total_reward = sum(rewards)
    score = clamp_task_score(total_reward)
    success = not had_error
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(
        f"[END] success={str(success).lower()} steps={len(rewards)} "
        f"score={score:.2f} rewards={rewards_str}"
    )

    if BENCHMARK_MODE:
        print(file=sys.stderr)
        print("Failure Analysis", file=sys.stderr)
        print("---------------", file=sys.stderr)
        for task in sorted(failure_by_task):
            print(f"{task:10s} : {failure_by_task[task]}", file=sys.stderr)

        print(file=sys.stderr)
        print("Difficulty Failures", file=sys.stderr)
        print("-------------------", file=sys.stderr)
        for diff in sorted(failure_by_difficulty):
            print(f"{diff:10s} : {failure_by_difficulty[diff]}", file=sys.stderr)

    return score


if __name__ == "__main__":
    run_inference()
