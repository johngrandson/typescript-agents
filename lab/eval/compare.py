#!/usr/bin/env python3
"""Compare current skill scores against a baseline.

Usage:
    python -m lab.eval.compare --baseline lab/eval/baselines/20260323-140000.json
    python -m lab.eval.compare --baseline lab/eval/baselines/20260323-140000.json --skill plan
    python -m lab.eval.compare --baseline lab/eval/baselines/latest.json
"""

import argparse
import json
import os
import sys

from lab.eval.scorer import score_skill, find_eval, PLUGIN_ROOT
from lab.eval.schemas import EvalDefinition


def find_latest_baseline() -> str | None:
    """Find the most recent baseline file."""
    baselines_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselines")
    if not os.path.isdir(baselines_dir):
        return None
    files = sorted(f for f in os.listdir(baselines_dir) if f.endswith(".json"))
    if not files:
        return None
    return os.path.join(baselines_dir, files[-1])


def compare(baseline_path: str, skill_names: list[str] | None = None) -> dict:
    """Compare current scores against baseline."""
    with open(baseline_path) as f:
        baseline = json.load(f)

    if skill_names is None:
        skill_names = list(baseline["skills"].keys())

    results = {}
    for name in skill_names:
        if name not in baseline["skills"]:
            print(f"  SKIP: {name} (not in baseline)")
            continue

        baseline_skill = baseline["skills"][name]
        skill_path = os.path.join(PLUGIN_ROOT, "skills", name, "SKILL.md")

        if not os.path.isfile(skill_path):
            print(f"  SKIP: {name} (file not found)")
            continue

        eval_path = find_eval(name)
        eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
        current = score_skill(skill_path, eval_def)
        current_dict = current.to_dict()

        delta_composite = current_dict["composite"] - baseline_skill["composite"]
        dimension_deltas = {}
        flipped_checks = []

        for dim_name in current_dict["dimensions"]:
            curr_dim = current_dict["dimensions"][dim_name]
            base_dim = baseline_skill["dimensions"].get(dim_name, {})
            base_score = base_dim.get("score", 0)
            delta = curr_dim["score"] - base_score
            dimension_deltas[dim_name] = {
                "baseline": base_score,
                "current": curr_dim["score"],
                "delta": round(delta, 4),
            }

            # Find flipped assertions
            base_assertions = {a["id"]: a["passed"] for a in base_dim.get("assertions", [])}
            for a in curr_dim.get("assertions", []):
                base_passed = base_assertions.get(a["id"])
                if base_passed is not None and base_passed != a["passed"]:
                    flipped_checks.append({
                        "dimension": dim_name,
                        "check": a["desc"],
                        "was": "PASS" if base_passed else "FAIL",
                        "now": "PASS" if a["passed"] else "FAIL",
                    })

        if delta_composite > 0.001:
            verdict = "improved"
        elif delta_composite < -0.001:
            verdict = "regressed"
        else:
            verdict = "unchanged"

        results[name] = {
            "baseline_composite": baseline_skill["composite"],
            "current_composite": current_dict["composite"],
            "delta": round(delta_composite, 4),
            "verdict": verdict,
            "dimensions": dimension_deltas,
            "flipped_checks": flipped_checks,
        }

        symbol = {"improved": "+", "regressed": "-", "unchanged": "="}[verdict]
        print(f"  [{symbol}] {name}: {baseline_skill['composite']:.3f} -> {current_dict['composite']:.3f} ({delta_composite:+.3f})")

    return {
        "baseline_file": baseline_path,
        "baseline_timestamp": baseline.get("timestamp", "unknown"),
        "skills": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare skill scores against baseline")
    parser.add_argument("--baseline", help="Path to baseline JSON (default: latest)")
    parser.add_argument("--skill", help="Single skill to compare")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output")
    args = parser.parse_args()

    baseline_path = args.baseline
    if baseline_path == "latest" or baseline_path is None:
        baseline_path = find_latest_baseline()
        if baseline_path is None:
            print("ERROR: No baseline found. Run: python -m lab.eval.baseline", file=sys.stderr)
            sys.exit(1)

    if not os.path.isfile(baseline_path):
        print(f"ERROR: Baseline file not found: {baseline_path}", file=sys.stderr)
        sys.exit(1)

    skill_names = [args.skill] if args.skill else None

    print(f"Comparing against baseline: {baseline_path}")
    result = compare(baseline_path, skill_names)

    if args.pretty:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
