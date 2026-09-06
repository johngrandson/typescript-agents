# Session lifecycle

`setup-dirs.sh` creates the existing six workflow directories at the recognized
workspace root: plans, reviews, solutions, audit, skill-metrics and research.
Persistent metrics are initialized only when `CLAUDE_PLUGIN_DATA` is supplied.
Starting inside `apps/mobile` never creates another `.claude` there.

`check-resume.sh` reports pending plan checkboxes and `/ts:work` paths. Outside a
recognized workspace it operates only on existing plans. A no-plan banner is
limited to recognized workspaces. `check-scratchpad.sh` reports the latest note
and all bullet entries, and creates the existing template only when a plan lacks
a scratchpad. It does not overwrite notes.

`detect-domain-resources.sh` uses declared dependencies plus known source paths
to report TypeBox contracts, Fastify modules, Drizzle repositories and worker
lifecycle. `detect-runtime-tools.sh` lists real development scripts and performs
at most one GET only after identifying the Fastify API and health route. The
URL is fixed to `http://127.0.0.1:<port>/health`; explicit `API_PORT` wins over a
schema-confirmed default. No `.env` file is executed.

The health probe does not follow redirects or use proxies/credentials. It has a
2-second connection and 3-second HTTP deadline. Only the known `data` envelope
with status, environment, nonnegative uptime and session count confirms
availability; the reported driver comes from the response. Unrecognized JSON,
offline service or redirect do not prove a runtime exists. A default port is
identified as a default, not an assertion about effective server configuration.

`check-branch-freshness.sh` finds the Git root, fetches origin quietly with a
25-second subprocess limit and no interactive credential prompt, then compares
the current branch with `origin/main` or `origin/master`. Offline failures are
silent. The hook never checks out, merges or rebases a branch.
