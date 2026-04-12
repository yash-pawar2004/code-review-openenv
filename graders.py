"""Statically discoverable grader entrypoints for hackathon validators.

All grading logic is self-contained here — no imports from server.environment —
so validators can import and call these functions without a running FastAPI server.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers (copied from server/environment.py so this file is self-contained)
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

    for start in range(0, len(text_tokens) - window_size + 1):
        window = " ".join(text_tokens[start : start + window_size])
        if SequenceMatcher(None, window, phrase_norm).ratio() >= threshold:
            return True
    return False


def _extract_review_text(*args: Any, **kwargs: Any) -> str:
    candidate_values: list[Any] = list(args)
    candidate_values.extend(
        [
            kwargs.get("review"),
            kwargs.get("response"),
            kwargs.get("prediction"),
            kwargs.get("answer"),
            kwargs.get("text"),
        ]
    )
    for value in candidate_values:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("review", "response", "prediction", "answer", "text"):
                field_value = value.get(key)
                if isinstance(field_value, str):
                    return field_value
    return ""


def _extract_task_payload(*args: Any, **kwargs: Any) -> Optional[dict]:
    candidates: list[Any] = list(args)
    candidates.extend([kwargs.get("task"), kwargs.get("entry"), kwargs.get("sample")])
    for value in candidates:
        if isinstance(value, dict) and ("keywords" in value or "task" in value):
            return value
    return None


def _task_terms(task_payload: Optional[dict]) -> list[str]:
    if not task_payload:
        return []
    terms: list[str] = []
    for key in ("keywords", "synonyms"):
        value = task_payload.get(key, [])
        if isinstance(value, list):
            terms.extend(str(item) for item in value)
    return terms


def clamp_task_score(score: float) -> float:
    return max(0.01, min(float(score), 0.99))


def _grade_by_concepts(
    review: str,
    concept_map: dict[str, list[str]],
    fallback_terms: list[str],
    task_payload: Optional[dict] = None,
) -> float:
    matched_concepts = 0
    for variants in concept_map.values():
        if any(_fuzzy_contains(review, variant) for variant in variants):
            matched_concepts += 1

    task_specific_match = False
    for term in _task_terms(task_payload):
        if _fuzzy_contains(review, term):
            task_specific_match = True
            break

    if matched_concepts > 0:
        confidence = matched_concepts / len(concept_map)
        if task_specific_match:
            confidence = min(1.0, confidence + 0.15)
        return clamp_task_score(0.45 + (0.5 * confidence))

    if task_specific_match:
        return clamp_task_score(0.52)

    if any(_fuzzy_contains(review, term) for term in fallback_terms):
        return clamp_task_score(0.35)

    return clamp_task_score(0.01)


# ---------------------------------------------------------------------------
# Core grading functions
# ---------------------------------------------------------------------------

def grade_security_task(*args: Any, **kwargs: Any) -> float:
    review = _extract_review_text(*args, **kwargs)
    task_payload = _extract_task_payload(*args, **kwargs)
    security_keywords = {
        "sql injection": ["sql injection", "parameterized query", "prepared statement", "sqli"],
        "command injection": ["command injection", "shell injection", "os command injection"],
        "hardcoded secret": ["hardcoded password", "hardcoded api key", "credential exposure", "embedded secret"],
        "unsafe deserialization": ["insecure deserialization", "unsafe pickle", "yaml load", "pickle loads"],
        "path traversal": ["path traversal", "directory traversal", ".."],
        "weak crypto": ["md5", "sha1", "weak hash", "insecure hashing"],
    }
    return _grade_by_concepts(
        review,
        security_keywords,
        ["security", "vulnerability", "unsafe", "attack", "risk"],
        task_payload,
    )


def grade_logic_task(*args: Any, **kwargs: Any) -> float:
    review = _extract_review_text(*args, **kwargs)
    task_payload = _extract_task_payload(*args, **kwargs)
    bug_keywords = {
        "division bug": ["division by zero", "zero division", "zerodivisionerror"],
        "mutable defaults": ["mutable default", "shared default", "default list"],
        "indexing bug": ["index error", "out of bounds", "off by one"],
        "control flow bug": ["missing return", "infinite loop", "loop never increments"],
        "scope bug": ["unboundlocalerror", "scope", "shadowed variable"],
        "resource bug": ["file descriptor leak", "unclosed file", "missing exception handling"],
        "concurrency bug": ["race condition", "data race", "thread unsafe"],
    }
    return _grade_by_concepts(review, bug_keywords, ["bug", "error", "crash", "issue", "problem"], task_payload)


def grade_style_task(*args: Any, **kwargs: Any) -> float:
    review = _extract_review_text(*args, **kwargs)
    task_payload = _extract_task_payload(*args, **kwargs)
    style_keywords = {
        "loop style": ["enumerate", "range len", "manual indexing", "inefficient loop"],
        "readability": ["unused variable", "variable naming", "readability", "verbose"],
        "boolean cleanup": ["boolean comparison", "truthy check", "redundant comparison"],
        "string/list style": ["list comprehension", "string concatenation", "use sum", "pythonic"],
    }
    return _grade_by_concepts(
        review,
        style_keywords,
        ["style", "clean", "readable", "refactor", "idiomatic"],
        task_payload,
    )


# ---------------------------------------------------------------------------
# One distinct callable per task in openenv.yaml (validators dedupe shared targets)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Lookup table used by tasks.py
# ---------------------------------------------------------------------------

DISCOVERABLE_GRADERS = {
    "code_review_style": "graders:grade_task_code_review_style",
    "code_review_logic": "graders:grade_task_code_review_logic",
    "code_review_security": "graders:grade_task_code_review_security",
    "division_by_zero": "graders:grade_task_division_by_zero",
    "mutable_default_argument": "graders:grade_task_mutable_default_argument",
    "sql_injection": "graders:grade_task_sql_injection",
}
