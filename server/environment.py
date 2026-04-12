import random
import uuid
from difflib import SequenceMatcher
from typing import Optional, Tuple, Any

from models import CodeObservation, CodeAction, CodeState, StepResult

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

DATASET = [
    {
        "task": "style",
        "difficulty": "easy",
        "code": "for i in range(len(arr)):\n    print(arr[i])",
        "description": "Identify a code style issue in this snippet.",
        "keywords": ["enumerate", "range(len", "manual indexing"],
        "synonyms": ["iteration", "loop style", "readability"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "result = []\nfor value in values:\n    result.append(str(value))",
        "description": "Identify the style issue in this data transformation.",
        "keywords": ["list comprehension", "comprehension", "append loop"],
        "synonyms": ["inefficient loop", "verbose", "style issue"],
    },
    {
        "task": "style",
        "difficulty": "easy",
        "code": "unused_total = sum(values)\nreturn len(values)",
        "description": "Identify the style issue in this function body.",
        "keywords": ["unused variable", "unused_total", "dead code"],
        "synonyms": ["cleanup", "readability", "unused"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "def process_data(d, x):\n    return d + x",
        "description": "Identify the readability issue in this function.",
        "keywords": ["variable naming", "descriptive name", "unclear name"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "if is_ready == True:\n    start_job()",
        "description": "Identify the style issue in this conditional.",
        "keywords": ["boolean comparison", "== true", "truthy"],
        "synonyms": ["style issue", "redundant", "readability"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "items = list(range(10))\nfor item in list(items):\n    print(item)",
        "description": "Identify the unnecessary operation in this loop.",
        "keywords": ["unnecessary list", "redundant list", "list conversion"],
    },
    {
        "task": "style",
        "difficulty": "easy",
        "code": "def create_user(name):\n    print('creating user', name)\n    return {'name': name}",
        "description": "Identify the code review issue in this function.",
        "keywords": ["debug print", "print statement", "logging"],
        "synonyms": ["debugging", "noise", "style issue"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "if value > 0:\n    return True\nelse:\n    return False",
        "description": "Identify the redundant pattern in this function.",
        "keywords": ["redundant condition", "return boolean", "simplify boolean"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "index = 0\nwhile index < len(users):\n    send_email(users[index])\n    index += 1",
        "description": "Identify the style issue in this iteration logic.",
        "keywords": ["iterate directly", "for loop", "manual indexing"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "message = ''\nfor part in parts:\n    message += part",
        "description": "Identify the inefficient string handling pattern.",
        "keywords": ["join", "string concatenation", "inefficient concatenation"],
        "synonyms": ["performance", "inefficient", "style issue"],
    },
    {
        "task": "bug",
        "difficulty": "easy",
        "code": "def divide(a, b):\n    return a / b",
        "description": "Identify a potential runtime bug in this function.",
        "keywords": ["zero", "division", "divide by zero"],
        "synonyms": ["runtime error", "exception", "bug"],
        "verifier": "division_by_zero",
        "grader": "server.environment:grade_logic_task",
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "def add_item(item, items=[]):\n    items.append(item)\n    return items",
        "description": "Identify the bug in this function.",
        "keywords": ["mutable", "default", "shared state"],
        "synonyms": ["bug", "unexpected state", "side effect"],
        "verifier": "mutable_default_argument",
        "grader": "server.environment:grade_logic_task",
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "def get_last(items):\n    return items[len(items)]",
        "description": "Identify the bug in this indexing logic.",
        "keywords": ["index", "out of bounds", "off by one"],
        "verifier": "index_out_of_bounds",
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "count = 0\nwhile count < 10:\n    print(count)",
        "description": "Identify the bug in this loop.",
        "keywords": ["infinite loop", "count += 1", "loop never increments"],
        "synonyms": ["never ends", "bug", "termination"],
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "if result == None:\n    handle_empty()",
        "description": "Identify the bug-prone comparison in this code.",
        "keywords": ["is none", "none comparison", "identity comparison"],
        "synonyms": ["comparison issue", "bug", "none handling"],
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "def find_user(users, target):\n    for user in users:\n        if user.id == target:\n            return user.name",
        "description": "Identify the bug in this function's control flow.",
        "keywords": ["missing return", "returns none", "no default return"],
    },
    {
        "task": "bug",
        "difficulty": "hard",
        "code": "total = 0\n\ndef add_value(value):\n    total += value\n    return total",
        "description": "Identify the bug in this function.",
        "keywords": ["unboundlocalerror", "scope", "global"],
        "verifier": "unbound_local_scope",
    },
    {
        "task": "bug",
        "difficulty": "hard",
        "code": "items = [1, 2, 3]\nfor items in items:\n    print(items)\nprint(items.append(4))",
        "description": "Identify the bug caused by this variable usage.",
        "keywords": ["shadowed variable", "shadowing", "list becomes int"],
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "i = 0\nwhile i <= len(values):\n    print(values[i])\n    i += 1",
        "description": "Identify the bug in this loop termination condition.",
        "keywords": ["index error", "out of bounds", "< len"],
    },
    {
        "task": "bug",
        "difficulty": "hard",
        "code": "for user in users:\n    if not user.active:\n        users.remove(user)",
        "description": "Identify the bug in this collection mutation.",
        "keywords": ["mutating while iterating", "remove during iteration", "skip elements"],
        "synonyms": ["bug", "list mutation", "iteration issue"],
    },
    {
        "task": "security",
        "difficulty": "easy",
        "code": "query = \"SELECT * FROM users WHERE name='\" + username + \"'\"",
        "description": "Identify a security vulnerability in this code snippet.",
        "keywords": ["sql injection", "parameterized", "prepared statement"],
        "synonyms": ["vulnerability", "unsafe query", "security issue"],
        "grader": "server.environment:grade_security_task",
    },
    {
        "task": "security",
        "difficulty": "hard",
        "code": "os.system('tar -czf backup.tar.gz ' + user_input)",
        "description": "Identify the security vulnerability in this shell command.",
        "keywords": ["command injection", "shell injection", "os.system"],
        "synonyms": ["unsafe command", "vulnerability", "security issue"],
    },
    {
        "task": "security",
        "difficulty": "medium",
        "code": "result = eval(user_expression)",
        "description": "Identify the security risk in this code.",
        "keywords": ["eval", "code execution", "unsafe evaluation"],
        "synonyms": ["unsafe", "vulnerability", "security risk"],
    },
    {
        "task": "security",
        "difficulty": "easy",
        "code": "DB_PASSWORD = 'super-secret-password'",
        "description": "Identify the security issue in this configuration.",
        "keywords": ["hardcoded password", "secret", "credential"],
        "synonyms": ["hardcoding", "sensitive data", "security issue"],
    },
    {
        "task": "security",
        "difficulty": "medium",
        "code": "API_KEY = 'sk_live_123456789'",
        "description": "Identify the security issue in this code.",
        "keywords": ["hardcoded api key", "secret", "credential"],
        "synonyms": ["hardcoding", "token exposure", "security issue"],
    },
    {
        "task": "security",
        "difficulty": "hard",
        "code": "with open('/srv/files/' + filename, 'r') as f:\n    return f.read()",
        "description": "Identify the security vulnerability in this file access.",
        "keywords": ["path traversal", "directory traversal", ".."],
        "synonyms": ["unsafe path", "file access issue", "vulnerability"],
    },
    {
        "task": "security",
        "difficulty": "medium",
        "code": "temp_path = '/tmp/' + user_name\nwith open(temp_path, 'w') as f:\n    f.write(data)",
        "description": "Identify the unsafe file handling issue in this code.",
        "keywords": ["unsafe file handling", "predictable path", "temporary file"],
    },
    {
        "task": "security",
        "difficulty": "hard",
        "code": "user = pickle.loads(payload)",
        "description": "Identify the security vulnerability in this deserialization logic.",
        "keywords": ["insecure deserialization", "pickle", "arbitrary code execution"],
        "synonyms": ["unsafe deserialization", "vulnerability", "security issue"],
    },
    {
        "task": "security",
        "difficulty": "medium",
        "code": "token = hashlib.md5(password.encode()).hexdigest()",
        "description": "Identify the security weakness in this hashing code.",
        "keywords": ["weak cryptography", "md5", "insecure hash"],
    },
    {
        "task": "security",
        "difficulty": "hard",
        "code": "subprocess.run('rm -rf ' + folder, shell=True)",
        "description": "Identify the security vulnerability in this process invocation.",
        "keywords": ["shell=true", "command injection", "unsafe shell execution"],
        "synonyms": ["unsafe shell", "vulnerability", "security issue"],
    },
    {
        "task": "security",
        "difficulty": "medium",
        "code": "token = random.random()",
        "description": "Identify the security issue in this token generation.",
        "keywords": ["insecure randomness", "predictable token", "random.random"],
        "synonyms": ["non-cryptographic random", "weak randomness", "security issue"],
    },
    {
        "task": "security",
        "difficulty": "hard",
        "code": "session_id = hashlib.sha1(user_id.encode()).hexdigest()",
        "description": "Identify the cryptographic weakness in this code.",
        "keywords": ["insecure hashing", "sha1", "weak hash"],
        "synonyms": ["weak cryptography", "security risk", "hash weakness"],
    },
    {
        "task": "security",
        "difficulty": "hard",
        "code": "data = yaml.load(payload, Loader=yaml.Loader)",
        "description": "Identify the security issue in this parser usage.",
        "keywords": ["unsafe yaml load", "deserialization", "code execution risk"],
        "synonyms": ["unsafe parsing", "insecure deserialization", "security issue"],
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "def read_config(path):\n    with open(path) as f:\n        data = f.read()\n    return json.loads(data)",
        "description": "Identify the robustness bug in this function.",
        "keywords": ["missing exception handling", "uncaught exception", "error handling"],
        "synonyms": ["no try except", "crash risk", "runtime failure"],
    },
    {
        "task": "bug",
        "difficulty": "hard",
        "code": "counter = {'value': 0}\n\ndef incr():\n    counter['value'] += 1",
        "description": "Identify the concurrency issue in this shared state update.",
        "keywords": ["race condition", "shared state", "thread safety"],
        "synonyms": ["data race", "concurrency bug", "synchronization"],
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "f = open('output.txt', 'w')\nf.write('done')",
        "description": "Identify the bug related to resource handling.",
        "keywords": ["file descriptor leak", "unclosed file", "resource leak"],
        "synonyms": ["missing close", "leak", "resource management"],
    },
    {
        "task": "style",
        "difficulty": "easy",
        "code": "total = 0\nfor n in numbers:\n    total = total + n",
        "description": "Identify the style/performance improvement in this snippet.",
        "keywords": ["use sum", "built-in sum", "inefficient loop"],
        "synonyms": ["pythonic", "style improvement", "readability"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "result = []\nfor i in range(len(values)):\n    result.append(values[i] * 2)",
        "description": "Identify the style issue in this transformation loop.",
        "keywords": ["list comprehension", "enumerate", "manual indexing"],
        "synonyms": ["verbose loop", "non-idiomatic", "style issue"],
    },
    {
        "task": "style",
        "difficulty": "medium",
        "code": "for user in users:\n    if user.is_active == True:\n        active.append(user)",
        "description": "Identify the style issue in this conditional loop.",
        "keywords": ["boolean comparison", "== true", "redundant comparison"],
        "synonyms": ["truthy check", "style cleanup", "readability"],
    },
    {
        "task": "bug",
        "difficulty": "hard",
        "code": "cache = {}\n\ndef get_value(key):\n    if key not in cache:\n        cache[key] = load_value(key)\n    return cache[key]",
        "description": "Identify a potential race condition in this caching logic.",
        "keywords": ["race condition", "double initialization", "thread unsafe cache"],
        "synonyms": ["concurrency issue", "shared mutable state", "thread safety"],
    },
]

STEP_REWARDS = {1: 0.3, 2: 0.3, 3: 0.4}
PARTIAL_STEP_REWARDS = {1: 0.15, 2: 0.15, 3: 0.2}
STEP_INSTRUCTIONS = {
    1: "Identify the issue in the code.",
    2: "Explain why the issue is a problem.",
    3: "Suggest a fix for the issue.",
}


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

def evaluate_review(
    review: str,
    keywords: list[str],
    synonyms: Optional[list[str]] = None,
    step_number: int = 1,
) -> str:
    expanded_synonyms = list(synonyms or [])
    for keyword in keywords:
        expanded_synonyms.extend(KEYWORD_EXPANSIONS.get(keyword.lower(), []))

    for kw in keywords:
        if _fuzzy_contains(review, kw):
            return "exact_match"

    for synonym in expanded_synonyms:
        if _fuzzy_contains(review, synonym):
            return "partial_match"

    return "no_match"


def grade(review: str, keywords: list[str], synonyms: Optional[list[str]] = None, step_number: int = 1) -> float:
    reason = evaluate_review(review, keywords, synonyms, step_number)
    if reason == "exact_match":
        return clamp_task_score(STEP_REWARDS[step_number])
    if reason == "partial_match":
        return clamp_task_score(PARTIAL_STEP_REWARDS[step_number])
    return clamp_task_score(0.01)


def clamp_task_score(score: float) -> float:
    return max(0.01, min(float(score), 0.99))


KEYWORD_EXPANSIONS: dict[str, list[str]] = {
    "sql injection": ["parameterized query", "prepared statement", "sqli"],
    "command injection": ["shell injection", "os command injection"],
    "path traversal": ["directory traversal", "../"],
    "hardcoded password": ["hardcoded secret", "embedded credential"],
    "hardcoded api key": ["hardcoded token", "embedded api key"],
    "insecure deserialization": ["unsafe pickle", "unsafe deserialize"],
    "unsafe shell execution": ["shell true", "shell execution risk"],
    "division": ["divide by zero", "zero division"],
    "mutable": ["mutable default", "shared default list"],
    "list comprehension": ["comprehension"],
    "boolean comparison": ["== true", "== false", "truthy check"],
    "debug print": ["print statement", "debug logging"],
}


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
    # Support multiple grader call shapes used by validators.
    candidate_values: list[Any] = []
    candidate_values.extend(args)
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


TASK_GRADERS = {
    "security": grade_security_task,
    "bug": grade_logic_task,
    "style": grade_style_task,
}


def verify_division_by_zero() -> bool:
    try:
        def divide(a, b):
            return a / b

        divide(10, 0)
    except ZeroDivisionError:
        return True
    except Exception:
        return False
    return False


def verify_mutable_default_argument() -> bool:
    try:
        def add_item(item, items=[]):
            items.append(item)
            return items

        first = add_item("a")
        second = add_item("b")
        return first is second and second == ["a", "b"]
    except Exception:
        return False


def verify_index_out_of_bounds() -> bool:
    try:
        def get_last(items):
            return items[len(items)]

        get_last([1, 2, 3])
    except IndexError:
        return True
    except Exception:
        return False
    return False


def verify_unbound_local_scope() -> bool:
    try:
        total = 0

        def add_value(value):
            total += value
            return total

        add_value(1)
    except UnboundLocalError:
        return True
    except Exception:
        return False
    return False


VERIFIERS = {
    "division_by_zero": verify_division_by_zero,
    "mutable_default_argument": verify_mutable_default_argument,
    "index_out_of_bounds": verify_index_out_of_bounds,
    "unbound_local_scope": verify_unbound_local_scope,
}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class CodeReviewEnv:
    def __init__(self):
        self._episode_id: str = ""
        self.step_count = 0
        self.max_steps = 3
        self.current_task: Optional[dict] = None
        self.history: list[str] = []
        self._done: bool = True

    def _build_observation(self) -> CodeObservation:
        if self.current_task is None:
            raise RuntimeError("No active task. Call reset() to start a new episode.")

        current_step = min(self.step_count + 1, self.max_steps)
        description = f"{self.current_task['description']} {STEP_INSTRUCTIONS[current_step]}"
        difficulty = self.current_task["difficulty"]
        hint_map = {"easy": 2, "medium": 1, "hard": 0}
        return CodeObservation(
            code=self.current_task["code"],
            task=self.current_task["task"],
            description=description,
            difficulty=difficulty,
            step=current_step,
            history=self.history.copy(),
            lines_of_code=len(self.current_task["code"].splitlines()),
            issue_type=self.current_task["task"],
            hint_level=hint_map.get(difficulty, 1),
        )

    def reset(self) -> CodeObservation:
        self._episode_id = str(uuid.uuid4())[:8]
        self.step_count = 0
        self._done = False
        self.history = []
        self.current_task = random.choice(DATASET)
        return self._build_observation()

    def step(self, action: CodeAction) -> StepResult:
        if self._done or self.current_task is None:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        current_step = self.step_count + 1
        reason = evaluate_review(
            action.review,
            self.current_task["keywords"],
            self.current_task.get("synonyms"),
            current_step,
        )
        verifier_name = self.current_task.get("verifier")
        verifier_success = False
        if verifier_name:
            verifier_fn = VERIFIERS.get(verifier_name)
            if verifier_fn is not None:
                try:
                    verifier_success = verifier_fn()
                except Exception:
                    verifier_success = False

        reward = clamp_task_score(0.01)
        if verifier_success or reason == "exact_match":
            reward = clamp_task_score(STEP_REWARDS[current_step])
        elif reason == "partial_match":
            reward = clamp_task_score(PARTIAL_STEP_REWARDS[current_step])

        task_grader = TASK_GRADERS.get(self.current_task["task"], grade_logic_task)
        task_score = task_grader(action.review, self.current_task)
        task_scores = {
            "code_review_security": grade_security_task(action.review),
            "code_review_logic": grade_logic_task(action.review),
            "code_review_style": grade_style_task(action.review),
        }
        self.history.append(action.review)

        self.step_count += 1
        self._done = self.step_count >= self.max_steps

        obs = self._build_observation()

        return StepResult(
            observation=obs,
            reward=reward,
            done=self._done,
            task_scores=task_scores,
            info={
                "task": self.current_task["task"],
                "difficulty": self.current_task["difficulty"],
                "reason": reason,
                "verifier": verifier_success,
                "task_score": task_score,
                "task_scores": task_scores,
            },
        )

    def state(self) -> CodeState:
        return CodeState(
            episode_id=self._episode_id,
            step_count=self.step_count,
        )


def dataset_preview() -> list[dict[str, str]]:
    return [
        {
            "task": entry["task"],
            "difficulty": entry["difficulty"],
            "description": entry["description"],
        }
        for entry in DATASET
    ]
