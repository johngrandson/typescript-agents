# Module and runtime troubleshooting

Check saved source, selected workspace, running process, generated artifacts, exports and env before changing logic. A stale package build can make correct source look broken.

Reproduce with an existing package test and record expected versus observed behavior. After three failed attempts document the hypotheses and research another approach; do not bypass verification.

## Starter evidence

Read `package.json` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.
