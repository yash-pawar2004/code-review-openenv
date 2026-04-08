import random
import uuid
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
    },
    {
        "task": "bug",
        "difficulty": "medium",
        "code": "def add_item(item, items=[]):\n    items.append(item)\n    return items",
        "description": "Identify the bug in this function.",
        "keywords": ["mutable", "default", "shared state"],
        "synonyms": ["bug", "unexpected state", "side effect"],
        "verifier": "mutable_default_argument",
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
    review_lower = review.lower()

    for kw in keywords:
        if kw in review_lower:
            return "exact_match"

    for synonym in synonyms or []:
        if synonym in review_lower:
            return "partial_match"

    return "no_match"


def grade(review: str, keywords: list[str], synonyms: Optional[list[str]] = None, step_number: int = 1) -> float:
    reason = evaluate_review(review, keywords, synonyms, step_number)
    if reason == "exact_match":
        return STEP_REWARDS[step_number]
    if reason == "partial_match":
        return PARTIAL_STEP_REWARDS[step_number]
    return 0.0


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
        self._done: bool = True

    def _build_observation(self) -> CodeObservation:
        if self.current_task is None:
            raise RuntimeError("No active task. Call reset() to start a new episode.")

        current_step = min(self.step_count + 1, self.max_steps)
        description = f"{self.current_task['description']} {STEP_INSTRUCTIONS[current_step]}"
        return CodeObservation(
            code=self.current_task["code"],
            task=self.current_task["task"],
            description=description,
            difficulty=self.current_task["difficulty"],
            step=current_step,
        )

    def reset(self) -> CodeObservation:
        self._episode_id = str(uuid.uuid4())[:8]
        self.step_count = 0
        self._done = False
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

        reward = 0.0
        if verifier_success or reason == "exact_match":
            reward = STEP_REWARDS[current_step]
        elif reason == "partial_match":
            reward = PARTIAL_STEP_REWARDS[current_step]

        self.step_count += 1
        self._done = self.step_count >= self.max_steps

        obs = self._build_observation()

        return StepResult(
            observation=obs,
            reward=reward,
            done=self._done,
            info={
                "task": self.current_task["task"],
                "difficulty": self.current_task["difficulty"],
                "reason": reason,
                "verifier": verifier_success,
            },
        )

    def state(self) -> CodeState:
        return CodeState(
            episode_id=self._episode_id,
            step_count=self.step_count,
        )
