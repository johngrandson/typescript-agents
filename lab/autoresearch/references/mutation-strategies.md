# Mutation Strategies

## Mutation Types

### compress_section

Remove verbosity while preserving meaning. Target sections exceeding 40 lines.
**When**: conciseness dimension fails on `max_section_lines`

### add_iron_law

Add a missing Iron Law from patterns observed in other skills.
**When**: safety or completeness fails on `has_iron_laws` with low count

### rewrite_description

Improve frontmatter description for better auto-triggering.
**When**: triggering fails on `description_keywords` or `description_length`
**Keywords**: typescript, fastify, react, drizzle, jobs, node, test, deploy, security, etc.

### move_to_references

Extract detailed content from SKILL.md to references/*.md.
**When**: conciseness fails on `line_count`
**Rule**: Iron Laws MUST stay in SKILL.md (agents may not read references/)

### fix_stale_reference

Update a cross-reference that points to a renamed, moved, or removed file/skill/agent.
**When**: accuracy fails on `valid_skill_refs`, `valid_agent_refs`, or `valid_file_refs`

### add_missing_section

Add a required section that doesn't exist.
**When**: completeness fails on `section_exists`

### add_table

Convert prose to a decision table for quick scanning.
**When**: conciseness or completeness — section is verbose but information-dense

### add_prohibition

Add explicit NEVER/MUST NOT/DO NOT rules.
**When**: safety fails on content_present for prohibition patterns

### add_description_structure

Add "Use when..." component to description.
**When**: specificity fails on `description_structure`

### add_examples

Add code blocks with concrete patterns.
**When**: specificity fails on `has_examples`

### increase_action_density

Convert theory/context into imperative instructions.
**When**: clarity fails on `action_density`

## ReflexiCoder Pattern (Post-Discard Analysis)

After a discard, BEFORE proposing the next mutation on the same skill:

1. Read the discarded mutation from results.tsv
2. Re-run the scorer to see exactly which checks got WORSE
3. Understand the causal chain: what did the mutation break?
4. Propose a mutation that achieves the same goal without the regression

## Strategy Selection

| Strategy | Best For | Convergence |
|----------|----------|-------------|
| `targeted` | Known weak spots, early optimization | Fast on low-hanging fruit |
| `sweep` | Broad improvement, initial pass | Steady, predictable |
| `random` | Escaping local optima, exploration | Slow but diverse |
