---
name: investigate
description: Investigate bugs and errors in TypeScript starter — root-cause analysis for crashes, exceptions, stack traces, test failures. Use --parallel for deep 4-track investigation.
effort: high
argument-hint: <bug description> [--parallel]
---

# Investigate Bug

Investigate bugs using the Ralph Wiggum approach: check the
obvious, read errors literally.

## Usage

```
/ts:investigate Session PATCH returns VALIDATION_FAILED for a valid partial update
/ts:investigate TypeError while applying a session event in the mobile store
/ts:investigate Stale session snapshot after reconnect --parallel
```

## Arguments

`$ARGUMENTS` = Bug description or error message. Add `--parallel`
for deep 4-track investigation.

## Mode Selection

Use **parallel mode** (spawn `deep-bug-investigator`) when:
bug mentions 3+ modules, spans multiple workspaces, is intermittent
or involves concurrency, or user says `--parallel`/`deep`.

Before spawning it, determine the effective maximum nesting depth. Use an
explicit positive-integer `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` value first;
when it is unset, inspect `claude --version` (the default is 1 in 2.1.217–2.1.218
and 3 in 2.1.219+). If the version is unavailable, conservatively use 1. At
depth 3+, use the `deep-bug-investigator` orchestrator. At depth 1 or 2, keep
orchestration in this main session: spawn the four
focused tracks (reproduction, root cause, impact, fix strategy) directly in
one parallel batch, wait for all four, then synthesize their evidence. Never
spawn an orchestrator that cannot delegate.

**Otherwise**: Run the sequential workflow below.

**Avoid confirmatory subagents**: Do NOT spawn parallel subagents
to "verify" findings you already identified in the main context.
If Step 3-4 already identified the root cause with high confidence,
present the evidence directly. Spawn another track only when it can resolve
an independent uncertainty.

## Iron Laws

1. **Read the error message literally first** — Most bugs tell you exactly what's wrong; resist the urge to theorize before reading what the system is saying
2. **Check the obvious before going deep** — Type errors, stale builds, invalid inputs and missing migrations are useful first checks; exhausting the Ralph Wiggum checklist saves hours
3. **Inspect action/API errors before UI debugging** — Follow the actual error envelope and validation evidence
4. **Consult compound docs before investigating fresh** — A previously solved problem saves the entire investigation cycle; always search `.claude/solutions/` first
5. **NEVER guess at a fix before reproducing** — Reproduce first, then identify root cause, then fix. Skipping steps causes wrong fixes
6. **DO NOT apply a fix without confirming root cause** — Verify your hypothesis with evidence (logs, tests, structured local logging) before changing code

## Investigation Workflow

### Step 0: Consult Compound Docs

Search `.claude/solutions/` for relevant keywords using Grep.

If matching solution exists, present it and ask: "Apply this
fix, or investigate fresh?"

### Step 0a: Runtime Auto-Capture (available local tools)

Capture logs from the identified local process, HTTP/OpenAPI state and relevant bounded read-only SQL using actually available tools. The starter has no application-inspection MCP
server. Prefer existing Fastify injection/Vitest fixtures for mutation probes. Confirm the running checkout and redact secrets. Record errors and source file/line, then continue;
lack of runtime access is an explicit coverage limit.

### Step 1: Sanity Checks

Read the workspace manifest and run its `check-types` script. Check saved files, exports, generated artifacts, process identity, env and migration history. Do not apply migrations
to an unknown database.

### Step 2: Reproduce

Run the nearest existing Vitest suite via `pnpm --filter <workspace> test:run <test-path>`. Record actual error output and correlated application logs; log paths come from the
running app, not a guessed framework directory.

### Step 3: Read Error LITERALLY

Parse the error message — check `${CLAUDE_SKILL_DIR}/references/error-patterns.md`.

### Step 4: Check the Obvious

Saved file? Correct workspace/process? Current package build? Valid TypeBox input? Expected envelope? Missing migration? Stale request ownership? Subscription cleanup? Current lease token?

For a silent form failure, inspect the action/API result and runtime validation before changing rendering. Web Server Actions and mobile REST hooks have different failure paths.

### Step 5: Verify One Hypothesis

Use an isolated test, bounded HTTP/log probe or disposable SQL fixture. Preserve unknown errors and compare expected versus observed output. After three failed attempts document
the failures and change approach.

### Step 6: Identify Root Cause

Find what's actually happening vs what should happen.

### Step 7: Hand Off

Present root cause + evidence. Then route by fix size:

- Small, contained fix → offer to apply directly or via `/ts:quick`
- Multi-file or risky fix → suggest `/ts:plan {root cause summary}` so
  the fix gets task structure and review
- Non-obvious root cause → after the fix lands, suggest `/ts:compound`

## Autonomous Iteration

Use `/ralph-loop:ralph-loop` for autonomous debugging with
clear completion criteria and `--max-iterations`.

## References

- `${CLAUDE_SKILL_DIR}/references/error-patterns.md` — Common errors and checklist
- `${CLAUDE_SKILL_DIR}/references/investigation-template.md` — Output format
- `${CLAUDE_SKILL_DIR}/references/debug-commands.md` — Debug commands and common fixes
