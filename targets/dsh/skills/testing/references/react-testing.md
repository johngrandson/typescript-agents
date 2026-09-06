# React and transport testing

Use Testing Library for web interaction and pending/error transitions. Test Server Actions, API client and SSE proxy contracts separately. Mobile screen hook/store/REST/WS tests
exercise native-client logic without proving device rendering.

Test stale loads after navigation, cancellation, reconnect and shared projection behavior. Use Playwright for actual browser flows, and record Android/iOS/device checks separately.

Starter evidence: `apps/web/components/session-panel/__tests__/mutation-transitions.test.tsx`.
