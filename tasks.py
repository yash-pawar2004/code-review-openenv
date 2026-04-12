"""Statically discoverable task manifest for hackathon validators."""

from __future__ import annotations

from graders import DISCOVERABLE_GRADERS


TASKS = [
    {
        "id": "code_review_style",
        "name": "code_review_style",
        "description": "Easy code review task focused on spotting Python style issues.",
        "difficulty": "easy",
        "enabled": True,
        "grader": DISCOVERABLE_GRADERS["code_review_style"],
    },
    {
        "id": "code_review_logic",
        "name": "code_review_logic",
        "description": "Medium code review task focused on logic and control-flow bugs.",
        "difficulty": "medium",
        "enabled": True,
        "grader": DISCOVERABLE_GRADERS["code_review_logic"],
    },
    {
        "id": "code_review_security",
        "name": "code_review_security",
        "description": "Hard code review task focused on security vulnerabilities.",
        "difficulty": "hard",
        "enabled": True,
        "grader": DISCOVERABLE_GRADERS["code_review_security"],
    },
    {
        "id": "division_by_zero",
        "name": "division_by_zero",
        "description": "Easy bug-finding task for division-by-zero review comments.",
        "difficulty": "easy",
        "enabled": True,
        "grader": DISCOVERABLE_GRADERS["division_by_zero"],
    },
    {
        "id": "mutable_default_argument",
        "name": "mutable_default_argument",
        "description": "Medium bug-finding task for shared mutable default arguments.",
        "difficulty": "medium",
        "enabled": True,
        "grader": DISCOVERABLE_GRADERS["mutable_default_argument"],
    },
    {
        "id": "sql_injection",
        "name": "sql_injection",
        "description": "Easy security review task for unsafe SQL string concatenation.",
        "difficulty": "easy",
        "enabled": True,
        "grader": DISCOVERABLE_GRADERS["sql_injection"],
    },
]


TASKS_WITH_GRADERS = [task for task in TASKS if task.get("grader")]
