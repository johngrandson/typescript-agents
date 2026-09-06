#!/usr/bin/env python3
"""Capture baseline scores for plugin skills.

Usage:
    python -m lab.eval.baseline
    python -m lab.eval.baseline --skills plan,work,review
    python -m lab.eval.baseline --all
"""

import argparse
import json
import os
from datetime import datetime, timezone

from lab.eval.scorer import score_skill, find_all_skills, find_eval, PLUGIN_ROOT
from lab.eval.schemas import EvalDefinition


DEFAULT_SKILLS = ["plan", "work", "review", "full", "investigate"]


def capture_baseline(skill_names: list[str] | None = None) -> dict:
    """Score specified skills and return baseline dict."""
    if skill_names is None:
        skill_names = DEFAULT_SKILLS

    results = {}
    for name in skill_names:
        skill_path = os.path.join(PLUGIN_ROOT, "skills", name, "SKILL.md")
        if not os.path.isfile(skill_path):
            print(f"  SKIP: {name} (file not found)", flush=True)
            continue

        eval_path = find_eval(name)
        eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
        score = score_skill(skill_path, eval_def)
        results[name] = score.to_dict()
        print(f"  {name}: {score.composite:.3f}", flush=True)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill_count": len(results),
        "skills": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Capture baseline skill scores")
    parser.add_argument("--skills", help="Comma-separated skill names (default: plan,work,review,full,investigate)")
    parser.add_argument("--all", action="store_true", help="Score all skills in plugin")
    parser.add_argument("--output", help="Output file path (default: auto-generated in baselines/)")
    args = parser.parse_args()

    if args.all:
        skill_names = [
            os.path.basename(os.path.dirname(p))
            for p in find_all_skills()
        ]
    elif args.skills:
        skill_names = [s.strip() for s in args.skills.split(",")]
    else:
        skill_names = DEFAULT_SKILLS

    print(f"Scoring {len(skill_names)} skills...")
    baseline = capture_baseline(skill_names)

    # Determine output path
    baselines_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines")
    os.makedirs(baselines_dir, exist_ok=True)

    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = os.path.join(baselines_dir, f"{ts}.json")

    with open(output_path, "w") as f:
        json.dump(baseline, f, indent=2)

    print(f"\nBaseline saved to: {output_path}")

    # Print summary
    composites = [s["composite"] for s in baseline["skills"].values()]
    if composites:
        avg = sum(composites) / len(composites)
        print(f"Average composite: {avg:.3f}")
        print(f"Range: {min(composites):.3f} - {max(composites):.3f}")


if __name__ == "__main__":
    main()
