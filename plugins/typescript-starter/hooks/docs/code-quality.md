# Code quality hooks

`check-format.sh` uses installed local Prettier. It asks for file information,
resolves configuration from the affected file and checks only that file with
`--check`. Project ignore files apply. A shared 25-second subprocess budget
fits inside the 30-second event timeout; timed-out child processes are killed.
Valid/ignored files are silent; invalid style, missing tooling, missing parser,
internal errors and timeout receive distinct messages. No automatic write or
package download occurs.

`iron-law-verifier.sh` checks only Edit `new_string` or Write `content`. Comments,
string/template text and regex bodies are excluded. Line references are relative
to the edit. Contextual source reads establish a client directive or surrounding
scope, without attributing existing unrelated violations to the edit.

Warnings cover direct application `process.env` outside the env package and
literal Expo public-URL adapter, server/database imports in web client files,
direct fetches in web components, raw HTML/SQL use, explicit monetary
`real`/`doublePrecision` columns, and module-scope timers. Type-only imports,
shared contracts, mobile services, BFF proxy handlers and controlled lifecycle
functions retain their distinctions. HTML and SQL warnings request review of
origin/interpolation; they do not claim every occurrence is unsafe.

`debug-statement-warning.sh` reviews `debugger`, `console.log`, `console.debug`
and `console.trace` in application source. Tests, fixtures, generated files and
scripts are excluded. `no-console` is off, so intentional logging may stay;
server logging can use `@starter/logger` when appropriate.

`security-reminder.sh` matches basename tokens separated by `_`, `-` or `.`.
`auth-token.ts` matches; `tokenizer.ts` and an `admin/` parent directory do not.
It reminds reviewers about TypeBox inputs, client/server boundaries, SQL/HTML
origins and authorization where identity exists. Session alone is not auth.

The lexical scanner is a review aid. It leaves template interpolation,
ambiguous fragment placement, effects/closures, stale responses and job fencing
to contextual analysis. The actual shared ESLint configuration remains the
source for type/lint rules and package/test exceptions.
