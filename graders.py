"""
Statically discoverable grader entrypoints for OpenEnv validators.

This file is FULLY SELF-CONTAINED — stdlib only, zero external dependencies.
Validators can import and call any grader without pydantic/fastapi installed.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    normalized = []
    for char in text.lower():
        if char.isalnum() or char.isspace():
            normalized.append(char)
        else:
            normalized.append(" ")
    return " ".join("".join(normalized).split())


def _fuzzy_contains(text: str, phrase: str, threshold: float = 0.86) -> bool:
    text_norm = _normalize_text(text)
    phrase_norm = _normalize_text(phrase)
    if not text_norm or not phrase_norm:
        return False
    if phrase_norm in text_norm:
        return True
    text_tokens = text_norm.split()
    phrase_tokens = phrase_norm.split()
    window_size = max(1, len(phrase_tokens))
    if len(text_tokens) < window_size:
        return SequenceMatcher(None, text_norm, phrase_norm).ratio() >= threshold
    for start in range(len(text_tokens) - window_size + 1):
        window = " ".join(text_tokens[start: start + window_size])
        if SequenceMatcher(None, window, phrase_norm).ratio() >= threshold:
            return True
    return False


def _extract_review_text(*args: Any, **kwargs: Any) -> str:
    candidates: list[Any] = list(args)
    candidates += [
        kwargs.get("review"), kwargs.get("response"),
        kwargs.get("prediction"), kwargs.get("answer"), kwargs.get("text"),
    ]
    for value in candidates:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("review", "response", "prediction", "answer", "text"):
                v = value.get(key)
                if isinstance(v, str):
                    return v
    return ""


def _extract_task_payload(*args: Any, **kwargs: Any) -> Optional[dict]:
    candidates: list[Any] = list(args)
    candidates += [kwargs.get("task"), kwargs.get("entry"), kwargs.get("sample")]
    for value in candidates:
        if isinstance(value, dict) and ("keywords" in value or "task" in value):
            return value
    return None


def _task_terms(task_payload: Optional[dict]) -> list[str]:
    if not task_payload:
        return []
    terms: list[str] = []
    for key in ("keywords", "synonyms"):
        val = task_payload.get(key, [])
        if isinstance(val, list):
            terms.extend(str(i) for i in val)
    return terms


def clamp_score(score: float) -> float:
    return max(0.01, min(float(score), 0.99))


def _grade_by_concepts(
    review: str,
    concept_map: dict,
    fallback_terms: list,
    task_payload: Optional[dict] = None,
) -> float:
    matched = sum(
        1 for variants in concept_map.values()
        if any(_fuzzy_contains(review, v) for v in variants)
    )
    task_match = any(_fuzzy_contains(review, t) for t in _task_terms(task_payload))

    if matched > 0:
        confidence = matched / len(concept_map)
        if task_match:
            confidence = min(1.0, confidence + 0.15)
        return clamp_score(0.45 + 0.5 * confidence)
    if task_match:
        return clamp_score(0.52)
    if any(_fuzzy_contains(review, t) for t in fallback_terms):
        return clamp_score(0.35)
    return clamp_score(0.01)


# ---------------------------------------------------------------------------
# Core grading logic (three task categories)
# ---------------------------------------------------------------------------

def _grade_security(review: str, task_payload: Optional[dict] = None) -> float:
    return _grade_by_concepts(
        review,
        {
            "sql injection": ["sql injection", "parameterized query", "prepared statement", "sqli"],
            "command injection": ["command injection", "shell injection", "os command injection"],
            "hardcoded secret": ["hardcoded password", "hardcoded api key", "credential exposure", "embedded secret"],
            "unsafe deserialization": ["insecure deserialization", "unsafe pickle", "yaml load", "pickle loads"],
            "path traversal": ["path traversal", "directory traversal", ".."],
            "weak crypto": ["md5", "sha1", "weak hash", "insecure hashing"],
        },
        ["security", "vulnerability", "unsafe", "attack", "risk"],
        task_payload,
    )


def _grade_logic(review: str, task_payload: Optional[dict] = None) -> float:
    return _grade_by_concepts(
        review,
        {
            "division bug": ["division by zero", "zero division", "zerodivisionerror"],
            "mutable defaults": ["mutable default", "shared default", "default list"],
            "indexing bug": ["index error", "out of bounds", "off by one"],
            "control flow bug": ["missing return", "infinite loop", "loop never increments"],
            "scope bug": ["unboundlocalerror", "scope", "shadowed variable"],
            "resource bug": ["file descriptor leak", "unclosed file", "missing exception handling"],
            "concurrency bug": ["race condition", "data race", "thread unsafe"],
        },
        ["bug", "error", "crash", "issue", "problem"],
        task_payload,
    )


def _grade_style(review: str, task_payload: Optional[dict] = None) -> float:
    return _grade_by_concepts(
        review,
        {
            "loop style": ["enumerate", "range len", "manual indexing", "inefficient loop"],
            "readability": ["unused variable", "variable naming", "readability", "verbose"],
            "boolean cleanup": ["boolean comparison", "truthy check", "redundant comparison"],
            "string/list style": ["list comprehension", "string concatenation", "use sum", "pythonic"],
        },
        ["style", "clean", "readable", "refactor", "idiomatic"],
        task_payload,
    )


# ---------------------------------------------------------------------------
# One public function per task declared in openenv.yaml
# ---------------------------------------------------------------------------

def grade_task_code_review_style(*args: Any, **kwargs: Any) -> float:
    """Easy task: spot Python style issues. Score 0.0-1.0."""
    return _grade_style(_extract_review_text(*args, **kwargs), _extract_task_payload(*args, **kwargs))


def grade_task_code_review_logic(*args: Any, **kwargs: Any) -> float:
    """Medium task: find logic / control-flow bugs. Score 0.0-1.0."""
    return _grade_logic(_extract_review_text(*args, **kwargs), _extract_task_payload(*args, **kwargs))


def grade_task_code_review_security(*args: Any, **kwargs: Any) -> float:
    """Hard task: identify security vulnerabilities. Score 0.0-1.0."""
    return _grade_security(_extract_review_text(*args, **kwargs), _extract_task_payload(*args, **kwargs))


def grade_task_division_by_zero(*args: Any, **kwargs: Any) -> float:
    """Easy bug: division-by-zero detection. Score 0.0-1.0."""
    return _grade_logic(_extract_review_text(*args, **kwargs), _extract_task_payload(*args, **kwargs))


def grade_task_mutable_default_argument(*args: Any, **kwargs: Any) -> float:
    """Medium bug: shared mutable default argument. Score 0.0-1.0."""
    return _grade_logic(_extract_review_text(*args, **kwargs), _extract_task_payload(*args, **kwargs))


def grade_task_sql_injection(*args: Any, **kwargs: Any) -> float:
    """Easy security: unsafe SQL string concatenation. Score 0.0-1.0."""
    return _grade_security(_extract_review_text(*args, **kwargs), _extract_task_payload(*args, **kwargs))


# ---------------------------------------------------------------------------
# Registry — used by tasks.py and the /grade HTTP endpoint in app.py
# ---------------------------------------------------------------------------

GRADER_REGISTRY = {
    "code_review_style":        grade_task_code_review_style,
    "code_review_logic":        grade_task_code_review_logic,
    "code_review_security":     grade_task_code_review_security,
    "division_by_zero":         grade_task_division_by_zero,
    "mutable_default_argument": grade_task_mutable_default_argument,
    "sql_injection":            grade_task_sql_injection,
}

DISCOVERABLE_GRADERS = {k: f"graders:{v.__name__}" for k, v in GRADER_REGISTRY.items()}


def call_grader(task_id: str, response: str) -> float:
    """Resolve a task_id to its grader and call it. Used by the /grade HTTP endpoint."""
    fn = GRADER_REGISTRY.get(task_id)
    if fn is None:
        raise KeyError(f"Unknown task_id: {task_id!r}. Known: {list(GRADER_REGISTRY)}")
    return fn(response)
