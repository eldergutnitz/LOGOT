---
applyTo: "**/*.{html,htm,css,scss,jsx,tsx}"
---

# Frontend (HTML/CSS/JavaScript, React) — Level 2

Plain HTML, CSS and JavaScript for simple interfaces; React, optionally with Bootstrap, for richer
ones. Dependencies are installed with npm and bundled with the application. At Level 2 the frontend
talks to a real backend behind real authentication.

## Security

- **The frontend enforces nothing.** Hiding UI is UX. Re-check authorisation server-side and never
  trust a role read from a token in the browser.
- **No secrets in frontend code.** Anything in the bundle is public — no API keys, client secrets or
  internal hostnames.
- **XSS is the main risk.** Never `innerHTML`, `outerHTML`, `document.write` or
  `dangerouslySetInnerHTML` with a value that is not a hard-coded literal. Use `textContent` and
  React's default escaping. If backend HTML must be rendered, sanitise it with a vetted npm
  sanitiser first and record it in the ADR.
- Never `eval`, `new Function` or a `javascript:` URL. Allow only `https:` and relative URLs in
  `href`/`src`.
- **Auth tokens:** prefer `HttpOnly`, `Secure`, `SameSite` cookies issued by the backend. If the SPA
  must hold a token, keep it in memory — never in `localStorage`.
- Send credentials only to your own origin. CSRF protection on every state-changing request.
- Configure a **CSP** with a per-request script nonce. No `'unsafe-inline'` in `script-src`.
- **No public CDNs.** Bundle dependencies from the lockfile. If a CDN is unavoidable and approved,
  pin it and use Subresource Integrity.
- Never render a raw backend error, stack trace or SQL fragment into the DOM.

## Structure

- Semantic HTML first: `<header>`, `<nav aria-label>`, `<main>`, `<section aria-labelledby>`,
  `<footer>`.
- Organise by feature. Components `PascalCase`, hooks `useX`, CSS classes kebab-case.
- Design tokens as CSS custom properties — see `brand-styling.instructions.md`.

## React

- Follow the rules of hooks with complete dependency arrays; do not disable exhaustive-deps without a
  comment explaining why.
- Clean up every effect — subscriptions, timers, listeners, abort controllers.
- Server state via TanStack Query or SWR; derive values instead of storing redundant state. Keep
  shareable state (filters, sort, page) in the URL.
- Stable `key`s from data identity, never the array index.
- Handle loading, empty, error and success for every async view. Show errors to the user.

## Accessibility — WCAG 2.2 AA

Keyboard operable end to end, visible focus, labels tied to controls, at least 4.5:1 body contrast,
meaningful `alt` text, correct heading order and `prefers-reduced-motion` respected. Never encode
meaning in colour alone. Run an automated a11y check in CI.

## Testing

React Testing Library, querying by accessible role and label, for components with real logic. Test
behaviour, not implementation. Before production, add Playwright for critical journeys, including
the IDP login redirect and the 401/403 paths.
