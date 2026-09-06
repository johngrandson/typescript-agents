# Context injection

`route-intent.sh` reads at most the first 4,000 prompt characters and emits one
suggestion per prompt. It suggests `/ts:pr-review` for PR feedback and
`/ts:investigate` for JS/TS diagnostics or web/mobile bug context. Explicit skill
invocations remain silent. Category deduplication uses hashed root/session state
in the TypeScript temporary namespace. Missing jq, malformed JSON and all
routine failures exit zero, preserving the prompt.

`inject-iron-laws.sh` gives subagents compact starter rules. It names TypeBox
contracts, transport/domain/repository separation, centralized env and the Expo
adapter, lifecycle and async cleanup, existing worker idempotency/leases/fencing,
web actions versus mobile services, server/client boundaries and real
pnpm/Turbo verification. It does not invent identity, infrastructure or servers.
The Session domain does not establish authentication.

`detect-domain-resources.sh` points to detected TypeBox, Fastify, Drizzle and
worker paths. It recommends the knowledge skill `domain-resources` through
native discovery/selection. Knowledge skills are not advertised as public slash
commands. All application-specific injection requires a recognized workspace.
