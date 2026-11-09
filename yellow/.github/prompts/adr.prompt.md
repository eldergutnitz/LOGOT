---
name: adr
description: Escribe un Architecture Decision Record para el cambio actual, siguiendo el formato obligatorio de Nivel 2.
agent: agent
argument-hint: la decisión a documentar (p. ej. "usar FastAPI en vez de Flask")
---

# Write an ADR — Level 2

Write an Architecture Decision Record for: **${input:decision:¿qué decisión hay que documentar?}**

## Steps

1. Read the current diff or referenced code. Do not document a decision you have not verified was
   made.
2. Find the next free number in `docs/adr/`, creating the directory if needed.
3. Write `docs/adr/ADR-<NNN>-<kebab-case-title>.md` with exactly this structure:

```markdown
# ADR-<NNN>: <decision in one line>

Status: proposed
Date: <YYYY-MM-DD>
Owner: <name + email>
Nivel: 2 (Amarillo) · Vertical IT: <FSK | FSE | FSP>
Stack: approved | exploratory

## Context
What forced a decision. Constraints — the approved stack, the corporate IDP, the data sources, the
existing gates. What breaks if we do nothing.

## Decision
What we chose, stated actively: "We will …".

## Alternatives considered
Rejected options, each with the concrete reason. For exploratory technology, include the
approved-stack option and why it does not fit.

## Consequences
What gets easier, what gets harder, and what we now owe — migrations, monitoring, documentation,
a decommissioning path.

## Security & cost impact
- Data touched and its classification
- Authentication/authorisation path affected
- New or changed dependencies
- Cloud footprint delta — **any increase must be raised with IT before implementation**
- Gates triggered: IT Security Risk Assessment · Pentest · OSS Compliance · IT Cost Review
```

4. Report the ADR number so the pull request can reference it.

## Rules

- Keep it short — a few lines per section, under one page.
- Be specific: name versions, systems and numbers.
- If you do not know the owner, vertical or data classification, leave a marked `TODO:` and say so.
  Do not invent it.
- One decision per ADR.
