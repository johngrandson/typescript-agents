#!/usr/bin/env bash
# Behavioral gate fixtures. Commands are JSON data and are never executed.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../scripts/block-dangerous-ops.sh"

if [[ ! -x "$HOOK" ]]; then
  echo "FATAL: $HOOK not executable" >&2
  exit 2
fi

PASS=0
FAIL=0
FAILED_CASES=()

# run_hook EXPECTED COMMAND TOOL_NAME
#   EXPECTED  = "block" | "allow"
#   COMMAND   = shell command string passed as tool_input.command
#   TOOL_NAME = "Bash" by default
run_hook() {
  local expected="$1"
  local cmd="$2"
  local tool="${3:-Bash}"

  local payload
  payload=$(jq -nc --arg t "$tool" --arg c "$cmd" \
    '{tool_name: $t, tool_input: {command: $c}}')

  local out
  out=$(echo "$payload" | bash "$HOOK" 2>/dev/null)

  local actual="allow"
  if [[ -n "$out" ]] && echo "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; then
    actual="block"
  fi

  if [[ "$actual" == "$expected" ]]; then
    PASS=$((PASS + 1))
    printf '  \033[32m✓\033[0m %s: %s\n' "$expected" "$cmd"
  else
    FAIL=$((FAIL + 1))
    FAILED_CASES+=("expected=$expected actual=$actual cmd=$cmd")
    printf '  \033[31m✗\033[0m want=%s got=%s :: %s\n' "$expected" "$actual" "$cmd"
  fi
}

echo "── git push --force / --force-with-lease ──────────────────────"

# Real force-push: MUST block
run_hook block "git push --force"
run_hook block "git push -f"
run_hook block "git push --force origin main"
run_hook block "git push -f origin main"
run_hook block "git push origin main --force"
run_hook block "git push origin main -f"
run_hook block "git push --force-with-lease=ref --force"  # lease + raw force together
run_hook block "cd repo && git push --force"
run_hook block "cd repo; git push -f"

# Anchor bypasses: leading whitespace / subshell wrapper. MUST block.
run_hook block "$(printf '\tgit push --force')"
run_hook block "  git push --force"
run_hook block "  git push -f origin main"
run_hook block "(git push --force)"
run_hook block "( git push -f )"
run_hook block "(cd repo && git push --force)"

# Lease variant: MUST allow (issue #61 headline)
run_hook allow "git push --force-with-lease"
run_hook allow "git push --force-with-lease origin main"
run_hook allow "git push --force-with-lease=refs/heads/main origin main"
run_hook allow "git push origin main --force-with-lease"
run_hook allow "git push --force-with-includes"  # hypothetical future flag

# Scan-past-separator false positives: MUST allow
run_hook allow 'git push origin main && gh issue create --body "use --force-with-lease"'
run_hook allow 'git push origin main; echo "next step uses --force-with-lease"'
run_hook allow 'echo "do not run git push --force without --force-with-lease"'

# Quoted mention wrapped in parens: `(` must NOT act as a mid-line separator,
# or the issue #61 protection regresses. MUST allow.
run_hook allow 'echo "(git push --force)"'
run_hook allow 'gh pr comment --body "never (git push --force) on main"'

# Unrelated commands: MUST allow
run_hook allow "git status"
run_hook allow "git push origin main"
run_hook allow "git push --tags"
run_hook allow "git pull --force"  # not a push
run_hook allow "tail -f /var/log/app.log"
run_hook allow "rm -f file.txt"
run_hook allow "find . -name '*.ts' -exec grep -f patterns {} +"

# Different tool: MUST allow (hook gates on Bash)
run_hook allow "git push --force" Edit

echo ""
# Workspace-specific classification, including literal package/Turbo wrappers.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/packages/db" "$TMP/apps/api"
printf '%s\n' '{"name":"fixture","devDependencies":{"typescript":"*"},"scripts":{"db:push":"turbo run db:push --filter=@starter/db"}}' > "$TMP/package.json"
printf '%s\n' '{"name":"@starter/db","scripts":{"db:push":"drizzle-kit push"}}' > "$TMP/packages/db/package.json"
printf '%s\n' 'packages:' '  - apps/*' '  - packages/*' > "$TMP/pnpm-workspace.yaml"
printf '%s\n' '{}' > "$TMP/turbo.json"
printf '%s\n' 'services: {}' > "$TMP/compose.yaml"
export CLAUDE_PROJECT_DIR="$TMP"

run_hook block 'dropdb example'
run_hook block 'env ENVIRONMENT=test dropdb example'
run_hook block 'ENVIRONMENT=test dropdb example'
run_hook block '  dropdb example'
run_hook block $'\tdropdb example'
run_hook block '(dropdb example)'
run_hook block 'cd apps/api && dropdb example'
run_hook block 'pnpm db:push --force'
run_hook block 'pnpm --filter @starter/db db:push --force'
run_hook block 'pnpm -C packages/db db:push --force'
run_hook block 'env ENVIRONMENT=test pnpm db:push --force'
run_hook block '  pnpm db:push --force'
run_hook block $'\tpnpm db:push --force'
run_hook block '(pnpm db:push --force)'
run_hook block 'pnpm exec drizzle-kit push --force'
run_hook block 'drizzle-kit push --force'
run_hook block 'psql -c "DROP DATABASE example"'
run_hook block 'psql --command="DROP SCHEMA example"'
run_hook block 'mysql -e "TRUNCATE TABLE example"'
run_hook block 'docker compose down --volumes'
run_hook block 'docker compose down -v'
run_hook block 'env A=b docker compose down -v'

run_hook allow 'pnpm db:generate'
run_hook allow 'pnpm db:migrate'
run_hook allow 'pnpm db:deploy'
run_hook allow 'pnpm db:push'
run_hook allow 'pnpm --filter @starter/db db:push'
run_hook allow 'drizzle-kit generate'
run_hook allow 'drizzle-kit migrate'
run_hook allow 'drizzle-kit push'
run_hook allow 'echo "dropdb example"'
run_hook allow 'echo "(dropdb example)"'
run_hook allow 'echo "pnpm db:push --force" && pnpm test'
run_hook allow 'echo "never ENVIRONMENT=test pnpm db:push --force"'
run_hook allow 'psql -c "SELECT 1"'
run_hook allow 'psql -c "-- DROP DATABASE example"'
run_hook allow 'docker compose down'
run_hook allow 'docker compose build'
run_hook allow 'NODE_ENV=production pnpm build'
run_hook allow 'ENVIRONMENT=production pnpm build'
run_hook allow 'env NODE_ENV=production pnpm build'
run_hook allow '  NODE_ENV=production pnpm build'
run_hook allow '(NODE_ENV=production pnpm build)'
run_hook allow 'FOO=1 NODE_ENV=production pnpm build'
run_hook allow 'NODE_ENV=production PORT=3001 pnpm build'
run_hook allow 'echo "(NODE_ENV=production pnpm build)"'

mkdir "$TMP/plain"
export CLAUDE_PROJECT_DIR="$TMP/plain"
# Walk to a separate root for the outside-workspace case.
OUTSIDE=$(mktemp -d)
export CLAUDE_PROJECT_DIR="$OUTSIDE"
run_hook allow 'dropdb example'
run_hook allow 'pnpm db:push --force'
run_hook allow 'docker compose down --volumes'
run_hook allow 'NODE_ENV=production pnpm build'
run_hook block 'git push --force'
rm -rf "$OUTSIDE"

echo "────────────────────────────────────────────────────────────────"
echo "Passed: $PASS"
echo "Failed: $FAIL"

if (( FAIL > 0 )); then
  echo ""
  echo "Failed cases:"
  for c in "${FAILED_CASES[@]}"; do
    echo "  $c"
  done
  exit 1
fi

exit 0
