# Compound Documentation Schema

YAML frontmatter schema for solution documentation files.

## Required Fields

### module

- **Type**: string
- **Description**: TypeScript module or context area
- **Examples**: `"SessionService"`, `"sessionsStore"`, `"JobRunner"`

### date

- **Type**: string
- **Pattern**: `YYYY-MM-DD`

### problem_type

- **Type**: string
- **Description**: Category of the problem. Use a concise label.
- **Suggested values**: `build_error`, `test_failure`, `runtime_error`,
  `performance_issue`, `database_issue`, `security_issue`,
  `react_bug`, `job_issue`, `runtime_issue`, `integration_issue`,
  `logic_error`, `deployment_issue`, `iron_law_violation`
- Free-form — use the closest match or create a new label if needed.

### component

- **Type**: string
- **Description**: Which component area was affected.
- **Suggested values**: `drizzle_schema`, `drizzle_query`, `drizzle_migration`,
  `fastify_service`, `fastify_route`, `fastify_registry`,
  `react_load`, `react_events`, `react_components`,
  `react_streams`, `job_handler`, `job_config`, `node_lifecycle`,
  `resource_cleanup`, `realtime`, `authentication`, `authorization`,
  `testing`, `deployment`, `configuration`
- Free-form — use the closest match or create a new label if needed.

### symptoms

- **Type**: array of strings (1-5 items)
- **Description**: Observable symptoms — error messages, visual issues,
  unexpected behavior. Must be specific and observable.
- **Examples**:
  - `"Repeated SQL query per listed session"`
  - `"Mobile session load completed after navigation"`

### root_cause

- **Type**: string
- **Description**: The actual underlying reason WHY this happened.
  Be specific and descriptive. Use the cause, not the symptom.
- **Examples**: `"Repeated findById in a session-list loop"`,
  `"Stale mobile request overwrote current session"`,
  `"Worker retried a malformed payload instead of abandoning it"`

### severity

- **Type**: enum
- **Values**: `critical`, `high`, `medium`, `low`

### tags

- **Type**: array of strings (up to 8)
- **Description**: Searchable keywords, lowercase, hyphen-separated
- **Examples**: `["batch-query", "sql", "n-plus-one"]`

## Optional Fields

### typescript_version / fastify_version

- **Type**: string, pattern `X.Y.Z`

### iron_law_number

- **Type**: integer (1-13)
- **Description**: Which Iron Law was violated (if applicable)

### related_solutions

- **Type**: array of strings (file paths to related solutions)

## Validation Rules

1. `module` must be a valid TypeScript module or context name
2. `date` must be in `YYYY-MM-DD` format
3. `symptoms` must be specific and observable (not vague)
4. `root_cause` must explain WHY, not just WHAT
5. `severity` must be one of the four enum values
6. `tags` should be lowercase, hyphen-separated
