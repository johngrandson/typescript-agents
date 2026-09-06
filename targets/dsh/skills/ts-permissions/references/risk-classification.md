# Classify actual command effects

| Class | Examples | Treatment |
| --- | --- | --- |
| GREEN | git status/diff/log, rg, reading manifests | Read-only when arguments do not redirect/mutate |
| YELLOW | pnpm check-types/lint/test:run/build, package scripts, git add/commit, Docker build/run | Inspect exact script and lifecycle/fixture effects before proposing a narrow rule |
| YELLOW | pnpm install/update, db:migrate/db:generate/db:push, deployment commands | Network/files/schema effects; scope to known workspace and authorized target |
| RED | reset/drop database, destructive deletion, force push, reset --hard, curl piped to shell | Never recommend broad automatic permission |

A package script can invoke arbitrary code. A familiar script name is not proof of safety; follow aliases and child commands. Quoted shell operators, redirects, substitutions and
executable aliases require actual parsing, not substring approval. Never recommend `Bash(pnpm *)` or `Bash(git *)` to reduce prompts.

Preserve explicit session authorization, but permission analysis does not grant it. Preview proposed settings, show their scope/effects, and merge only approved entries without
deleting unrelated settings.
