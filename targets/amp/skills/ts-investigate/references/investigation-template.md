# Investigation output template

Return this structure in the current session; do not write a report file unless the user explicitly asks for one. Fill this template with
observed evidence; leave unexecuted checks unchecked. An example hypothesis is
a response-envelope mismatch: a consumer reads `payload.session`, while the
validated API returns `{ data: session }`. Confirm the actual failing boundary
before using that explanation.

````markdown
# Bug Investigation: <bug description>

## Error

```text
{exact error message and stack, with credentials redacted}
```

## Reproduction

```sh
{existing package test command that reproduces the failure}
```

- Expected: {behavior required by the contract}
- Observed: {actual result and exit status}

## Initial checks

- [ ] Saved source and executing workspace match
- [ ] Affected package type check completed
- [ ] External payload passes the actual TypeBox validator
- [ ] Consumer reads the validated DTO or response envelope correctly
- [ ] Session/request ownership and resource cleanup remain current

## Root cause

- Failure: {specific invalid operation or violated invariant}
- Location: {actual source path and line}
- Cause: {input and execution path explaining the failure}
- Evidence: {failing test, log or bounded runtime observation}

## Fix

```typescript
// Insert the verified implementation excerpt with its source path.
```

## Prevention and verification

- Add a boundary test for the observed payload and a malformed response.
- Keep external data `unknown` until runtime validation succeeds.
- Check the affected workspace's TypeScript types and existing tests.
- Record actual commands, results and checks not executed.
````
