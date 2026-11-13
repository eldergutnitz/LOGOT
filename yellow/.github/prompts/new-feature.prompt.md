---
name: new-feature
description: Construye una funcionalidad de Nivel 2 en iteraciones cortas — encuadrar, primera versión funcional, iterar y endurecer antes del PR.
agent: agent
argument-hint: qué hay que construir
---

# New feature — Level 2 flow

Build: **${input:feature:¿qué hay que construir?}**

Work in short, visible iterations. Follow `.github/copilot-instructions.md`; the security guardrails
apply at every step.

1. **Frame in two sentences.** Level 1, 2 or 3, and approved stack or exploration lane. For Level 3,
   name the signal and build only the largest safe Level 2 subset. State your assumptions instead of
   asking, unless an ask-first boundary applies.
2. **Build a thin slice.** The smallest end-to-end version that works, following existing patterns
   and the rules in `.github/instructions/` for the files you touch. Use synthetic data and local
   fakes where real integrations are not ready.
3. **Check fast.** After each step, run the app or a focused test and fix what breaks. Add tests for
   logic, permission checks and data access as you go.
4. **Iterate.** Show the result, then extend or refine in small steps.
5. **Harden before the PR.** When the feature is ready for review:
   - complete the tests, including 401/403 and malformed input where relevant;
   - run the full verified commands;
   - write a short ADR with `/adr` if a decision is expensive to reverse or uses exploratory
     technology;
   - for sensitive changes (auth, data access, dependencies, scripts, AI features, deployment
     config), apply `.github/skills/level-2-security-review/SKILL.md` to the diff.
6. **Hand over in a few lines.** What changed, commands run with results, what is not verified and
   what the reviewer must check.

You do not merge. A human reviews every pull request.
