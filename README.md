---
title: Code Review Env
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Code Review Environment (OpenEnv)

## Overview

This project implements a **Code Review Environment** compatible with the **OpenEnv specification**.

The environment simulates a real-world developer workflow where an AI agent reviews code snippets and identifies issues such as **style problems, bugs, or security vulnerabilities**.

Each episode presents the agent with a **code snippet containing an issue**. The agent must respond with a **review comment describing the problem**. The environment evaluates the response using **deterministic keyword-and-concept grading** and returns a **reward between 0.0 and 1.0**.

---

## Motivation

Code review is an essential part of modern software engineering. Developers routinely analyze code to find style violations, logical bugs, security vulnerabilities, and inefficient patterns. This environment provides a simplified simulation of that workflow so that **AI agents can be evaluated on their code review abilities** in a reproducible, automated way.

---

## Environment Interaction Loop

```
Environment → Observation → Agent → Action → Environment → Reward
```

1. Environment provides a code snippet.
2. Agent produces a review comment.
3. Environment evaluates the comment with deterministic grading and optional verifier checks.
4. Reward is returned for the current phase (`step 1`, `step 2`, or `step 3`).

---

## OpenEnv Interface

| Endpoint     | Method | Description                  |
|-------------|--------|------------------------------|
| `/reset`    | POST   | Start a new episode          |
| `/step`     | POST   | Submit a review action       |
| `/state`    | GET    | Query environment metadata   |

---

## Observation Space

Each observation contains:

| Field         | Type   | Description                        |
|--------------|--------|------------------------------------|
| `code`       | string | Code snippet under review          |
| `task`       | string | Review category (`style`, `bug`, `security`) |
| `description`| string | Instructions for the agent         |
| `difficulty` | string | Difficulty label (`easy`, `medium`, `hard`) |
| `step`       | integer | Current review phase (`1`, `2`, `3`) |

Example observation:

```json
{
  "code": "for i in range(len(arr)):
    print(arr[i])",
  "task": "style",
  "description": "Identify a code style issue in this snippet.",
  "difficulty": "easy",
  "step": 1
}
```

---

## Action Space

The agent produces a review comment as a plain string:

```json
{ "review": "Use enumerate instead of range(len(arr))" }
```

The environment evaluates the comment using deterministic keyword and concept matching.

---

## Tasks

### Task 1 — Style Improvement *(Easy)*

Detect inefficient or non-idiomatic Python style.

**Example code:**
```python
for i in range(len(items)):
    print(items[i])
```

**Expected keyword:** `enumerate`

**Reward rule:** `1.0` if review contains `"enumerate"`, else `0.0`

---

### Task 2 — Bug Detection *(Medium)*

Identify potential runtime bugs.

**Example code:**
```python
def divide(a, b):
    return a / b
```

**Expected keywords:** `zero`, `division`

**Reward rule:** `1.0` if review mentions `"zero"` or `"division"`, else `0.0`

---

### Task 3 — Security Issue *(Hard)*

Detect security vulnerabilities.

**Example code:**
```python
query = "SELECT * FROM users WHERE name='" + username + "'"
```

**Expected keywords:** `sql injection`, `parameterized`, `prepared statement`

**Reward rule:** `1.0` if review mentions `"sql injection"`, `"parameterized"`, or `"prepared statement"`, else `0.0`

---

## Dataset

The environment uses an internal dataset of **30 deterministic code review tasks**. During `reset()`, one task is selected at random.

```python
DATASET = [
    {"task": "style", "code": "...", "keywords": ["enumerate", "manual indexing"]},
    {"task": "bug", "code": "...", "keywords": ["mutable", "default"]},
    {"task": "security", "code": "...", "keywords": ["sql injection", "parameterized"]},
]
```

### Expanded Coverage

- **10 style tasks** covering inefficient loops, unused variables, weak naming, redundant boolean comparisons, unnecessary list conversions, debug print statements, redundant conditions, manual indexing, poor iteration patterns, and inefficient string concatenation.
- **10 bug tasks** covering division by zero, mutable default arguments, index errors, infinite loops, incorrect `None` comparison, missing returns, scope mistakes, shadowed variables, bad loop termination, and collection mutation during iteration.
- **10 security tasks** covering SQL injection, command injection, unsafe `eval()`, hardcoded passwords, hardcoded API keys, path traversal, unsafe file handling, insecure deserialization, weak cryptography, and unsafe shell execution.
- Every task is labeled with a difficulty of `easy`, `medium`, or `hard` so evaluation can be broken down like a benchmark.

Each task includes multiple keywords, and some include optional synonyms, so grading remains deterministic while being more robust to natural phrasing variations.

---

## Reward Function

```python
step_1_reward = 0.3  # identify issue
step_2_reward = 0.3  # explain impact
step_3_reward = 0.4  # suggest fix
```

The episode ends after step 3 (`done = True`).

### Improved Grading

- Exact keyword match -> full step reward (`0.3`, `0.3`, `0.4`)
- Synonym match -> partial step reward (`0.15`, `0.15`, `0.2`)
- No match -> `0.0`

This keeps grading deterministic while reducing false negatives for correct explanations that use slightly different wording.

## Verifiable Reward System

Some bug tasks include a controlled `verifier` field that runs safe local checks to validate expected runtime behavior.

Examples:

- `division_by_zero` confirms `ZeroDivisionError` is reproducible
- `mutable_default_argument` confirms shared list state across calls
- `index_out_of_bounds` confirms `IndexError` behavior

Verifier checks are deterministic and sandboxed:

- no arbitrary user code execution
- no filesystem or network access
- all checks run in local `try/except` guards

## Benchmark Evaluation

The environment includes difficulty labels for every task:

- `easy` for obvious review findings such as division by zero, unused variables, debug prints, or hardcoded passwords
- `medium` for issues that need more careful reasoning such as mutable defaults, unsafe `eval()`, or inefficient string building
- `hard` for more subtle or dangerous issues such as path traversal, command injection, insecure deserialization, or mutation during iteration

During inference runs, rewards are grouped by difficulty and averaged independently:

- Easy accuracy = average reward over all `easy` episodes
- Medium accuracy = average reward over all `medium` episodes
- Hard accuracy = average reward over all `hard` episodes
- Style accuracy = average reward over all `style` episodes
- Bug accuracy = average reward over all `bug` episodes
- Security accuracy = average reward over all `security` episodes
- Overall score = average reward across every episode

Example result table:

| Metric | Score |
|--------|-------|
| Easy accuracy | 0.90 |
| Medium accuracy | 0.65 |
| Hard accuracy | 0.40 |
| Style accuracy | 0.72 |
| Bug accuracy | 0.66 |
| Security accuracy | 0.51 |
| Overall score | 0.63 |

## Benchmark Results Format

Inference runs report:

- performance by difficulty
- performance by task type
- overall score

Example benchmark output:

```text
CodeReviewEnv Benchmark

Model: gpt-4o-mini
Episodes: 30

Difficulty Scores

Easy     : 0.90
Medium   : 0.65
Hard     : 0.40

Task Scores

Style    : 0.72
Bug      : 0.66
Security : 0.51

Overall

Score    : 0.63
```

---

## Project Structure

```
code_review_env/
├── Dockerfile
├── requirements.txt
├── README.md
├── inference.py
├── models.py
├── client.py
├── openenv.yaml
├── test_env.py
└── server/
    ├── environment.py
    └── app.py
```

---

## Setup & Local Usage

### Install dependencies

```bash
pip install fastapi uvicorn pydantic requests openai
```

### Run the server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Test with the Python client

```python
from client import CodeReviewClient

client = CodeReviewClient("http://localhost:7860")
obs = client.reset()
print(obs)
result = client.step("This code is vulnerable to SQL injection. Use parameterized queries.")
print(result)
```

---

## Docker

### Build

```bash
docker build -t code-review-env .
```

### Run

```bash
docker run -p 7860:7860 code-review-env
```

---

## Baseline Inference Script

Run an LLM baseline against the environment:

```bash
export OPENAI_API_KEY=sk-...
export MODEL_NAME=gpt-4o-mini
export NUM_EPISODES=30
python inference.py
```

Example output:

```text
[START] task=code_review env=code_review_env model=gpt-4o-mini
[STEP] episode=1 step=1 difficulty=easy task=bug action='Division by zero bug' reward=0.30 reason=exact_match verifier=true done=false error=null
[STEP] episode=1 step=2 difficulty=easy task=bug action='It crashes when b is zero' reward=0.30 reason=exact_match verifier=true done=false error=null
[STEP] episode=1 step=3 difficulty=easy task=bug action='Add a zero check before division' reward=0.40 reason=exact_match verifier=true done=true error=null
CodeReviewEnv Benchmark

Model: gpt-4o-mini
Episodes: 30

Difficulty Scores

Easy     : 0.90
Medium   : 0.65
Hard     : 0.40

Task Scores

Style    : 0.72
Bug      : 0.66
Security : 0.51

Overall

Score    : 0.63
[END] success=false episodes=30 score=0.83 total_reward=25.00
```

---

## Baseline Results

Baseline evaluation using `gpt-4o-mini` over 30 episodes:

| Task     | Score |
|---------|-------|
| Style    | 0.90  |
| Bug      | 0.70  |
| Security | 0.60  |
| **Overall** | **0.73** |

---

## Deployment to HuggingFace Spaces

1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **Docker** runtime.
2. Push the repository contents to the Space repo.
3. The Space will build the Docker container and expose the service.

The endpoint will be:

```
https://<username>-code-review-env.hf.space
```

API routes available:

```
POST https://<username>-code-review-env.hf.space/reset
POST https://<username>-code-review-env.hf.space/step
GET  https://<username>-code-review-env.hf.space/state
```

---

## Summary

This project provides a realistic code review simulation environment for evaluating AI agents. Key features include real-world developer task simulation, deterministic grading, an OpenEnv-compatible HTTP interface, containerized deployment, and a reproducible baseline inference script.
