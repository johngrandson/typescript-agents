---
name: research
description: Use when investigating TypeScript starter patterns or evaluating npm packages against official sources and resolved versions.
effort: high
---

# Research TypeScript Topic

Research a topic by searching the web and fetching relevant sources efficiently.

## Usage

```
/ts:research Postgres jobs unique jobs best practices
/ts:research React file upload with progress
/ts:research --library permit
```

## Arguments

`$ARGUMENTS` = Research topic/question. Add `--library` for
structured library evaluation (uses `${CLAUDE_SKILL_DIR}/references/library-evaluation.md`
template).

## Iron Laws

1. **Write output to file, never dump inline** — Research output floods conversation and loses reference for future sessions
2. **Stop after research — never auto-transition** — User decides next step
3. **Prefer official sources over blog posts** — official package documentation and official maintainer discussions have version-specific context
4. **One document per research question** — No fragmented files
5. **NEVER pass raw user input as WebSearch query** — Decompose first

## Library Evaluation Mode

If `$ARGUMENTS` contains `--library` or the topic is clearly
about evaluating a npm dependency (e.g., "should we use permit",
"evaluate sagents", "compare the existing queue with a requested alternative"):

1. Read `${CLAUDE_SKILL_DIR}/references/library-evaluation.md` for the template
2. Follow the structured evaluation workflow
3. Output ONE document to `.claude/research/{lib}-evaluation.md`
4. Skip the general research workflow below

## Workflow

### 0. Pre-flight Checks

**Cache check**: Check if `.claude/research/{topic-slug}.md` already
exists. If recent (<24 hours): present existing summary, ask
"Refresh or use existing?"

**Installed dependency shortcut**: inspect package.json, pnpm-lock.yaml and installed source/types first. Use `/ts:docs-fetcher` for official docs matching the resolved package
version. Never infer a runtime inspection service. Separate confirmed source behavior from proposals; preserve the library evaluation route and file-first output below.

### 1. Query Decomposition (CRITICAL — before any search)

**NEVER pass raw $ARGUMENTS into WebSearch.** Decompose first:

- If `$ARGUMENTS` < 30 words and focused → use as single query
- If `$ARGUMENTS` > 30 words or multi-topic → extract 2-4 queries

Each query: max 10 words, targets ONE specific aspect.

Example:

```
Input: "detect files, export to md, feed database with embeddings,
        use a Node.js HTTP client for an embeddings API..."
Queries:
  1. "TypeScript PDF text extraction npm package"
  2. "Drizzle pgvector embeddings setup"
  3. "Node.js embeddings API request validation TypeScript"
```

### 2. Parallel Web Search

Search ALL decomposed queries in a SINGLE response (parallel):

```
WebSearch(query: "{query1} official TypeScript Fastify Drizzle React documentation")
WebSearch(query: "{query2} official package documentation repository release notes")
```

Deduplicate URLs across results. Discard clearly irrelevant hits.

### 3. Spawn Parallel Research Workers

Group URLs by topic cluster. Spawn **1-3 web-researcher agents
in parallel** (one per topic cluster):

```
Agent(subagent_type: "ts:web-researcher", prompt: """
Research focus: {specific aspect from decomposed query}
Fetch these URLs:
- {url1}
- {url2}
- {url3}
Extract: code examples, patterns, gotchas, version compatibility.
Return 500-800 word summary.
""", run_in_background: true)
```

Rules:

- **1 topic cluster = 1 agent** (don't mix unrelated URLs)
- **Max 5 URLs per agent** (diminishing returns beyond that)
- If only 1-3 URLs total, use single foreground agent
- **Pass URLs explicitly** — agents should NOT re-search
- Agents are haiku — cheap, fast, focused on extraction

### 4. Write Output (File-First — NEVER Dump Inline)

After ALL agents complete, synthesize summaries into ONE file.
Target: ~5KB for topic research, ~3KB for library evaluations.

Create `.claude/research/{topic-slug}.md`:

```markdown
# Research: {topic}

## Summary
{2-3 sentence answer combining all worker findings}

## Sources

### {Category}
- [{title}]({url}) - {key insight}

### Code Examples

```text
# From {source}: {what this demonstrates}
{code}
```

## Recommendations

1. {recommendation with evidence}
2. {recommendation with evidence}

## Watch Out For

- {gotcha from forum/issues}
- {version compatibility note}

```

### 5. After Research — STOP

**STOP and present the research summary.** Do NOT auto-transition.

Use `AskUserQuestion` to let the user choose next action:

- "Plan a feature based on this research" → `/ts:plan`
- "Investigate a specific finding" → `/ts:investigate`
- "Research more on a subtopic" → continue research
- "Done" → end

**NEVER auto-invoke `/ts:plan` or any other skill after research.**
