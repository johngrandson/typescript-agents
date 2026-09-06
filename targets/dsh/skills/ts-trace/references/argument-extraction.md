# Arguments and data flow

For each confirmed call edge record the caller file/line, callee/export identity, arguments, validation, transformation and async/error boundary. Name DTO types and runtime schemas
separately; an annotation does not prove validation.

Example path: PATCH session params/body validated by shared TypeBox → SessionService.update(sessionId, patch) → repository update → successful revision metadata → bus broadcast →
validated client event → applySessionEvent. Web Server Actions and mobile REST have distinct upstream paths.

Follow object spreads and partial patches carefully: omitted fields and explicit values have different semantics. Inspect closures/callback registration for values captured
earlier. Stop at depth 10 and preserve unresolved branches rather than speculating.
