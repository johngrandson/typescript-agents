# Component boundaries

packages/ui exports React DOM source to the web bundler. Reuse its components and Tailwind tokens in web. Mobile screens use React Native primitives and their theme; shared
contracts are portable, DOM components are not.

Keep UI events close to components but domain decisions behind server/service boundaries. Test rendering and interaction at the right platform. Do not infer native layout
correctness from jsdom or Playwright.

## Starter evidence

Read `packages/ui/package.json` in the application checkout. Use the captured starter snapshot recorded by the harness for copied examples; confirm changed source hashes before adapting them.
