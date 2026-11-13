# Plantilla de repositorio — Vibe Coding Nivel 2 (Amarillo)

Plantilla mínima para proyectos SEAT S.A. de Nivel 2 —datos internos reales, servidor, credenciales o
despliegue interno— desarrollados con GitHub Copilot. Configura Copilot para usar el stack aprobado,
aplicar los guardrails de IT-SEC y dejar evidencia para la revisión humana.

## Stack aprobado

| Área | Tecnología |
|---|---|
| Python | Python 3.11+ — Streamlit, FastAPI o Flask |
| JavaScript / TypeScript | Node.js LTS — Express o NestJS, solo con **npm** |
| Frontend | HTML/CSS/JavaScript o React (opcionalmente Bootstrap), con npm |
| Base de datos | PostgreSQL |

> **npm en la red corporativa:** `npm install` no funciona hasta configurar el proxy de JFrog:
>
> ```bash
> npm config set registry https://jfrog.hub.vwgroup.com/artifactory/api/npm/remote-npm-js/
> npm login   # credenciales de Artifactory
> ```
>
> Como alternativa a `npm login`, añade la autenticación en tu `~/.npmrc` de usuario. Nunca subas
> credenciales al repositorio (ni en un `.npmrc` del proyecto).

## Flujo de trabajo

Iteraciones cortas: primero una versión mínima que funcione, después se mejora. Durante la iteración
basta con comprobaciones rápidas y tests para la lógica, los permisos y el acceso a datos; los tests
completos, el ADR (si hace falta) y la revisión de seguridad se hacen antes del PR. Los guardrails de
seguridad se aplican siempre.

### Otras tecnologías

Se pueden explorar otras tecnologías como prototipo local si se cumplen los guardrails de seguridad
sin excepciones, con datos sintéticos, sin conexiones corporativas ni despliegue, con dependencias
fijadas y un ADR que justifique la elección. Explorar no es aprobar: integrarlas o llevarlas a
producción requiere la aprobación de la vertical IT. Las condiciones completas están en
`.github/copilot-instructions.md`.

## Contenido

```text
.github/
├── copilot-instructions.md                 ← datos del proyecto, stack, niveles y reglas
├── instructions/
│   ├── security-guardrails.instructions.md ← decisiones IT-SEC (todos los ficheros)
│   ├── python.instructions.md              ← *.py
│   ├── node-typescript.instructions.md     ← *.ts, *.js
│   ├── frontend.instructions.md            ← HTML, CSS, JSX/TSX
│   ├── brand-styling.instructions.md       ← estilo visual y marcas
│   └── sql-data.instructions.md            ← *.sql (PostgreSQL)
├── skills/level-2-security-review/SKILL.md ← workflow de revisión de seguridad
├── agents/secure-coder.agent.md            ← revisor de seguridad de solo lectura
├── prompts/
│   ├── new-feature.prompt.md               ← /new-feature
│   └── adr.prompt.md                       ← /adr
├── ISSUE_TEMPLATE/copilot-task.yml         ← tarea acotada para asignar a Copilot
└── pull_request_template.md                ← evidencia para la revisión humana
```

## Uso

1. Copia `.github/` a la raíz del repositorio.
2. Borra las instrucciones de stacks que no uses (p. ej. `python.instructions.md` en un proyecto
   solo npm).
3. Completa los `TODO` de `.github/copilot-instructions.md`: datos del proyecto y comandos
   verificados. Un prototipo local con datos sintéticos puede empezar antes; integración y
   despliegue no.
4. Activa protección de rama, checks obligatorios y revisión humana. Las instrucciones no sustituyen
   SAST, CODEOWNERS ni los gates corporativos.
5. Comprueba en Copilot Chat (**References**) que se cargan las instrucciones.

Las cadenas HALT/WARN/ALERT de `security-guardrails.instructions.md` las verifica el harness
corporativo de IT-SEC: no las modifiques.
