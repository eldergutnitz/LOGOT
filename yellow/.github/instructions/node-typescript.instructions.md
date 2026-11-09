---
applyTo: "**/*.{ts,js,mjs,cjs}"
---

# JavaScript / TypeScript (Node.js + npm) — Level 2

Approved shapes: **Express** or **NestJS** on Node.js LTS for internal APIs, with **PostgreSQL** as the
database. Frontend code follows the same package rules; see `frontend.instructions.md`.

## Baseline

- TypeScript in `strict` mode. No `any` — use `unknown` and narrow. No `@ts-ignore` without a
  comment explaining why.
- **npm only.** Commit `package-lock.json`, install with `npm ci` and pin versions. Do not add Yarn or
  pnpm lockfiles.
- Inside the corporate network, packages come through the JFrog npm proxy (see `Approved stack` in
  `.github/copilot-instructions.md`). If an install fails with a network or 401 error, report the
  missing registry setup — never switch registries, disable TLS or put credentials in the repository.
- Never install a dependency whose `preinstall`/`postinstall` script runs encoded or dynamic code —
  flag it (OBF07).
- ESLint + Prettier in CI. No `console.log` in shipped code — use a structured logger.

## Security

- **Authentication is delegated to the corporate IDP (ISAM / CloudIDP / GRP).** Validate the OIDC
  token against the issuer's JWKS on every request. Never implement your own login, session store,
  password hashing or token issuer.
- **Deny by default:** auth middleware at the router level, with explicit opt-out for the few public
  routes. Ownership checks in the handler — a valid token is not authorisation for a specific record.
- Secrets from `process.env`, parsed at startup through a `zod` schema so a missing or malformed
  value stops the process immediately.
- **Parameterised queries only** — placeholders bound to an argument array, never a template literal
  with input. With an ORM (Prisma, Drizzle, TypeORM), never use its raw-SQL escape hatch with
  interpolated input.
- Validate every request body, param and query with **zod** (or `class-validator` in NestJS).
- `helmet` for security headers, an explicit **CORS allow-list** (never `origin: '*'` on an
  authenticated API) and rate limiting on exposed routes.
- Never `eval`, `new Function`, `child_process.exec` with interpolated input, or `require()` of a
  computed path.
- Centralised error handler: log the detail server-side, return a generic message and a request ID.
  Never send a stack trace.

## Async correctness

- `async/await` throughout; every promise is awaited or explicitly handled. Enable
  `@typescript-eslint/no-floating-promises`.
- Handle `unhandledRejection` and `uncaughtException` by logging and exiting — never swallow them.
- Set an explicit timeout and abort signal on every outbound HTTP call.

## PostgreSQL

- One shared `pg` pool with a sane max and a connection timeout. Never a connection per request.
- Migrations are versioned, reviewed files applied by the pipeline — never ad-hoc DDL.
- Transactions for multi-statement writes, with rollback on error.
- Paginate every list endpoint.

## Testing

Vitest or Jest, with Supertest for HTTP. Test logic and data access as you build. Before review,
every changed secured endpoint has 401 and 403 tests and the repository's coverage threshold is met
if one is set. Run data-access tests against a local PostgreSQL of the production major version,
not an in-memory substitute.
