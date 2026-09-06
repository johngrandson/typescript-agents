# Permission settings format

Read the existing runtime settings before proposing changes. Claude project/local settings have a permissions object with allow/deny lists; other runtimes use their own formats.
This example is a reviewable narrow proposal, not an automatically installed grant.

```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)"
    ]
  }
}
```

Package scripts need their actual contents inspected before a rule is proposed. An inspected check-types command may justify an exact workspace rule; a pnpm wildcard can run
updates, lifecycle scripts or database mutations. Never recommend broad git/pnpm/shell permission merely to avoid prompts.

## Merge procedure

Parse the JSON, preserve all unrelated keys and rules, deduplicate exact equivalent entries and show additions/removals with effect classification. Write only the approved subset
to the intended project scope; --dry-run changes nothing. Confirm syntax and inspect the final diff. Do not modify global settings unless explicitly requested.

Entries with malformed syntax, shell operators or surprising aliases need investigation. A deny list does not make an overbroad allow proposal sound. Preserve user authorization
without claiming that settings analysis grants permission.
