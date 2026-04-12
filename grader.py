from graders import (
    grade_task_code_review_style,
    grade_task_code_review_logic,
    grade_task_code_review_security,
    grade_task_division_by_zero,
    grade_task_mutable_default_argument,
    grade_task_sql_injection,
    DISCOVERABLE_GRADERS,
)

TASKS = [
    {"id": "code_review_style", "task_id": "code_review_style", "name": "Code Review Style", "difficulty": "easy", "grader": "graders:grade_task_code_review_style"},
    {"id": "code_review_logic", "task_id": "code_review_logic", "name": "Code Review Logic", "difficulty": "medium", "grader": "graders:grade_task_code_review_logic"},
    {"id": "code_review_security", "task_id": "code_review_security", "name": "Code Review Security", "difficulty": "hard", "grader": "graders:grade_task_code_review_security"},
    {"id": "division_by_zero", "task_id": "division_by_zero", "name": "Division By Zero", "difficulty": "easy", "grader": "graders:grade_task_division_by_zero"},
    {"id": "mutable_default_argument", "task_id": "mutable_default_argument", "name": "Mutable Default Argument", "difficulty": "medium", "grader": "graders:grade_task_mutable_default_argument"},
    {"id": "sql_injection", "task_id": "sql_injection", "name": "SQL Injection", "difficulty": "easy", "grader": "graders:grade_task_sql_injection"},
]

def grade_performance(state, task_id):
    task = str(task_id or "code_review_style").lower()
    if task in DISCOVERABLE_GRADERS:
        return DISCOVERABLE_GRADERS[task](state)
    return 0.5
