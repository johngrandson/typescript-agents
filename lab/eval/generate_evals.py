#!/usr/bin/env python3
"""Generate eval definitions for all skills that don't have one yet.

Reads each SKILL.md, analyzes its structure, and creates a tailored eval JSON.
Skips skills that already have an eval file.

Usage:
    python -m lab.eval.generate_evals
    python -m lab.eval.generate_evals --force  # Overwrite existing
"""

import argparse
import json
import os
import re

from lab.eval.matchers import parse_frontmatter, get_sections

PLUGIN_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plugins", "typescript-starter")
EVALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evals")


# Requirements come from the starter responsibilities, not the old framework's
# vocabulary. These checks complement, rather than replace, structural gates.
DOMAIN_CHECKS = {
    "audit": [(r"architecture|Architecture", "Assesses package/domain architecture"), (r"performance|Performance", "Assesses measured performance"), (r"dependencies|Dependency", "Includes dependency risk coverage")],
    "background-jobs": [(r"idempoten", "Requires at-least-once handler idempotence"), (r"lease|fenc", "Preserves lease ownership and fencing"), (r"shutdown|drain", "Covers bounded worker shutdown")],
    "boundaries": [(r"package.{0,30}(?:exports|imports)|imports.{0,30}package", "Traces real package imports and exports"), (r"worker.{0,50}API|API.{0,50}worker", "Preserves worker/API independence")],
    "brainstorm": [(r"interview\.md", "Persists requirements for planning"), (r"alternatives|tradeoffs|options", "Compares requirements and alternatives")],
    "brief": [(r"plan\.md", "Briefs an existing plan"), (r"scratchpad|decisions", "Explains decisions from available artifacts")],
    "challenge": [(r"evidence|Evidence", "Challenges decisions with evidence"), (r"risk|Risk|tradeoff", "Examines consequential tradeoffs")],
    "codex-loop": [(r"codex review", "Uses the installed Codex reviewer"), (r"round|cycle|iteration", "Bounds review/fix iterations"), (r"exit|failure|failed", "Retains process failure evidence")],
    "compound-docs": [(r"\.claude/solutions", "Uses the existing solution archive"), (r"search|Search|rg|Grep", "Searches before reusing a solution")],
    "compound": [(r"\.claude/solutions", "Captures a reusable solution"), (r"verification|verified|test", "Records evidence that the fix worked")],
    "deploy": [(r"Dockerfile|Compose|compose", "Uses the existing image/Compose deployment"), (r"migration|migrate", "Verifies migration ordering"), (r"ENVIRONMENT|STORAGE_MODE", "Distinguishes deployed environment/storage modes")],
    "deps-audit": [(r"pnpm-lock\.yaml", "Audits the actual pnpm lock graph"), (r"integrity|SRI", "Verifies artifact integrity"), (r"incomplete|coverage", "Preserves incomplete audit coverage")],
    "deps-update": [(r"pnpm outdated|outdated", "Inventories real package updates"), (r"ignore-scripts", "Separates lock resolution from lifecycle execution"), (r"peer|Peer", "Reviews peer compatibility")],
    "deps-vet": [(r"dependency-vet\.json", "Uses the JSON dependency ledger"), (r"integrity|artifact", "Binds vetting to exact artifacts"), (r"reviewer|review", "Records the actual reviewer and decision")],
    "docs-fetcher": [(r"package|version", "Resolves the relevant package/version"), (r"official|primary|source", "Uses primary version-aware documentation")],
    "document": [(r"OpenAPI|TypeBox", "Documents the existing HTTP contracts"), (r"test|verified|evidence", "Checks documented behavior against evidence")],
    "domain-resources": [(r"TypeBox", "Uses shared TypeBox boundary contracts"), (r"service", "Keeps domain behavior in services"), (r"repositor", "Separates repository persistence")],
    "drizzle-constraint-debug": [(r"SQLSTATE|constraint", "Traces actual database constraint evidence"), (r"migration|schema", "Compares schema and migration state"), (r"parameter|sanitiz|databaseErrorMessage", "Avoids exposing complete SQL error parameters")],
    "drizzle-n1-check": [(r"quer(?:y|ies).{0,40}(?:count|loop)|N\+1", "Investigates repeated query behavior"), (r"Drizzle|drizzle", "Uses the actual ORM/repository layer")],
    "drizzle-patterns": [(r"transaction", "Covers transactional consistency"), (r"repositor", "Preserves repository ports and adapters"), (r"parameter|sql`", "Uses parameterized SQL")],
    "examples": [(r"TypeScript|Fastify|Drizzle|React", "Examples use installed starter technologies"), (r"test|verification", "Makes example behavior verifiable")],
    "fastify-modules": [(r"AppContext|registry", "Explains explicit Fastify composition"), (r"service|domain", "Keeps domain logic outside HTTP transport")],
    "freeze": [(r"\.claude/\.freeze", "Uses the existing freeze sentinel"), (r"Bash|editing tools|Edit", "States the limits of edit-tool enforcement")],
    "full": [(r"progress\.md", "Persists the existing full workflow state"), (r"cycle|round", "Preserves bounded review cycles")],
    "help": [(r"/ts:", "Routes to the public TypeScript namespace"), (r"investigate|plan|quick", "Distinguishes execution and investigation workflows")],
    "init": [(r"CLAUDE\.md|AGENTS\.md", "Initializes instructions for the actual runtime"), (r"package\.json|workspace", "Detects workspace capabilities before setup")],
    "intent-detection": [(r"TypeScript|Fastify|Drizzle|React", "Routes starter-specific intent"), (r"investigate|plan|quick", "Distinguishes ambiguous intents")],
    "intro": [(r"/ts:", "Introduces the public TypeScript namespace"), (r"workflow|Workflow", "Explains workflow selection")],
    "investigate": [(r"reproduc|Reproduc", "Requires an observed reproduction"), (r"root.cause|hypothes", "Investigates causes before changing code")],
    "learn-from-fix": [(r"--library.{0,30}--scope|--scope.{0,30}--library", "Preserves explicit package and scope selection"), (r"pnpm-lock\.yaml", "Anchors knowledge to the locked package version"), (r"user-invocable: false", "Keeps generated package knowledge private"), (r"hand-authored|existing content", "Preserves unrelated authored knowledge"), (r"~/.claude/skills/npm-<package>/SKILL.md", "Documents personal npm knowledge destination"), (r"\.claude/skills/npm-<package>/SKILL.md", "Documents project npm knowledge destination"), (r"~/.claude/CLAUDE\.md", "Preserves personal cross-project instruction route"), (r"SHA-256", "Encodes canonical npm identity without scope/path collisions"), (r"canonical npm package name", "Validates scoped npm identity before storing knowledge") ],
    "narrow-catch": [(r"unknown", "Treats caught JavaScript values as unknown"), (r"rethrow|throw", "Preserves unexpected failures")],
    "perf": [(r"measure|Measure|baseline", "Measures before optimizing"), (r"event.loop|latency|query", "Examines Node/client/database costs")],
    "permissions": [(r"pnpm|package\.json", "Derives permissions from installed commands"), (r"reset|destructive|force", "Preserves destructive-operation boundaries")],
    "plan": [(r"plan\.md", "Produces the existing plan artifact"), (r"acceptance|Acceptance|verification", "Defines observable acceptance and verification")],
    "pnpm-compression": [(r"rtk", "Uses the existing output compression tool"), (r"exit|status|failure", "Preserves command failure status")],
    "pr-review": [(r"thread|comment|feedback", "Retrieves concrete PR feedback"), (r"head|commit|SHA", "Binds changes to the reviewed head")],
    "quick": [(r"workspace|package\.json", "Scopes a contained change to the actual package"), (r"check-types|verify", "Requires relevant checks before completion")],
    "react-patterns": [(r"SSE", "Accounts for web event streams"), (r"WS|WebSocket", "Accounts for mobile WebSocket transport"), (r"cleanup|cancel|stale", "Preserves ownership and cleanup")],
    "react-state-audit": [(r"retained|memory|subscription", "Inspects retained client resources"), (r"cleanup|cancel|unmount", "Checks release of client resources")],
    "recall": [(r"scratchpad|session|history", "Finds actual previous-session evidence"), (r"search|Search|query", "Searches before asserting recall")],
    "research": [(r"source|Source|official", "Uses attributable research sources"), (r"version|Version|lock", "Records version context")],
    "review": [(r"diff|commit|base", "Reviews a defined change scope"), (r"file|line|evidence", "Anchors actionable findings to source")],
    "runtime-inspection": [(r"/health", "Uses the actual API health endpoint"), (r"driver|STORAGE_MODE", "Confirms the active persistence driver"), (r"MCP|installed|available", "States available inspection capabilities")],
    "security": [(r"TypeBox", "Validates boundary inputs"), (r"identity|authentication", "Distinguishes identity from the Session domain"), (r"parameter|databaseErrorMessage", "Protects SQL parameters and database error details")],
    "techdebt": [(r"contract|boundar", "Examines meaningful architectural debt"), (r"evidence|impact|cost", "Ranks debt by evidence and impact")],
    "testing": [(r"Vitest", "Uses the installed unit test runner"), (r"inject", "Exercises Fastify without opening a port"), (r"Postgres|postgres", "Distinguishes real database coverage")],
    "trace": [(r"entry.point|entry points", "Traces toward actual application entry points"), (r"dynamic|unresolved", "Preserves unresolved call edges")],
    "triage": [(r"severity|BLOCKER|WARNING", "Classifies findings before selecting fixes"), (r"Skipped|Deferred|skip", "Retains skipped/deferred findings")],
    "typescript-idioms": [(r"unknown|discriminated|satisfies", "Uses strict TypeScript error/type idioms"), (r"AbortSignal|cleanup|shutdown", "Defines Node async resource lifecycle"), (r"import type|exports", "Respects package ESM/type boundaries")],
    "verify": [(r"pnpm verify", "Runs the actual final workspace gate"), (r"test:postgres", "Selects database integration checks when relevant"), (r"NOT RUN|NOT AVAILABLE|unavailable", "Distinguishes unexecuted checks from success")],
    "watch-pr": [(r"head SHA|head_sha|headSha|current head", "Avoids counting stale-head review evidence"), (r"codex-rounds|MAX_DURATION", "Bounds polling and paid review rounds")],
    "work": [(r"checkbox|\[x\]", "Uses plan checkboxes as workflow state"), (r"scratchpad", "Reads existing failed-approach context"), (r"3 retries|three|3 failed", "Preserves the retry bound")],
}


def classify_skill(skill_name: str, fm: dict, sections: dict, content: str) -> str:
    """Classify skill type: command, workflow, reference, internal."""
    if fm.get("disable-model-invocation"):
        return "command"
    if skill_name in ("plan", "work", "review", "full", "compound", "brief", "triage", "quick", "verify"):
        return "workflow"
    if skill_name in ("intent-detection", "docs-fetcher", "runtime-inspection", "compound-docs"):
        return "internal"
    if skill_name in ("challenge", "examples"):
        return "reference"
    # Reference skills typically have no argument-hint and are auto-loaded
    if "argument-hint" not in fm:
        return "reference"
    return "command"


def detect_references(skill_path: str) -> list[str]:
    """List reference files for a skill."""
    refs_dir = os.path.join(os.path.dirname(skill_path), "references")
    if not os.path.isdir(refs_dir):
        return []
    return [f for f in os.listdir(refs_dir) if f.endswith(".md")]


def count_iron_laws(sections: dict) -> int:
    """Count items in Iron Laws section."""
    for name, body in sections.items():
        if "iron law" in name.lower():
            return len(re.findall(r'^\s*[-*\d]+[\.\)]\s+', body, re.MULTILINE))
    return 0


def has_section(sections: dict, name: str) -> bool:
    return any(s.lower() == name.lower() or name.lower() in s.lower() for s in sections)


def generate_eval(skill_name: str, skill_path: str) -> dict:
    """Generate eval definition for one skill."""
    with open(skill_path) as f:
        content = f.read()

    fm = parse_frontmatter(content)
    sections = get_sections(content)
    skill_type = classify_skill(skill_name, fm, sections, content)
    refs = detect_references(skill_path)
    iron_law_count = count_iron_laws(sections)

    # --- Build completeness checks ---
    completeness_checks = [
        {"type": "frontmatter_field", "field": "name", "desc": "Has name field"},
        {"type": "frontmatter_field", "field": "description", "desc": "Has description field"},
    ]

    if has_section(sections, "Iron Laws"):
        min_laws = max(1, min(iron_law_count, 3))
        completeness_checks.append(
            {"type": "has_iron_laws", "min_count": min_laws, "desc": f"At least {min_laws} Iron Laws"}
        )
    else:
        # Should have Iron Laws
        completeness_checks.append(
            {"type": "section_exists", "section": "Iron Laws", "desc": "Has Iron Laws section"}
        )

    if has_section(sections, "Usage"):
        completeness_checks.append({"type": "section_exists", "section": "Usage", "desc": "Has Usage section"})

    if skill_type == "command" and "argument-hint" in fm:
        completeness_checks.append(
            {"type": "frontmatter_field", "field": "argument-hint", "desc": "Has argument-hint"}
        )

    # Check for key content patterns based on skill domain
    for pattern, desc in DOMAIN_CHECKS.get(skill_name, []):
        completeness_checks.append({"type": "content_present", "pattern": pattern, "desc": desc})

    if refs:
        completeness_checks.append(
            {"type": "content_present", "pattern": "references/", "desc": "Has References section"}
        )

    # --- Build accuracy checks ---
    accuracy_checks = [
        {"type": "valid_skill_refs", "desc": "All skill references valid"},
        {"type": "valid_agent_refs", "desc": "All agent references valid"},
    ]
    if refs:
        accuracy_checks.append({"type": "valid_file_refs", "desc": "All reference file paths valid"})

    # --- Build conciseness checks ---
    # Determine line target based on type
    if skill_type == "command":
        target, tolerance = 100, 85  # up to 185
    elif skill_type == "workflow":
        target, tolerance = 100, 95  # up to 195
    elif skill_type == "reference":
        target, tolerance = 100, 50  # up to 150
    else:  # internal
        target, tolerance = 100, 85

    conciseness_checks = [
        {"type": "line_count", "target": target, "tolerance": tolerance,
         "desc": f"Near {target}-line target ({target + tolerance} max)"},
        {"type": "max_section_lines", "max": 45, "desc": "No section exceeds 45 lines"},
        {"type": "content_absent", "pattern": "In this section|As mentioned above|It is important to note",
         "desc": "No filler phrases"},
    ]

    # --- Build triggering checks ---
    triggering_checks = [
        {"type": "description_length", "min": 50, "max": 250, "desc": "Description under 250-char plugin listing budget"},
        {"type": "description_keywords", "min": 3, "desc": "Enough domain keywords"},
        {"type": "description_no_vague", "desc": "No vague words in description"},
    ]

    # --- Build safety checks ---
    safety_checks = [
        {"type": "no_dangerous_patterns", "desc": "No unsafe code patterns"},
        {"type": "askuserquestion_option_limit",
         "desc": "AskUserQuestion lists within 4-option tool limit"},
    ]
    if iron_law_count > 0 or has_section(sections, "Iron Laws"):
        min_laws = max(1, min(iron_law_count, 3))
        safety_checks.insert(0,
            {"type": "has_iron_laws", "min_count": min_laws, "desc": f"At least {min_laws} Iron Laws"}
        )

    # Add prohibition check for command/workflow skills
    if skill_type in ("command", "workflow"):
        safety_checks.append(
            {"type": "content_present", "pattern": "NEVER|MUST NOT|DO NOT|CRITICAL",
             "desc": "Has explicit prohibitions or critical rules"}
        )

    # --- Build clarity checks (NEW: from SkillsBench, MePO) ---
    # Command/workflow skills need higher action density (imperative instructions)
    # Reference/review skills can be lower (checklists, questions are also actionable)
    action_threshold = 0.25 if skill_type in ("command", "workflow") else 0.10
    clarity_checks = [
        {"type": "action_density", "min_ratio": action_threshold,
         "desc": f"Action density (>{int(action_threshold*100)}% actionable lines)"},
        {"type": "no_duplication", "desc": "No cross-section duplication"},
    ]
    if skill_type in ("command", "workflow"):
        clarity_checks.append(
            {"type": "workflow_step_coverage", "desc": "No missing workflow steps"}
        )

    # --- Build specificity checks (NEW: from SkillsBench, SWE-Skills-Bench) ---
    specificity_checks = [
        {"type": "specificity_ratio", "min_ratio": 0.15, "desc": "Concrete over vague (>15% specific lines)"},
        {"type": "has_examples", "min_blocks": 1, "desc": "Has code examples"},
        {"type": "description_structure", "desc": "Description has what+when components"},
    ]

    return {
        "skill": skill_name,
        "skill_path": f"plugins/typescript-starter/skills/{skill_name}/SKILL.md",
        "dimensions": {
            "completeness": {"weight": 0.15, "checks": completeness_checks},
            "accuracy": {"weight": 0.10, "checks": accuracy_checks},
            "conciseness": {"weight": 0.12, "checks": conciseness_checks},
            "triggering": {"weight": 0.10, "checks": triggering_checks},
            "safety": {"weight": 0.08, "checks": safety_checks},
            "clarity": {"weight": 0.13, "checks": clarity_checks},
            "specificity": {"weight": 0.12, "checks": specificity_checks},
            "behavioral": {"weight": 0.20, "checks": []},
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate eval definitions for plugin skills")
    parser.add_argument("--force", action="store_true", help="Overwrite existing eval files")
    args = parser.parse_args()

    skills_dir = os.path.join(PLUGIN_ROOT, "skills")
    os.makedirs(EVALS_DIR, exist_ok=True)

    generated = 0
    skipped = 0

    for skill_name in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
        if not os.path.isfile(skill_path):
            continue

        eval_path = os.path.join(EVALS_DIR, f"{skill_name}.json")
        if os.path.isfile(eval_path) and not args.force:
            skipped += 1
            continue

        eval_def = generate_eval(skill_name, skill_path)
        with open(eval_path, "w") as f:
            json.dump(eval_def, f, indent=2)
            f.write("\n")

        generated += 1
        print(f"  Generated: {skill_name} ({len(eval_def['dimensions']['completeness']['checks'])} completeness, "
              f"{len(eval_def['dimensions']['accuracy']['checks'])} accuracy checks)")

    print(f"\nDone: {generated} generated, {skipped} skipped (already exist)")


if __name__ == "__main__":
    main()
