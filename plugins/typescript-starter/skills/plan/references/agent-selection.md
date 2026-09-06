# Agent Selection Guidelines

## When to Spawn Which Agents

| Feature Type | Agents to Spawn |
|--------------|-----------------|
| CRUD feature | starter-patterns-analyst, drizzle-schema-designer |
| Interactive UI | starter-patterns-analyst, react-architect |
| External integration | starter-patterns-analyst, node-runtime-advisor (+ npm-library-researcher ONLY if new lib) |
| Background processing | starter-patterns-analyst, background-jobs-specialist, node-runtime-advisor |
| Data-heavy | starter-patterns-analyst, drizzle-schema-designer (+ npm-library-researcher ONLY if new lib) |
| Real-time | starter-patterns-analyst, react-architect |
| Auth/permissions | starter-patterns-analyst, security-analyzer |
| Refactoring | starter-patterns-analyst, call-tracer |
| Review fix (simple) | starter-patterns-analyst only |
| Review fix (complex) | starter-patterns-analyst + relevant specialists |
| Full new feature | ALL relevant agents |

## When to Spawn npm-library-researcher

**Spawn ONLY when:**

- Feature requires a NEW library not yet in package.json
- Evaluating ALTERNATIVE libraries to replace an existing dep

**Do NOT spawn when:**

- Library is already in package.json (use Read/Grep on `node_modules/` instead)
- Fixing review blockers (libraries already chosen)
- Refactoring existing code
- Understanding API of an existing dependency
- Simple bug fixes or improvements

**To understand an existing library's API:**

- Use `Read` on the installed package source and exports source code
- Use `Grep` to find function signatures and docs
- Use `/ts:docs-fetcher` for official installed-version documentation
- Do NOT spawn npm-library-researcher for this

## When to Spawn web-researcher

**Model**: haiku (cheap fetch worker — extraction, not reasoning)

**Spawn when:**

- Feature involves unfamiliar library/pattern
- Need community input (official maintainer discussions discussions)
- Looking for real-world examples
- Checking for known issues/gotchas
- CI/CD or infrastructure questions

**Do NOT spawn when:**

- Standard CRUD feature
- Well-known patterns (auth, pagination)
- Codebase already has similar implementation

**Spawn rules:**

- Pass a focused 5-15 word query OR pre-searched URLs, NEVER raw text
- If multiple web topics: spawn multiple agents in parallel (1 per topic)
- Max 5 URLs per agent (diminishing returns beyond that)
- Agent returns 500-800 word summary — synthesis happens in orchestrator

## When to Spawn call-tracer

Spawn when planning involves:

- **Changing function signatures** — Need all callers and argument patterns
- **Moving/renaming functions** — Need all call paths
- **Refactoring service/repository boundaries** — Need data flow understanding

## When to Ask Clarifying Questions

**Ask if:**

- Multiple valid approaches exist
- Scope is ambiguous
- Performance requirements unclear
- Integration points undefined

**Don't ask if:**

- Best practice is clear
- Codebase shows clear patterns
- Feature is well-specified

Max 3 questions. Make them count.
