# Import and caller analysis

Use rg to locate the declaration, exported names, re-exports, import aliases and call expressions. Resolve package exports and TypeScript path aliases before calling two similarly
named symbols identical. Read each candidate location to confirm the edge.

Record static, type-only, dynamic and registry edges distinctly. Knip finds unused imports/exports/dependencies; Turbo orders tasks; neither alone provides an authoritative call
tree. Validate signature changes with affected consumer typechecks and behavior tests.

Track visited file/symbol pairs and a maximum depth of 10. For multiple entry categories, split independent traces and merge shared segments after every selected track returns.
Missing track results remain explicit coverage gaps.
