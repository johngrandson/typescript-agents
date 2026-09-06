# Release templates

## Changelog

Before release preparation:

```markdown
## [Unreleased]

### Added

- Feature X.

### Fixed

- Bug Y.
```

After preparing `X.Y.Z` on `YYYY-MM-DD`:

```markdown
## [Unreleased]

### Added

### Changed

### Fixed

## [X.Y.Z] - YYYY-MM-DD

### Added

- Feature X.

### Fixed

- Bug Y.
```

Keep the empty Unreleased section at the top.

## Release notes

Extract the new changelog section into a temporary file:

```bash
notes_file="$(mktemp)"
awk '/^## \[X\.Y\.Z\]/{keep=1} \
  keep && /^## \[/ && !/X\.Y\.Z/{exit} keep' CHANGELOG.md > "$notes_file"
```

Review the file before using it. Add documentation links only after confirming
that they resolve at the chosen release destination.

If the update needs manual steps, put this block before the changelog section:

```markdown
> [!WARNING]
> Upgrading requires these commands in this order. Explain what fails if they
> are skipped.
>
> ```bash
> command-one
> command-two
> ```
```

Use tested installation commands and describe the visible upgrade impact.

## Commit message

Use a semantic release-preparation commit:

```text
chore(release): prepare vX.Y.Z

Optional body explaining the version choice or migration.
```

A coauthor trailer is optional and requires the named contributor's agreement.

## Verification record

Before committing, record the exact revision and outcome of:

```bash
make ci
```

The required local gate covers lint, tests, offline validation, generated
targets, golden snapshots and structural evaluations. Record optional runtime,
provider, database, device and security checks separately when they run.

## Checklist

- The release destination is explicit.
- A repository with no semantic version tags follows the first-release path.
- TypeScript starter manifest versions and the changelog heading match.
- `catchup` remains at its independent version unless it changed.
- Generated files and executable modes were reviewed before snapshot updates.
- `make ci` passed on the release commit contents.
- The tag points to the semantic release-preparation commit.
- The user approved the exact push and publication commands.
- Publication is reported only after remote verification.
