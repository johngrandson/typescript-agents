# Documentation principles

Document tested behavior and why a boundary exists. TypeScript signatures already show parameter types; JSDoc should explain invariants, side effects, errors, cancellation, return
completeness and ownership.

SessionService documents domain behavior; repository.ts explains nullability, atomic admission and revision metadata; JobRunner explains sequential fenced at-least-once execution.
Use actual symbols and verified examples instead of hypothetical APIs.

Keep public/private distinctions meaningful. Updating an export or schema requires checking consumers and docs. An ADR records a consequential tested decision with alternatives and
consequences, not every implementation detail. Do not claim a browser test proves mobile rendering.
