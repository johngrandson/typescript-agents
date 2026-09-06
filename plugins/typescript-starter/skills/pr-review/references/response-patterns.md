# PR Review Response Patterns

Templates and patterns for responding to PR review comments.

## Response Templates by Category

### Code Change Responses

**Accepting a suggestion:**

```
Good catch! Updated to use {suggestion}. {Brief explanation of why it's better if not obvious.}
```

**Accepting with modification:**

```
Agreed on the concern about {issue}. I went with {alternative} instead because {reason}. Let me know if you'd prefer your original suggestion.
```

**Declining with explanation:**

```
Considered this, but {reason for current approach}. Specifically, {concrete detail, e.g., "the repository fetches related rows in one batch"}.
```

**Iron Law conflict:**

```
This would violate Iron Law #{n}: {description}. The current code uses {pattern} to avoid {consequence}. See {reference} for the rationale.
```

### Question Responses

**Explaining a decision:**

```
{Direct answer}. I chose this approach because {reason}. {Optional: alternative considered and why rejected.}
```

**Explaining TypeScript starter patterns:**

```
This uses {pattern name} — {1-sentence explanation}. In Fastify, {brief context for why this is idiomatic}. See {official package documentation link} for more detail.
```

### Nitpick Responses

**Quick acknowledgment:**

```
Fixed, thanks!
```

**Style preference:**

```
Updated. I'll follow this convention going forward.
```

**Disagreement on style (rare):**

```
I see the preference for {their style}. This codebase uses {current style} consistently in {examples}. Happy to align either way — what do you think?
```

### Discussion Responses

**Architecture trade-off:**

```
Good point about {concern}. Current approach optimizes for {priority}. The trade-off is {downside}. We could mitigate with {option} if it becomes an issue. Want me to open an issue to track?
```

**Alternative suggestion:**

```
Interesting approach! Comparing:
- Current: {pros/cons}
- Suggested: {pros/cons}
I lean toward {choice} because {reason}, but open to your perspective.
```

## Common TypeScript Review Patterns

### Pattern: "Flatten nested async branches"

Use early returns when they clarify failure paths. Keep dependent operations
in explicit `await` order; use `Promise.all` only for independent work.
Check cleanup and error propagation before accepting a shorter rewrite.

### Pattern: "Missing boundary validation or return type"

Use explicit TypeScript types where a public contract or the package lint
rules require them. Local inference can be sufficient. External data still
needs the shared TypeBox schema or validator; adding `as Payload` cannot
replace runtime validation.

### Pattern: "Narrow a discriminated union"

Check the union's actual discriminant before suggesting a `switch` or a
type guard. Destructuring reads properties; it does not check their values.
Preserve exhaustive handling and distinguish an absent property from a
valid `false`, `0` or empty-string value.

### Pattern: "N+1 query concern"

Confirm emitted SQL and query-count growth before accepting an N+1 finding. Mapping in-memory event-bus counts is not SQL. Check joins/batching against repository parity.

### Pattern: "Missing error handling"

Trace expected `AppError` values to the API's `toErrorResponse` boundary.
Await asynchronous work and preserve unexpected storage errors. Narrow
`unknown` catch values before reading their properties; do not replace
every failure with an empty result or expose driver details to clients.

### Pattern: "Test coverage"

Use the testing-reviewer criteria to identify the missing behavior:
public service contracts, web/mobile interactions, or worker retry,
lease and shutdown transitions. Name the regression the test must catch.

## Tone Guidelines

- **Be grateful**: Reviewers spend time improving your code
- **Be specific**: Reference exact lines, functions, patterns
- **Be brief**: Don't over-explain accepted changes
- **Be honest**: If you don't know, say so and research
- **Avoid defensive language**: "Actually..." or "Well..."
- **Use code blocks**: Show the fix, don't just describe it

## Handling Conflicts Between Reviewers

When multiple reviewers give conflicting feedback:

1. Identify the core concern each reviewer has
2. Find a solution that addresses both concerns
3. If irreconcilable, present both options and ask the PR author to decide
4. Never silently pick one reviewer's suggestion over another

## Batch Response Strategy

When a PR has many comments:

1. Group related comments (same file, same concern)
2. Address with a single response referencing all locations
3. Use "Addressed in {commit SHA}" for code changes
4. Leave "Will address in follow-up" for non-blocking items

## Anti-patterns to Avoid

- **Rubber-stamping**: Don't accept every suggestion blindly
- **Arguing style**: If it's not an Iron Law, defer to team convention
- **Ignoring context**: Read the full diff, not just the commented line
- **Over-promising**: Don't commit to changes you haven't verified
- **Emoji-only responses**: Always include at least a brief text acknowledgment
