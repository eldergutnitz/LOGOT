---
name: level-2-security-review
description: Review a SEAT S.A. Vibe Coding Level 2 change for security and production-gate risks. Use for diffs, pull requests, authentication or authorization changes, corporate-data access, dependencies, scripts, AI features, or deployment configuration, and before handing Level 2 work to a human reviewer.
---

# Review a Level 2 change

Perform an evidence-based pre-review. Do not edit the change, approve it, merge it or represent this
review as a pentest, corporate gate or substitute for human review.

## Establish scope

1. Read `.github/copilot-instructions.md`, including the owner, stack, exploration lane, data and
   commands.
2. Read `.github/instructions/security-guardrails.instructions.md` completely.
3. Inspect the requested diff or PR plus the surrounding code needed to understand changed data,
   trust and authorization boundaries. Review actual code, not the issue's claims about it.
4. List relevant checks. If the active agent has execution access, run configured tests/security
   commands that do not change external state. Otherwise list them as not run. Never invent one.

## Evaluate

Apply the IT-SEC decision tree to every changed file. Also check:

- secrets, real personal/confidential data and unsafe logging;
- identity delegation, endpoint/object authorization, tenant isolation and 401/403 coverage;
- schema validation, parameterised SQL/commands, output encoding and safe deserialisation;
- dynamic/encoded execution, download-and-run and bypass/evasion patterns;
- dependency provenance, pinning, lockfile, advisories and lifecycle/install hooks;
- safe errors, rollback, timeouts, query bounds, cost and observability;
- prompt injection, excessive AI tool authority and unsafe use of model output;
- technology outside the approved stack: exploration-lane conditions met and ADR present;
- Level 3 signals, acceptance criteria, ownership and missing production gates.

Do not over-block data-only base64, download-to-file, ordinary pipelines or literal process
replacement. Follow the false-positive rules in the security instructions.

## Report

Lead with the IT-SEC decision: **HALT**, **WARN**, **ALERT** or **PASS**, using the exact required
wording when applicable. Then report findings from highest to lowest severity. For each finding give:

- severity and WEB/LLM/OBF category;
- file and line (or dependency and version);
- evidence and realistic impact;
- smallest secure remediation;
- test or check that demonstrates the fix.

Avoid style-only comments and unsupported speculation. If there are no findings, say so without
claiming the change is secure.

End with one delivery verdict:

- `VEREDICTO: BLOQUEADO` — any critical/HALT issue.
- `VEREDICTO: CON RESERVAS` — non-critical findings remain.
- `VEREDICTO: LISTO PARA REVISIÓN HUMANA` — no material finding in the reviewed scope.

Finally list, briefly, commands run with results, checks not run, files or systems not inspected and
assumptions. Keep the report proportional to the change: a small change with no findings needs only
the decision, the verdict and that list.
