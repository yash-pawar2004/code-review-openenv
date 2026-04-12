"""
Deterministic test suite for the Code Review Environment.

Runs without a live server - tests the environment logic directly.

Usage:
    python test_env.py
"""

import sys

sys.path.insert(0, ".")

from server.environment import DATASET, VERIFIERS, CodeReviewEnv, grade
from server.environment import grade_security_task, grade_logic_task, grade_style_task
from server.app import app
from models import CodeAction
from fastapi.testclient import TestClient


PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    msg = f"  [{status}] {name}"
    if not condition and detail:
        msg += f"\n         -> {detail}"
    print(msg)
    _results.append(bool(condition))


print("\n-- Grade function ------------------------------------------")
check("exact match step 1 -> 0.3", grade("division by zero bug", ["zero", "division"], step_number=1) == 0.3)
check("partial match step 1 -> 0.15", grade("shared state issue", ["mutable"], ["shared state"], 1) == 0.15)
check("no match step 1 -> 0.01", grade("looks fine", ["zero", "division"], step_number=1) == 0.01)
check("exact match step 3 -> 0.4", grade("check for zero before division", ["zero", "division"], step_number=3) == 0.4)
check("partial match step 3 -> 0.2", grade("shared state issue", ["mutable"], ["shared state"], 3) == 0.2)
check(
    "fuzzy/synonym matching gives non-zero credit",
    grade("This has zero division risk", ["division by zero"], ["zero division"], 1) > 0.0,
)


print("\n-- Task Graders --------------------------------------------")
security_synonym_score = grade_security_task("Use prepared statements to prevent SQLi attacks.")
logic_synonym_score = grade_logic_task("This can crash due to a mutable default list being reused.")
style_synonym_score = grade_style_task("Prefer a comprehension here; current loop is non-idiomatic.")
check("security synonym score in range", 0.0 < security_synonym_score < 1.0, f"got {security_synonym_score}")
check("logic synonym score in range", 0.0 < logic_synonym_score < 1.0, f"got {logic_synonym_score}")
check("style synonym score in range", 0.0 < style_synonym_score < 1.0, f"got {style_synonym_score}")
check(
    "grader fallback score in range",
    0.0 < grade_security_task("completely unrelated response") < 1.0,
)


print("\n-- Verifiers ------------------------------------------------")
check("division_by_zero verifier passes", VERIFIERS["division_by_zero"]() is True)
check("mutable_default_argument verifier passes", VERIFIERS["mutable_default_argument"]() is True)
check("index_out_of_bounds verifier passes", VERIFIERS["index_out_of_bounds"]() is True)
check("unbound_local_scope verifier passes", VERIFIERS["unbound_local_scope"]() is True)


print("\n-- Dataset --------------------------------------------------")
check("dataset has at least 40 entries", len(DATASET) >= 40)
task_counts = {task: sum(1 for entry in DATASET if entry["task"] == task) for task in ("style", "bug", "security")}
check("style has at least 10 entries", task_counts["style"] >= 10, f"got {task_counts['style']}")
check("bug has at least 10 entries", task_counts["bug"] >= 10, f"got {task_counts['bug']}")
check("security has at least 10 entries", task_counts["security"] >= 10, f"got {task_counts['security']}")

valid_difficulties = {"easy", "medium", "hard"}
for entry in DATASET:
    for field in ("task", "difficulty", "code", "description", "keywords"):
        check(f"{entry['task']} entry has '{field}'", field in entry and bool(entry[field]), f"missing {field}")
    check(
        f"{entry['task']} difficulty is valid",
        entry["difficulty"] in valid_difficulties,
        f"got {entry['difficulty']}",
    )
    if "verifier" in entry:
        check(f"{entry['task']} verifier is registered", entry["verifier"] in VERIFIERS)


print("\n-- Grader Range --------------------------------------------")
for entry in DATASET:
    review = " ".join(entry["keywords"][:2])
    if entry["task"] == "security":
        score = grade_security_task(review, entry)
    elif entry["task"] == "bug":
        score = grade_logic_task(review, entry)
    else:
        score = grade_style_task(review, entry)
    check(f"{entry['task']} score in (0,1)", 0.0 < score < 1.0, f"got {score}")


print("\n-- Multi-step lifecycle ------------------------------------")
import random

target = next(item for item in DATASET if item.get("verifier") == "division_by_zero")
original_choice = random.choice
random.choice = lambda _: target

env = CodeReviewEnv()
obs = env.reset()
check("reset sets observation step to 1", obs.step == 1, f"got {obs.step}")
check("state step_count is 0 after reset", env.state().step_count == 0, f"got {env.state().step_count}")

r1 = env.step(CodeAction(review="There is a division by zero bug"))
check("step 1 reward is 0.3", r1.reward == 0.3, f"got {r1.reward}")
check("step 1 done is False", r1.done is False)
check("next observation step is 2", r1.observation.step == 2, f"got {r1.observation.step}")
check("step 1 info reason", r1.info.get("reason") == "exact_match", f"got {r1.info.get('reason')}")
check("step 1 info verifier true", r1.info.get("verifier") is True, f"got {r1.info.get('verifier')}")

r2 = env.step(CodeAction(review="If b is zero it crashes at runtime"))
check("step 2 reward is 0.3", r2.reward == 0.3, f"got {r2.reward}")
check("step 2 done is False", r2.done is False)
check("next observation step is 3", r2.observation.step == 3, f"got {r2.observation.step}")

r3 = env.step(CodeAction(review="Add a check for zero before division"))
check("step 3 reward is 0.4", r3.reward == 0.4, f"got {r3.reward}")
check("step 3 done is True", r3.done is True)
check("state step_count is 3 at episode end", env.state().step_count == 3, f"got {env.state().step_count}")

try:
    env.step(CodeAction(review="extra step"))
    check("step after done raises RuntimeError", False, "no exception raised")
except RuntimeError:
    check("step after done raises RuntimeError", True)

random.choice = original_choice

# Verifier priority test: no keyword match but verifier success still grants full step reward.
original_choice = random.choice
random.choice = lambda _: target
env_verify = CodeReviewEnv()
env_verify.reset()
rv = env_verify.step(CodeAction(review="Completely unrelated response text"))
check("verifier can grant reward without keyword match", rv.reward == 0.3, f"got {rv.reward}")
check("verifier priority reason is no_match", rv.info.get("reason") == "no_match", f"got {rv.info.get('reason')}")
check("verifier priority flag is true", rv.info.get("verifier") is True, f"got {rv.info.get('verifier')}")
random.choice = original_choice


print("\n-- Session isolation ---------------------------------------")
client = TestClient(app)
session_a = "session-a"
session_b = "session-b"

ra = client.post("/reset", headers={"X-Session-Id": session_a})
rb = client.post("/reset", headers={"X-Session-Id": session_b})
check("session A reset status 200", ra.status_code == 200, f"got {ra.status_code}")
check("session B reset status 200", rb.status_code == 200, f"got {rb.status_code}")

sa0 = client.get("/state", headers={"X-Session-Id": session_a}).json()
sb0 = client.get("/state", headers={"X-Session-Id": session_b}).json()
check("session A starts at step_count 0", sa0.get("step_count") == 0, f"got {sa0}")
check("session B starts at step_count 0", sb0.get("step_count") == 0, f"got {sb0}")

step_a = client.post("/step", headers={"X-Session-Id": session_a}, json={"review": "there is an issue"})
check("session A step status 200", step_a.status_code == 200, f"got {step_a.status_code}")

sa1 = client.get("/state", headers={"X-Session-Id": session_a}).json()
sb1 = client.get("/state", headers={"X-Session-Id": session_b}).json()
check("session A increments independently", sa1.get("step_count") == 1, f"got {sa1}")
check("session B remains isolated", sb1.get("step_count") == 0, f"got {sb1}")

default_reset = client.post("/reset")
default_state = client.get("/state").json()
check("default session reset status 200", default_reset.status_code == 200, f"got {default_reset.status_code}")
check("default session state available", "step_count" in default_state, f"got {default_state}")

dataset_resp = client.get("/dataset")
dataset_json = dataset_resp.json()
check("dataset endpoint status 200", dataset_resp.status_code == 200, f"got {dataset_resp.status_code}")
check("dataset endpoint count >= 40", dataset_json.get("count", 0) >= 40, f"got {dataset_json.get('count')}")


print("\n-- Summary --------------------------------------------------")
passed = sum(_results)
total = len(_results)
print(f"  Results: {passed}/{total} passed", end="")
if passed == total:
    print("  PASS All tests passed")
else:
    print("  FAIL")
    sys.exit(1)
