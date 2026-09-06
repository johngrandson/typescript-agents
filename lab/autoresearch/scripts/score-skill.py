#!/usr/bin/env python3
"""Thin wrapper around lab/eval/scorer.py for autoresearch use.

Usage:
    python3 lab/autoresearch/scripts/score-skill.py plugins/typescript-starter/skills/review/SKILL.md
    python3 lab/autoresearch/scripts/score-skill.py plugins/typescript-starter/skills/review/SKILL.md lab/eval/evals/review.json

Outputs single JSON line to stdout. Errors to stderr.
"""

import os
import sys

# Add project root to path (scripts/ -> autoresearch/ -> lab/ -> project root)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from lab.eval.scorer import score_skill, find_eval
from lab.eval.schemas import EvalDefinition


def main():
    if len(sys.argv) < 2:
        print("Usage: score-skill.py <skill_path> [eval_path]", file=sys.stderr)
        sys.exit(1)

    skill_path = sys.argv[1]
    eval_path = sys.argv[2] if len(sys.argv) > 2 else None

    if eval_path is None:
        skill_name = os.path.basename(os.path.dirname(skill_path))
        eval_path = find_eval(skill_name)

    eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
    score = score_skill(skill_path, eval_def)
    print(score.to_json())


if __name__ == "__main__":
    main()
