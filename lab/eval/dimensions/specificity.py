"""Specificity dimension: Concrete patterns vs vague guidance.

From SkillsBench: Specificity (0-3 scale) measures actionable vs vague guidance.
From SWE-Skills-Bench: Skills with low specificity cause surface anchoring failures.
"""

from lab.eval.schemas import AssertionResult, DimensionResult, EvalDimension
from lab.eval.matchers import run_check


def score(content: str, dimension: EvalDimension, skill_path: str = "", plugin_root: str = "") -> DimensionResult:
    assertions = []
    for i, check in enumerate(dimension.checks):
        check_id = f"specificity-{i}"
        passed, evidence = run_check(
            content, check.check_type, skill_path=skill_path, plugin_root=plugin_root, **check.params
        )
        assertions.append(AssertionResult(
            id=check_id, check_type=check.check_type,
            description=check.description, passed=passed,
            evidence=evidence, weight=check.weight,
        ))
    return DimensionResult.from_assertions("specificity", assertions)
