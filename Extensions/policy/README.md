# Política de extensiones permitidas — VS Code

Lista blanca **deny-by-default** para la flota corporativa, construida sobre el inventario
real (`clean/instalaciones.csv`), no sobre suposiciones.

## Tres niveles y un perfil

**Niveles** — la misma flota, con distinto grado de restricción. Cada uno es subconjunto
estricto del anterior; `verify.py` lo comprueba.

| Nivel | Sufijo | Entradas | Cobertura | Para qué |
|---|---|---:|---:|---|
| **Completa** | *(ninguno)* | 404 | 86,5% | Punto de partida recomendado |
| **Reducida** | `.reducida` | 355 | 83,8% | Endurecer tras rodar el canal de excepciones |
| **Mínima** | `.minima` | 125 | 73,1% | Lista cerrada; todo lo demás por excepción |

**Perfil** — una política para un tipo de usuario, no un escalón más. No se deriva del
inventario y no tiene por qué encajar en la escalera de arriba.

| Perfil | Sufijo | Entradas | Para quién |
|---|---|---:|---|
| **Vibecoding** | `.vibecoding` | 71 | Gente que no programa y trabaja con Copilot |

Comparativa completa y recomendación: **[COMPARATIVA.md](COMPARATIVA.md)**.

Todas comparten la misma política de IA: **solo Copilot y lo que publique Microsoft**.

### El perfil Vibecoding

Pensado para quien no es desarrollador y se apoya en el asistente. Contiene:

- **Copilot y Copilot Chat**, que es el motivo de que estos usuarios abran el editor.
- **Todo lo oficial de Microsoft y GitHub** por publisher, así que Python, Jupyter,
  contenedores, remoto, Codespaces y Pull Requests entran sin listarlos uno a uno.
- **Git**: GitLens, Git Graph, Git History y plantillas `.gitignore`.
- **Trece básicos**: formateo automático (Prettier), el error visible en la propia línea
  (Error Lens), corrector ortográfico con diccionario español, EditorConfig,
  autocompletado de rutas, Markdown con diagramas Mermaid, Draw.io, previsualización web
  (Live Server) y lectura de datos (CSV, hojas de cálculo, PDF).
- **`win-ca`**, sin el cual TLS falla detrás del proxy corporativo.

Fuera queda todo lo demás: fabricantes de stacks, lenguajes de nicho, cadenas de
compilación, depuradores especializados, clientes de base de datos y, por supuesto,
cualquier IA que no sea Copilot.

No se construye a partir de quién usa qué hoy: **estos usuarios todavía no están en el
inventario**. La lista sale de lo que necesita alguien que escribe con un asistente, no
de la telemetría de la flota.

## Ficheros por nivel

Sustituye `<sufijo>` por el de la tabla (vacío para Completa):

| Fichero | Para qué sirve |
|---|---|
| `extensions.allowed<sufijo>.jsonc` | Versión anotada, con secciones y usuarios por entrada. **Es la que se revisa y se versiona.** |
| `extensions.allowed<sufijo>.json` | Misma política en JSON estricto, para pegar en `settings.json` o automatizar |
| `IMPACTO<sufijo>.md` | Qué se rompe si se despliega tal cual, medido sobre la flota actual |
| `impacto_usuarios<sufijo>.csv` | Usuarios afectados y qué pierde cada uno, para avisar antes |

Regenerar los tres: `python build_policy.py`

## Cómo funciona

VS Code resuelve `extensions.allowed` de lo más específico a lo más general: primero busca
el ID completo (`publisher.extension`), luego el publisher, y por último el comodín `*`.

```jsonc
{
  "extensions.allowed": {
    "ms-python": true,                  // todo el publisher, cualquier versión
    "esbenp.prettier-vscode": "stable", // solo versiones estables (bloquea pre-release)
    "tabnine.tabnine-vscode": false,    // denegada explícitamente
    "*": false                          // todo lo no listado, bloqueado
  }
}
```

También admite fijar versiones concretas (`["3.0.0", "4.2.3"]`) y versiones por plataforma
(`["5.0.0@win32-x64"]`), útil si en algún momento hay que congelar una extensión conflictiva.

Requiere **VS Code 1.96 o superior**. Las extensiones ya instaladas que dejen de estar
permitidas se deshabilitan; no se desinstalan solas.

## Criterio de construcción

1. **Microsoft y GitHub** (`true`, cualquier versión): todos los publishers `ms-*` más los
   equipos de producto de Microsoft que publican con otro ID (`vscjava`,
   `visualstudioexptteam`, `powerquery`, `teamsdevapp`, `analysis-services`…) y `github`.
2. **Fabricantes de los stacks corporativos** (`true`): Red Hat, IBM, Zowe, Broadcom,
   Oracle, Salesforce, SAP, Snowflake, Docker, HashiCorp, SonarSource, VMware (Spring),
   Angular, Vue, GraphQL, PlatformIO. Mismo motivo que Microsoft: son el proveedor del
   lenguaje o la plataforma sobre la que se trabaja.
3. **Extensiones con capacidad de trabajo** (`"stable"`): lenguajes, depuradores,
   linters, formateadores, tests, control de versiones y acceso a datos. En **Mínima**
   esta vía está desactivada: solo entra lo curado a mano.
4. **Denegación explícita** (`false`): toda la IA que no sea Copilot ni Microsoft.

Los niveles se definen en `TIERS`, y las extensiones curadas viven en
`CURATED_BY_GROUP` agrupadas por capacidad (`cadena`, `lenguajes`, `depuracion`, `red`,
`pruebas`, `vcs`, `datos`, `python`, `web_api`, `docs`, `stack`). Cada nivel declara qué
grupos incluye, así que **añadir una extensión al grupo correcto la coloca sola en su
nivel** — no hay que mantener tres listas.

### Qué entra y qué no

**El número de usuarios no decide nada.** Un solo especialista de robótica necesita su
extensión de KUKA KRL tanto como los 59 usuarios de Rainbow CSV necesitan la suya, y un
tema con 34 usuarios no lo necesita nadie para trabajar.

| Entra | No entra |
|---|---|
| Soporte de lenguaje | Temas e iconos |
| Depuradores | Snippets |
| Linters y formateadores | Packs de extensiones |
| Tests | Atajos de teclado |
| Control de versiones | Previsualizadores que duplican funciones ya integradas |
| Acceso a datos y clientes de API | Deprecadas |
| Documentación y diagramas | IA que no sea Copilot ni Microsoft |

La clasificación sale de las categorías del marketplace, que **no son fiables en ningún
sentido**, así que dos listas curadas corrigen sus fallos conocidos:

- `WORK_TOOLS_UNCATEGORISED` — herramientas de trabajo que el marketplace mete en
  «Other»: Git Graph, Error Lens, el visor de SQLite, Test Explorer, `win-ca`…
- `COSMETIC_DENIED` — cosmética que se cuela en una categoría de trabajo: Better Comments
  se declara «Formatters» pero solo colorea comentarios.

Una extensión que declare `Themes` **no** queda vetada si además aporta capacidad: la de
KUKA KRL incluye un tema de color, y vetarla por eso dejaba tirado al único especialista
que la usa.

### Revisión manual pendiente

`IMPACTO.md` lista dos conjuntos que la regla no puede decidir sola:

- **Sin categorías declaradas** — su manifiesto no las trae. Quedan bloqueadas; hay que
  mirarlas una a una.
- **Permitidas pero sin repositorio** — aportan capacidad, así que entran, pero no se
  puede auditar su código ni seguir sus CVE. No se bloquean automáticamente porque varias
  son de fabricantes reales (Rocket COBOL, Parasoft, Tenable, Fanuc) y bloquearlas pararía
  a un especialista.

### Política de IA

**Solo GitHub Copilot y lo que publique Microsoft.** Copilot y Copilot Chat entran por el
publisher `github`; IntelliCode, Azure MCP Server, Copilot for Azure y la modernización de
Java entran por los publishers de Microsoft.

Todo lo demás está denegado, **incluidos los asistentes de fabricantes cuyo publisher sí
está permitido** para el resto de sus extensiones (Anthropic, Google, AWS, Salesforce).
Esos solo quedan bloqueados gracias a su entrada por ID: sin ella, la regla de publisher
los dejaría pasar. Si se añade un fabricante nuevo a `VENDOR_PUBLISHERS`, hay que revisar
si publica algún asistente y denegarlo por ID.

Una comprobación en `build_policy.py` aborta la generación si alguna entrada de
`ESSENTIAL_EXTENSIONS` resulta ser una extensión con IA.

## Despliegue en Windows (GPO / Intune)

La política se llama `AllowedExtensions` y escribe en
`HKEY_LOCAL_MACHINE\Software\Policies\Microsoft\VSCode`. El valor es el objeto JSON de
`extensions.allowed<sufijo>.json` (solo el objeto interno, sin la clave que lo envuelve).

**Group Policy:**

1. Coger las plantillas ADMX/ADML de la carpeta `policies` de la instalación de VS Code
   (se incluyen desde la 1.69) y copiarlas al Central Store del dominio.
2. `gpedit.msc` → *Computer Configuration* → *Administrative Templates* → *Visual Studio
   Code* → **Allowed Extensions**, y pegar el contenido de `extensions.allowed.json`
   (solo el objeto interno, sin la clave `extensions.allowed`).

**Intune:** configurar la misma política `AllowedExtensions` mediante el catálogo de
configuración o una plantilla administrativa, con el objeto JSON como valor. El formato
exacto lo define el ADMX de la versión de VS Code que tengáis desplegada: conviene
verificarlo ahí antes de publicar la asignación.

**Alternativa sin políticas:** el mismo objeto vale en el `settings.json` de máquina, pero
un usuario con permisos puede editarlo. Para que sea vinculante, GPO.

> En macOS el mecanismo equivalente son perfiles `.mobileconfig` (VS Code trae ejemplos en
> `Contents/Resources/app/policies` desde la 1.99). No se ha generado aquí porque toda la
> flota inventariada es Windows.

## Antes de desplegar

1. Leer `IMPACTO.md`: cuántos usuarios pierden algo y qué.
2. Comunicar el cambio de IA. Es el impacto más visible: **50 usuarios** pierden un
   asistente que usan hoy (Claude Code 28, Codex 22, y el resto de proveedores). Conviene
   anunciar Copilot como la alternativa antes de aplicar la política, no después.
3. Avisar a los usuarios de `impacto_usuarios.csv` que pierden 5 o más extensiones.
4. Piloto con un grupo pequeño antes de aplicar a toda la flota.
5. Revisar las dos listas de «revisión manual pendiente» de `IMPACTO.md`.
6. Definir un canal de excepciones: quién aprueba añadir una extensión y quién regenera
   la política.

## Mantenimiento

La política caduca en cuanto cambia la flota. Al repetir el inventario:

```bash
python clean_extensions.py   # depura el CSV nuevo
python build_policy.py       # política + impacto actualizados
python build_report.py       # informe de la flota (lee la política para el apartado de riesgo)
python verify.py             # comprueba resolución, invariantes por nivel y HTML
```

El orden importa: `build_report.py` lee `policy/extensions.allowed.json` para calcular
cuánto riesgo cubre ya la política. Si aún no existe, esa columna sale vacía.

Ajustes habituales en `build_policy.py`:

| Quiero… | Dónde |
|---|---|
| Permitir un fabricante entero | `VENDOR_PUBLISHERS` / `EXTENDED_VENDORS` / `CORE_VENDORS` |
| Permitir una extensión concreta | el grupo que corresponda en `CURATED_BY_GROUP` |
| Bloquear cosmética que se cuela por su categoría | `COSMETIC_DENIED` |
| Cambiar qué capacidades cuentan | `WORK_CATEGORIES` o `Tier.categories` |
| Cambiar qué incluye un nivel | `TIERS` (campo `groups`) |
| Decidir sobre un asistente de IA | `AI_DENIED` / `AI_APPROVED` |
