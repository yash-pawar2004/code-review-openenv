"""Statically discoverable grader entrypoints for hackathon validators."""

from __future__ import annotations

from typing import Any

from server.environment import (
    grade_logic_task,
    grade_security_task,
    grade_style_task,
)


def grade_task_code_review_style(*args: Any, **kwargs: Any) -> float:
    return grade_style_task(*args, **kwargs)


def grade_task_code_review_logic(*args: Any, **kwargs: Any) -> float:
    return grade_logic_task(*args, **kwargs)


def grade_task_code_review_security(*args: Any, **kwargs: Any) -> float:
    return grade_security_task(*args, **kwargs)


def grade_task_division_by_zero(*args: Any, **kwargs: Any) -> float:
    return grade_logic_task(*args, **kwargs)


def grade_task_mutable_default_argument(*args: Any, **kwargs: Any) -> float:
    return grade_logic_task(*args, **kwargs)


def grade_task_sql_injection(*args: Any, **kwargs: Any) -> float:
    return grade_security_task(*args, **kwargs)


DISCOVERABLE_GRADERS = {
    "code_review_style": grade_task_code_review_style,
    "code_review_logic": grade_task_code_review_logic,
    "code_review_security": grade_task_code_review_security,
    "division_by_zero": grade_task_division_by_zero,
    "mutable_default_argument": grade_task_mutable_default_argument,
    "sql_injection": grade_task_sql_injection,
}
