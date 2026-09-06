import json
from pathlib import Path
import runpy


METRICS = runpy.run_path(str(
    Path(__file__).resolve().parents[2]
    / ".claude/skills/session-scan/references/compute-metrics.py"
))


def test_session_transcript_recognizes_pnpm_and_node_execution():
    calls = METRICS["extract_tool_calls"]([
        {"role": "assistant", "content": "$ pnpm test:run"},
        {"role": "assistant", "content": "$ node scripts/check.mjs"},
        {"role": "assistant", "content": "Review the TypeScript diagnostics."},
    ])
    assert [call["name"] for call in calls] == ["Bash", "Bash"]


def test_session_backfill_suggests_verification_after_repeated_pnpm_checks(tmp_path):
    extract = tmp_path / "session.json"
    extract.write_text(json.dumps({
        "session_id": "typescript-checks",
        "tool_usage": {"Bash": 3},
        "pnpm_commands": ["pnpm check-types", "pnpm test:run", "pnpm test:run"],
    }))
    result = METRICS["backfill_from_v1"](extract)
    assert result["session_id"] == "typescript-checks"
    assert result["plugin_signals"]["could_use"] == ["verify"]


def test_starter_file_categories_follow_package_roles_and_test_precedence():
    result = METRICS["categorize_files"]([
        "apps/api/src/modules/sessions/__tests__/service.test.ts",
        "apps/worker/src/worker.test.ts",
        "apps/web/src/app/page.tsx",
        "apps/mobile/src/screens/session.tsx",
        "packages/db/drizzle/0004_session_revisions.sql",
        "packages/db/drizzle/meta/_journal.json",
        "apps/worker/src/worker.ts",
        "apps/api/src/modules/sessions/routes.ts",
        "apps/web/src/app/api/sessions/route.ts",
        "apps/api/src/modules/sessions/service.ts",
        "packages/types/src/session.ts",
        "packages/config/scripts/check.mjs",
    ])
    assert result == {
        "test": 2, "react": 2, "migration": 2, "worker": 1,
        "router": 2, "api_module": 1, "typescript": 1, "javascript": 1,
    }
