# Planning Workflow — Detailed Steps

Full step-by-step details for `/ts:plan`. The SKILL.md has a
summary; this reference has the complete workflow.

## Interview Detection (from /ts:brainstorm)

Before asking clarification questions, check for a pre-existing
brainstorm interview:

1. Check `$ARGUMENTS` for a path containing `interview.md`
2. Check `.claude/plans/*/interview.md` for recent files (<24h)

If found with `Status: COMPLETE`:

- Read the interview.md Summary and Coverage Details
- Skip clarification questions entirely — the interview IS the clarification
- Use interview content as input for agent spawning (depth detection still applies)
- Note in scratchpad: "Requirements from /ts:brainstorm interview"

If found with `Status: IN_PROGRESS`:

- Read what exists, note gaps in coverage
- Ask ONLY about uncovered dimensions (don't re-ask covered ones)

## Clarification Questions (when requirements are fuzzy)

When the description is vague, unclear, or missing key details,
and no brainstorm interview.md exists, ask clarifying questions
**one at a time** before planning.

**Signals that clarification is needed:**

- Description is under 10 words without specifics
- Contains "some kind of", "maybe", "I think", "not sure"
- Missing WHO (which users), WHAT (specific behavior), or WHY
- Multiple possible interpretations exist
- Security/data implications that need explicit decisions

**Question flow** (ask ONE at a time, not all at once):

1. **Purpose**: "What problem does this solve for users?"
2. **Scope**: "Which specific behavior should this include?"
3. **Users**: "Who will use this? Any role/permission differences?"
4. **Constraints**: "Any technical constraints or preferences?"
5. **Edge cases**: "What should happen when [X]?"

**Stop asking when**: You have enough to write a plan with
concrete tasks. 2-4 questions is usually enough. Don't
interrogate — if the user gives a detailed answer, extract
what you need and move on.

**Capture decisions**: Save all clarification answers to
`.claude/plans/{slug}/scratchpad.md` as DECISION entries for future
reference.

## Depth Detection

If `--depth` not specified, auto-detect from **both** the clarity
of the request and the technical complexity:

| Request Clarity            | Technical Scope                    | Depth                       |
| -------------------------- | ---------------------------------- | --------------------------- |
| Clear + specific           | 1 module, <5 files                | `quick`                     |
| Clear + specific           | 2-3 modules, schemas/components    | `standard`                  |
| Clear + specific           | 4+ modules, security, new workers | `deep`                      |
| Vague (post-clarification) | Any                                | At least `standard`         |
| From review file           | Any                                | `standard` (scope is known) |

**Depth determines agent count AND plan detail:**

| Depth      | Agents             | Clarification           | Plan Detail                          |
| ---------- | ------------------ | ----------------------- | ------------------------------------ |
| `quick`    | 1 (patterns only)  | Skip if clear           | Task list, minimal prose             |
| `standard` | 2-3 specialists    | 1-2 questions if needed | Phased tasks with code patterns      |
| `deep`     | 4+ (full research) | 3-5 questions           | Full system map, risks, alternatives |

**TypeScript-specific complexity signals**: New migration? New client interaction?
Changes to worker leases or Fastify service/repository boundaries? Multiple
workspaces affected? These push toward deeper planning.

## Agent Spawning

Spawn agents using the Agent tool based on what's actually needed.
Delegate broad research to agents. You MAY read specific files
(CI config, a single module) for plan detail, but do NOT do the
agents' job -- let them handle pattern discovery.

**Agent count scales with depth:**

- `quick`: 1 agent (starter-patterns-analyst only)
- `standard`: 2-3 agents (patterns + relevant specialists)
- `deep`: 4+ agents (patterns + specialists +
  web-researcher + npm-library-researcher)

**Always spawn:**

- `starter-patterns-analyst`: Analyze codebase for existing patterns

**Spawn conditionally based on feature needs:**

| Condition                             | Agent                    |
| ------------------------------------- | ------------------------ |
| NEW library needed (not in package.json)   | `npm-library-researcher` |
| UI, forms, SSE/WS interactions    | `react-architect`     |
| Database, schema, table changes       | `drizzle-schema-designer`   |
| Job, worker, async, queue             | `background-jobs-specialist`        |
| Node lifecycle, process, state             | `node-runtime-advisor`            |
| Auth, login, permission, security     | `security-analyzer`      |
| Unfamiliar tech, need community input | `web-researcher`         |
| Changing function signatures          | `call-tracer`            |

**npm-library-researcher rules (STRICT):**

- ONLY spawn when evaluating a library NOT already in package.json
- Do NOT spawn for: review blockers, refactoring, existing libraries
- To understand an existing library's API, use Read/Grep on
  the installed package source and exports or use `/ts:docs-fetcher` instead

**CRITICAL**: Spawn ALL applicable agents in ONE Tool Use block
(parallel) with `run_in_background: true`. Minimum 1 agent spawned.

**Agent prompts must be FOCUSED.** Scope each prompt to the
relevant directories, files, and patterns. Do NOT give vague
prompts like "analyze the codebase."

## Waiting for Agents

You'll be notified as each background agent completes. Read each
agent's output file to collect results. Do NOT proceed to plan
generation until every agent has completed.

Then read reports from `.claude/plans/{slug}/research/`.

If an agent fails, do the research yourself with Read/Grep
instead of re-spawning.

## Infrastructure Knowledge Persistence

When Explore agents discover **project infrastructure** (not
feature-specific code) — e.g., test helpers, factory patterns,
API endpoint maps, workspace build configuration — write a compact summary
to `.claude/plans/{slug}/scratchpad.md` under a `## Infrastructure`
heading. This prevents re-exploration in follow-up sessions.

Signals that knowledge is infrastructure (not feature-specific):

- Test setup patterns (`__tests__/`, shared contract fixtures)
- Workspace environment and test configuration
- Factory/fixture patterns
- CI/deployment pipeline structure

## Breadboard System Map (React Features)

**When to breadboard**: The feature touches 2+ React pages or
components, has complex event flows (event bus, streams, multi-step
forms), or involves navigation between multiple web routes or mobile screens.
**Skip** for single-page CRUD, config changes, or non-React work.

If react-architect was spawned, its report should include
affordance tables. Use these to build a system map. See
`${CLAUDE_SKILL_DIR}/references/breadboarding.md` for full details.

## Completeness Check

**MANDATORY when planning from review.** List ALL findings from
the source and verify every one is covered:

> Source has N items. Coverage:
>
> - Finding 1: -> Plan A / Task X
> - Finding 2: -> Plan A / Task Y
>
> All N items are planned.

Every finding gets a task. No exceptions. If the user wants to
exclude something, they must say so explicitly.

**TypeScript completeness**: Does the plan include migration if schema
changes? Tests for new public functions? React rendering, interactions and cleanup on the intended platform?
Service methods and repository contracts for new domain logic?

## Split Decision

**One plan = one MD file = one focused work unit.**

If the feature is small (up to ~8 tasks, same domain), skip this
step and create one plan. Do NOT ask unnecessary questions.

If the feature is large, present OPTIONS with concrete numbers:

> Based on my analysis, this feature has N concerns and ~M tasks.
> How should I structure the plans?
>
> 1. **One plan** -- 1 file, ~M tasks across K phases
> 2. **Split into X plans** -- grouped by domain:
>    - `sessions/plan.md` (5 tasks) -- creation, limits, committed mutation receipts
>    - `session-clients/plan.md` (4 tasks) -- web SSE, mobile WS, recovery, cleanup

## Plan Generation

Create plan(s) at `.claude/plans/{feature-slug}/plan.md`.

Key requirements:

- Tasks in `- [ ] [Pn-Tm][annotation] Description` format
  (required for `/ts:work`). Valid annotations:
  `[direct]` (most common), `[drizzle]`, `[react]`, `[jobs]`,
  `[runtime]`, `[security]`, `[test]`.
  Do NOT use subagent_type names like `[general-purpose]` or
  `[solo]` -- those are not valid annotations.
- Include: Summary, Scope, Technical Decisions, Phased Tasks,
  Patterns, Risks

**Task granularity**: Tasks are logical work units, NOT individual
file edits. Group by PATTERN (what you're doing), list LOCATIONS
within. Each task includes implementation detail (code examples,
before/after). Aim for 3-8 tasks per phase, not 15+.

**Function signature precision**: When a task involves extracting,
refactoring, or renaming functions, ALWAYS specify the exact
file path, exported symbol, parameter types and return type for both source and target.
For example, preserve `SessionService.create(input: CreateSessionInput): Promise<SessionSnapshot>`
in `apps/api/src/modules/sessions/service.ts`; its repository dependency is
`createIfBelowLimit(input, hardLimit)`. A proposed move must name its destination
and account for callers, imports and method binding. Never write vague tasks
like "extract existing pattern" without specifying the actual contract.

**Scratchpad**: Also create `.claude/plans/{feature-slug}/scratchpad.md`
with initial context (feature name, brief description, plan file
path). This captures planning decisions for future sessions.

For the full plan structure, read
`${CLAUDE_SKILL_DIR}/references/plan-template.md` once when writing
the plan — do not re-read other reference files.

## Self-Check (Deep Plans Only)

For `deep` plans, answer these three questions in the plan's
**Risks** section before presenting:

1. **"What was the hardest decision?"** — Which technical choice
   had the most tradeoffs? Document alternatives considered.
2. **"What alternatives were rejected?"** — For each major
   decision, note what else was considered and why it lost.
3. **"What am I least confident about?"** — Flag areas where
   the plan might be wrong. Mark with ⚠️ for user review.

## Presenting the Plan

**STOP and present the plan.** Briefly summarize the plan (task
count, phase names, key scope). Then use `AskUserQuestion`:

For single plan:

- **Start in fresh session** (recommended for 5+ tasks)
- **Get a briefing** -- interactive walkthrough via `/ts:brief`
- **Start here** -- in current session (fine for small plans)
- **Review or adjust the plan** -- walk through phases, tell me what to change

Do NOT say "Start Phase 1" — `/ts:work` runs the whole plan.

**When user selects "Start in fresh session"**, print clear
step-by-step:

```
1. Run `/new` to start a fresh session
2. Then run one of:
   /ts:work .claude/plans/{slug}/plan.md
   /ts:full .claude/plans/{slug}/plan.md  (includes review + compound)
```

## Deepening an Existing Plan (--existing mode)

When `--existing` is passed with a plan file path, enhance the
plan with deeper research instead of creating a new one.

### Deepening Workflow

1. **Load plan** -- Parse phases, tasks, annotations, `???` markers
2. **Search compound docs** -- Find known issues in planned areas
   (`grep -rl "KEYWORD" .claude/solutions/`)
3. **Spawn research agents** -- Use SPECIALIST agents (same
   selection rules as main flow), NOT Explore agents. Each agent
   MUST write detailed output to
   `.claude/plans/{slug}/research/{topic}.md` and return ONLY a
   500-word summary. Spawn all in ONE Tool Use block with
   `run_in_background: true`
4. **Wait for ALL agents** -- You'll be notified as each completes.
   Read each agent's output file. Do NOT proceed until all complete
5. **Enhance plan** -- Add implementation detail, resolve spikes,
   add verification criteria, note risk from compound docs
6. **Present diff summary** -- Show what was enhanced

### When Deepening Adds Value

- Plan has 5+ tasks touching unfamiliar code
- Feature involves external API integration
- Security-sensitive features (auth, payments)
- Plan generated from review findings
- Tasks have `???` or spike markers

### Deepening Rules

- **NEVER delete existing tasks** — Only add detail and risks
- **Preserve task IDs** — `[Pn-Tm]` identifiers must not change
- **Compound docs first** — Check solution docs before spawning
  agents (saves context)
- **Context budget** — `--existing` often runs in sessions with
  prior history. Use specialist agents that write to files and
  return short summaries. Never use Explore agents (they return
  full output inline and exhaust context)
