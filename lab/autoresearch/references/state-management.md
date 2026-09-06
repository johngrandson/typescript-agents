# State Management

## Git Protocol

### Branch

Create a dedicated branch before starting: `git checkout -b autoresearch/sweep-{date}`
Branch HEAD = current best. Only improvements committed. Failed experiments reverted.

### Per-Iteration Protocol

1. Apply mutation to working tree
2. Run eval
3. If KEEP: `git add + git commit -m "autoresearch: {skill} {dim} {old}->{new}"`
4. If DISCARD: `git checkout -- plugins/typescript-starter/skills/{skill}/`

### Merge Protocol (Human)

```bash
git log --oneline autoresearch/sweep-{date}
git diff main..autoresearch/sweep-{date} --stat
git checkout main && git merge autoresearch/sweep-{date}
```

## Results Journal

**Path**: `lab/autoresearch/results.tsv` (gitignored)

### Header

```
iteration skill dimension mutation_type old_composite new_composite kept timestamp description
```

## Session State

**Path**: `lab/autoresearch/autoresearch.md` (gitignored)

Written after every iteration. Read at start of every iteration.
Bridges across context resets (/loop restarts).

Contains: iteration number, per-skill best scores, consecutive discards, stuck skills, last mutation.
