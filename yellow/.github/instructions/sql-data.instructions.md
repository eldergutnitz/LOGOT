---
applyTo: "**/*.sql"
---

# SQL and PostgreSQL — Level 2

PostgreSQL is the approved database. Real corporate data is what makes a project Level 2, so every
query is a data-protection control.

## Non-negotiable

1. **Parameterised statements only.** Every value from a user, an API, a file or model output is
   bound as a parameter. Never concatenate, interpolate or `format()` a value into SQL — including
   `ORDER BY` or a table name. A dynamic identifier must match a hard-coded allow-list.
2. **Least privilege.** The application connects with a role that can do exactly what it needs.
   Never the `postgres` superuser or a schema-owner role from application code. Read-only workloads
   use a read-only role.
3. **Credentials from the vault or environment.** Never a connection string in a `.sql` file, a
   notebook, a committed config or a comment.
4. **No real personal or confidential data in fixtures, seeds or tests.** Synthetic only.

## Query discipline

- Bound every result set with `LIMIT` and a deterministic `ORDER BY`. An unbounded query is a cost
  and availability incident, not just a slow page.
- Select the columns you need — no `SELECT *` in application code.
- Avoid N+1: one set-based query instead of a query per row.
- Index the columns you filter and join on; add the index in the migration that introduces the query.
- Use `NUMERIC` for money and `timestamptz` in UTC for timestamps.

## Migrations

- Every schema change is a versioned, reviewed migration using the project's tool (for example
  Alembic in Python, or Prisma Migrate / node-pg-migrate with npm). No manual DDL in any deployed
  environment.
- Migrations are forward-only and idempotent where possible, each with a stated rollback plan.
- Destructive changes — `DROP`, `TRUNCATE`, a narrowing `ALTER` — are **ask-first** and never bundled
  into an unrelated change.
- Add columns nullable or with a default first, backfill, then enforce `NOT NULL`.

## Checklist for any query

- [ ] All values bound as parameters
- [ ] Result set bounded and ordered deterministically
- [ ] Runs under a least-privilege role
- [ ] No real personal data
- [ ] Filters indexed, no N+1
- [ ] Cost impact stated for large tables or scheduled workloads
