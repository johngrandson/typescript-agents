---
name: ts-help
description: Use when choosing a TypeScript Starter Harness workflow for planning,
  debugging, review or verification; not for bare /help or a plugin tour.
---

# Plugin Help — Interactive Command Advisor

Helps users find the right command, skill, or agent for their situation.

## Usage

```
/skill:ts-help                          # Analyze context, suggest commands
/skill:ts-help how do I debug this?     # Route to /skill:ts-investigate
/skill:ts-help add a new feature        # Route to /skill:ts-plan -> /skill:ts-work
```

## Arguments

- `$ARGUMENTS` — optional description of what the user wants to do
- Empty = analyze current context (git status, existing plans, file patterns)

## Execution Flow

### Step 1: Gather Context

If `$ARGUMENTS` is non-empty, use it as primary signal.

Always gather ambient context (run in parallel):

1. Check for existing plans: use Glob on `.claude/plans/*/plan.md` — active work in progress?
2. Check git status: uncommitted changes? which files?
3. Check for solution docs: use Glob on `.claude/solutions/**/*.md` — prior knowledge?

### Step 2: Classify Intent

Read `references/tool-catalog.md` for the full routing table.

Map the user's situation to one of these categories:

| Category | Signals | Primary Commands |
|----------|---------|-----------------|
| **Starting out** | No plans, new to plugin | `/skill:ts-intro` |
| **Ideation** | "explore", "brainstorm", "not sure", "how to approach", "vague idea" | `/skill:ts-brainstorm` |
| **New feature** | "add", "build", "implement", multi-file | `/skill:ts-plan` → `/skill:ts-work` |
| **Quick change** | Single file, <50 lines, "fix typo" | `/skill:ts-quick` |
| **Bug** | Error, stack trace, "broken", "failing" | `/skill:ts-investigate` |
| **Review** | "check", "review", PR ready | `/skill:ts-review` |
| **Performance** | "slow", "N+1", "memory" | `/skill:ts-perf`, `/skill:drizzle-n1-check`, `/skill:react-state` |
| **Research** | "how to", "best practice", "evaluate lib" | `/skill:ts-research` |
| **Resume work** | Existing plan with unchecked tasks | `/skill:ts-work --continue` |
| **Post-fix** | "that worked", solved a hard bug | `/skill:ts-compound` |
| **Full cycle** | Large feature, new domain area | `/skill:ts-full` |
| **Project health** | "audit", "tech debt", "overall quality" | `/skill:ts-audit`, `/skill:ts-techdebt` |
| **Dep update audit** | "audit deps", "supply chain", "post-`pnpm update`", "review pnpm-lock.yaml PR" | `/skill:ts-deps-audit` |
| **Manual dep vetting** | "vet this package", "approve dep", "trust ledger", "after /skill:ts-deps-audit findings" | `/skill:ts-deps-vet` |
| **Deployment** | "deploy", "release", "production" | `/skill:ts-verify` then deploy skill |
| **Permissions** | "too many prompts", "allow", "permission fatigue" | `/skill:ts-permissions` |
| **Returning after time off** | "what did I miss", "back from vacation", "catch up", "what changed while I was out" | `/catchup` (companion plugin, separate install) |

### Step 3: Respond or Clarify

**If high confidence** (clear match to one category):
Present the recommendation with:

- The command to run (with exact syntax)
- One-line explanation of what it does
- What artifacts it creates (if any)
- Suggested next step after it completes

**If medium confidence** (2-3 possible matches):
Use `AskUserQuestion` with the top options, each with a one-line explanation.

**If low confidence** (vague or no signal):
Ask ONE focused clarifying question. Examples:

- "Are you starting something new or continuing existing work?"
- "Is this a bug fix or a new feature?"
- "How many files do you expect to change?"

Then recommend based on the answer.

### Step 4: Offer Follow-up

After recommending, always add:

- "Run `/skill:ts-help` anytime to get routing advice"
- If they seem new: "Try `/skill:ts-intro` for a full plugin walkthrough"

## Iron Laws

1. **ONE recommendation** — don't dump the full catalog, pick the best match
2. **MAX ONE clarifying question** — don't interrogate, make your best guess
3. **Show exact syntax** — `/skill:ts-plan Add user notifications` not just "use the plan command"
4. **Context over keywords** — existing plans + git state matter more than word matching
5. **NEVER block** — if user already knows what they want, DO NOT redirect

## Integration

- Complements `intent-detection` (auto-trigger) with explicit invocation
- References same routing logic but adds interactive clarification
- Can recommend `/skill:ts-intro` for onboarding
