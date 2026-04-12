"""
OpenEnv grader functions for code_review_env.
Fully self-contained - stdlib only, zero external dependencies.
Each function accepts a review string and returns a float in [0.0, 1.0].
"""
from difflib import SequenceMatcher
from typing import Any


def _norm(text: str) -> str:
    out = []
    for ch in text.lower():
        out.append(ch if (ch.isalnum() or ch.isspace()) else " ")
    return " ".join("".join(out).split())


def _has(text: str, phrase: str, thresh: float = 0.85) -> bool:
    t, p = _norm(text), _norm(phrase)
    if not t or not p:
        return False
    if p in t:
        return True
    pw = p.split()
    tw = t.split()
    w = max(1, len(pw))
    if len(tw) < w:
        return SequenceMatcher(None, t, p).ratio() >= thresh
    for i in range(len(tw) - w + 1):
        if SequenceMatcher(None, " ".join(tw[i:i+w]), p).ratio() >= thresh:
            return True
    return False


def _score(review: str, keywords: list, fallbacks: list) -> float:
    hits = sum(1 for kw in keywords if _has(review, kw))
    if hits > 0:
        return max(0.01, min(0.45 + 0.5 * (hits / len(keywords)), 0.99))
    if any(_has(review, f) for f in fallbacks):
        return 0.35
    return 0.01


def _get_text(*args: Any, **kwargs: Any) -> str:
    for v in list(args) + [kwargs.get(k) for k in ("review","response","prediction","answer","text")]:
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            for k in ("review","response","prediction","answer","text"):
                if isinstance(v.get(k), str):
                    return v[k]
    return ""


def grade_style(*args: Any, **kwargs: Any) -> float:
    """Easy: spot Python style issues. Returns 0.0-1.0."""
    review = _get_text(*args, **kwargs)
    return _score(review,
        ["enumerate", "range len", "list comprehension", "unused variable",
         "boolean comparison", "truthy", "pythonic", "string join", "use sum"],
        ["style", "clean", "readable", "refactor", "idiomatic"])


def grade_bug(*args: Any, **kwargs: Any) -> float:
    """Medium: find logic bugs. Returns 0.0-1.0."""
    review = _get_text(*args, **kwargs)
    return _score(review,
        ["division by zero", "mutable default", "infinite loop", "index error",
         "missing return", "off by one", "race condition", "unboundlocalerror",
         "unclosed file", "scope"],
        ["bug", "error", "crash", "issue", "problem"])


def grade_security(*args: Any, **kwargs: Any) -> float:
    """Hard: identify security vulnerabilities. Returns 0.0-1.0."""
    review = _get_text(*args, **kwargs)
    return _score(review,
        ["sql injection", "parameterized query", "command injection",
         "hardcoded password", "hardcoded api key", "path traversal",
         "insecure deserialization", "pickle", "md5", "sha1", "weak hash"],
        ["security", "vulnerability", "unsafe", "attack", "risk"])


# Registry for /grade endpoint and tasks.py
GRADERS = {
    "style_review":    grade_style,
    "bug_review":      grade_bug,
    "security_review": grade_security,
}


def run(task_id: str, response: str) -> float:
    """Call the grader for a given task_id. Raises KeyError if unknown."""
    fn = GRADERS[task_id]
    return fn(response)
