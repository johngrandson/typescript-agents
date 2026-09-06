"""Cross-file consistency checks born from the 2026-06-11 session-insights work.

Two bug classes that per-skill scoring cannot catch:

1. References teaching anti-patterns their own Iron Laws ban
   (such as browser code importing a database runtime, or fetching directly
   from a component instead of the API adapter).
2. Skill-invoked shell scripts using cwd-relative .claude/ state paths
   (fetch-cc-changelog.sh created a stray nested .claude/ dir when run from
   inside the skill folder).
"""

import glob
import os
import re

import pytest

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
SKILLS_GLOB = os.path.join(REPO_ROOT, "plugins", "typescript-starter", "skills", "*")


# --- 1. Iron Law <-> references consistency ---

# Rules follow CLAUDE.md's web boundary and the canonical TypeScript, Drizzle
# and security skill contracts. These syntactic checks review examples; they
# do not prove data flow or replace runtime validation.
# Banned patterns must never appear in references as POSITIVE examples.
# Each occurrence must have a negative marker within +/- WINDOW lines.
CLIENT_EXAMPLE = (
    r"""(?ms)^[ \t]*["']use client["'];?[ \t]*\n(?:(?!^[ \t]*```)[\s\S])*?"""
)
TYPE_ONLY_IMPORT = r"""type\b|\{\s*(?:type\s+[\w$]+(?:\s+as\s+[\w$]+)?\s*,?\s*)+\}"""
BANNED_PATTERNS = [
    (
        "Web clients must use the server boundary instead of database runtime imports",
        re.compile(
            CLIENT_EXAMPLE
            + r"""^[ \t]*import[ \t]+(?!"""
            + TYPE_ONLY_IMPORT
            + r""")[^;\n]+\bfrom[ \t]*["']@starter/db(?:/[^"']*)?["']"""
        ),
    ),
    (
        "Web component requests belong behind Server Actions or the BFF adapter",
        re.compile(
            CLIENT_EXAMPLE
            + r"""^[ \t]*(?:(?:const|let)\s+\w+\s*=\s*|return\s+)?(?:await\s+)?fetch\s*\("""
        ),
    ),
    (
        "Drizzle SQL values must stay parameterized",
        re.compile(r"\bsql\.raw\s*\(\s*`[^`]*\$\{"),
    ),
    (
        "Parsed boundary data needs runtime validation before a concrete type assertion",
        re.compile(r"\bJSON\.parse\([^;\n]*\)\s+as\s+(?!unknown\b|const\b)[A-Za-z_$]"),
    ),
    (
        "Node error handling must not silently swallow failures",
        re.compile(r"(?<![\w$.])catch\s*(?:\([^)]*\)\s*)?\{\s*\}"),
    ),
]

NEGATIVE_MARKERS = re.compile(
    r"WRONG|NEVER|Never\b|never\b|DO NOT|Do NOT|Don'?t|don'?t|anti-pattern|Anti-pattern"
    r"|Iron Law|iron law|AVOID|Avoid\b|avoid\b|instead|Instead|BAD\b|Bad:|❌|✗"
    r"|exhaustion|unsafe|Unsafe|vulnerab|XSS|injection|Cartesian|deprecated|caution|Caution"
)

WINDOW = 5


def _reference_files():
    return sorted(glob.glob(os.path.join(SKILLS_GLOB, "references", "*.md")))


def _unmarked_patterns(text):
    lines = text.split("\n")
    for law, pattern in BANNED_PATTERNS:
        for match in pattern.finditer(text):
            idx = text.count("\n", 0, match.start())
            end = text.count("\n", 0, match.end())
            context = "\n".join(lines[max(0, idx - WINDOW) : end + WINDOW + 1])
            if not NEGATIVE_MARKERS.search(context):
                yield idx + 1, law, lines[idx].strip()[:80]


class TestIronLawReferenceConsistency:
    def test_reference_files_exist(self):
        assert len(_reference_files()) > 50, "reference glob looks broken"

    def test_no_unmarked_banned_patterns(self):
        violations = []
        for path in _reference_files():
            with open(path) as f:
                text = f.read()
            rel = os.path.relpath(path, REPO_ROOT)
            for line, law, excerpt in _unmarked_patterns(text):
                violations.append(f"{rel}:{line} — {law}: {excerpt}")
        assert not violations, (
            "Banned Iron Law patterns appear in references WITHOUT a negative "
            "marker (WRONG/NEVER/anti-pattern/...) nearby — they read as "
            "positive examples:\n" + "\n".join(violations)
        )

    @pytest.mark.parametrize(
        "example",
        [
            '"use client";\nimport { db } from "@starter/db";',
            '"use client";\nimport { type Repository, db } from "@starter/db";',
            '"use client";\nconst result = await fetch("/api/sessions");',
            "const query = sql.raw(`select * from sessions where id = ${input.id}`);",
            "const input = JSON.parse(payload) as CreateSessionInput;",
            "try { await writeSnapshot(); } catch (error) {}",
        ],
    )
    def test_current_unsafe_examples_require_explicit_warning(self, example):
        assert list(_unmarked_patterns(example))
        assert not list(
            _unmarked_patterns("WRONG: illustrative anti-pattern\n" + example)
        )

    @pytest.mark.parametrize(
        "example",
        [
            'import { db } from "@starter/db"; // server repository',
            '"use client";\nimport type { Repository } from "@starter/db";',
            '"use client";\nimport { type Repository, type Query as QueryType } from "@starter/db";',
            '"use client";\nconst result = await loadSessionAction(id);',
            "const result = await fetch(url); // mobile API adapter",
            "const query = sql`select * from sessions where id = ${input.id}`;",
            "const input: unknown = JSON.parse(payload);\nvalidateSession(input);",
            "try { await writeSnapshot(); } catch (error) { throw error; }",
            '```tsx\n"use client";\nrenderView();\n```\n```ts\nconst result = await fetch(url);\n```',
        ],
    )
    def test_current_safe_examples_remain_available(self, example):
        assert not list(_unmarked_patterns(example))


# --- 2. Skill script .claude/ path anchoring ---

# A literal `.claude/` path that does not go through CLAUDE_PROJECT_DIR (or an
# explicit $PWD fallback) resolves against the caller's cwd. Skill scripts run
# wherever the Bash tool's persistent cwd happens to be.
RELATIVE_CLAUDE_PATH = re.compile(r"""(?x)
    (?<! [\w$}/.\-] )      # not preceded by var/expansion/path chars
    \.claude/              # the literal relative path
""")


def _skill_scripts():
    scripts = sorted(glob.glob(os.path.join(SKILLS_GLOB, "scripts", "*.sh")))
    scripts += sorted(glob.glob(os.path.join(REPO_ROOT, "scripts", "*.sh")))
    return scripts


class TestSkillScriptPathAnchoring:
    def test_scripts_exist(self):
        assert len(_skill_scripts()) >= 2, "script glob looks broken"

    def test_no_cwd_relative_claude_paths(self):
        violations = []
        for path in _skill_scripts():
            with open(path) as f:
                lines = f.read().split("\n")
            for idx, line in enumerate(lines):
                if line.lstrip().startswith("#"):
                    continue
                if not RELATIVE_CLAUDE_PATH.search(line):
                    continue
                # Anchored on the same line is fine
                if "CLAUDE_PROJECT_DIR" in line or "$PWD" in line:
                    continue
                rel = os.path.relpath(path, REPO_ROOT)
                violations.append(f"{rel}:{idx + 1} — {line.strip()[:90]}")
        assert not violations, (
            "cwd-relative .claude/ paths in skill scripts — anchor with "
            '"${CLAUDE_PROJECT_DIR:-$PWD}" (nested-state-dir bug class):\n'
            + "\n".join(violations)
        )
