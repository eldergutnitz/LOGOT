# Impacto de la politica de extensiones permitidas - REDUCIDA

> Desarrollo, pruebas y acceso a datos, ademas del control de versiones que llevan todos los niveles. Fuera quedan documentacion, diagramas, clientes de API, los fabricantes secundarios y todo lo que no declara repositorio.

_Simulado el 30/07/2026 sobre el inventario limpio (5.466 instalaciones, 523 usuarios)._

## Resultado

- **4.583 de 5.466 instalaciones (83,8%) siguen permitidas.**
- **883 instalaciones** de **356 extensiones** quedarian bloqueadas.
- **243 de 523 usuarios (46%)** perderian al menos una extension.
- 46 usuarios perderian 5 o mas: contactar antes del despliegue (ver `impacto_usuarios.reducida.csv`).

Se permite por capacidad, no por implantacion: una extension entra aunque la use una sola persona. Categorias que cuentan en este nivel: Debuggers, Formatters, Languages, Linters, Programming Languages, SCM Providers, Testing. Lo bloqueado es aspecto (temas, iconos, cosmetica), snippets y packs, previsualizadores que duplican funciones ya integradas, extensiones deprecadas, y toda la IA que no sea Copilot ni Microsoft. Ademas se exige repositorio declarado: lo que no se puede auditar, no entra.

El detalle por usuario esta en `impacto_usuarios.reducida.csv` para avisar o tramitar excepciones antes de aplicar.

## Asistentes de IA

**Politica: solo GitHub Copilot y lo que publique Microsoft.** Todo lo demas queda denegado, incluidos los asistentes de fabricantes cuyo publisher si esta permitido para el resto de sus extensiones.

| Extension | Proveedor | Usuarios que lo pierden |
|---|---|---:|
| `anthropic.claude-code` | Claude Code (Anthropic) | 28 |
| `openai.chatgpt` | Codex (OpenAI) | 22 |
| `salesforce.salesforcedx-einstein-gpt` | Agentforce Vibes (Salesforce) | 8 |
| `continue.continue` | Continue (agente open-source, modelo a eleccion del usuario) | 6 |
| `google.geminicodeassist` | Gemini Code Assist (Google) | 5 |
| `mintlify.document` | Mintlify: genera documentacion enviando el codigo a su API | 5 |
| `saoudrizwan.claude-dev` | Cline | 4 |
| `sourcery.sourcery` | Sourcery | 4 |
| `amazonwebservices.amazon-q-vscode` | Amazon Q (AWS) | 2 |
| `blackboxapp.blackbox` | Blackbox | 2 |
| `blackboxapp.blackboxagent` | Blackbox | 2 |
| `codeium.codeium` | Windsurf / Codeium | 2 |
| `danielsanmedium.dscodegpt` | CodeGPT | 2 |
| `tabnine.tabnine-vscode` | Tabnine | 2 |
| `leonkohli.snapsource` | Copy4AI: exporta codigo a servicios externos | 2 |
| `google.gemini-cli-vscode-ide-companion` | Gemini CLI Companion (Google) | 1 |
| `codeium.codeium-enterprise-updater` | Windsurf / Codeium | 1 |
| `danlambiase.lmstudio-copilot-provider` | modelos locales LM Studio | 1 |
| `mistralai.mistral-vibe-code` | Mistral | 1 |
| `ollama.ollama` | modelos locales Ollama | 1 |
| `silasnevstad.gpthelper` | GPT Helper | 1 |
| `supermaven.supermaven` | Supermaven | 1 |
| `zoocodeorganization.zoo-code` | Zoo Code | 1 |
| `andrepimenta.claude-code-chat` | cliente Claude de terceros | 1 |

### Sin categorias declaradas: revisar a mano

La regla permite por capacidad, y estas extensiones no declaran ninguna categoria en su manifiesto. Quedan bloqueadas por defecto, pero puede haber herramientas de trabajo entre ellas: añadirlas a `WORK_TOOLS_UNCATEGORISED` si lo son.

| Extension | Nombre | Usuarios |
|---|---|---:|
| `satoshiyamamoto.vscode-line-number` | Line Number | 1 |
| `googlecloudtools.datacloud` | Google Cloud Data Agent Kit | 1 |

### Extensiones con IA permitidas por la regla de publisher

Entran porque su fabricante esta permitido al completo. No las bloquea nada; figuran aqui para que su presencia sea una decision y no un efecto colateral. Para excluir alguna, basta una entrada propia en `false`: la clave del ID concreto gana sobre la del publisher.

| Extension | Clasificacion | Usuarios |
|---|---|---:|
| `github.copilot-chat` | Asistente de codigo IA | 60 |
| `visualstudioexptteam.vscodeintellicode` | Asistente de codigo IA | 25 |
| `github.copilot` | Asistente de codigo IA | 17 |
| `ms-azuretools.vscode-azure-github-copilot` | Asistente de codigo IA | 9 |
| `ms-azuretools.vscode-azure-mcp-server` | Servidor MCP | 9 |
| `vscjava.migrate-java-to-azure` | Asistente de codigo IA | 6 |
| `vscjava.vscode-java-upgrade` | Asistente de codigo IA | 4 |
| `analysis-services.powerbi-modeling-mcp` | Servidor MCP | 4 |

## Extensiones bloqueadas con mas usuarios (top 30 de 356)

Revisar esta tabla es lo que decide si hace falta ampliar la lista blanca.

| Extension | ID | Usuarios | Instalaciones |
|---|---|---:|---:|
| Live Server | `ritwickdey.liveserver` | 38 | 38 |
| Material Icon Theme | `pkief.material-icon-theme` | 34 | 34 |
| Claude Code for VS Code | `anthropic.claude-code` | 28 | 28 |
| Codex – OpenAI’s coding agent | `openai.chatgpt` | 22 | 22 |
| Python Environment Manager (deprecated) | `donjayamanne.python-environment-manager` | 19 | 19 |
| Python Extension Pack | `donjayamanne.python-extension-pack` | 19 | 19 |
| indent-rainbow | `oderwat.indent-rainbow` | 17 | 17 |
| json | `zainchen.json` | 17 | 17 |
| vscode-icons | `vscode-icons-team.vscode-icons` | 15 | 15 |
| Open in External App | `yutengjing.open-in-external-app` | 12 | 12 |
| Better Comments | `aaron-bond.better-comments` | 10 | 10 |
| Markdown Preview Enhanced | `shd101wyy.markdown-preview-enhanced` | 9 | 9 |
| One Dark Pro | `zhuangtongfa.material-theme` | 9 | 9 |
| Prettify JSON | `mohsen1.prettify-json` | 8 | 8 |
| Agentforce Vibes | `salesforce.salesforcedx-einstein-gpt` | 8 | 8 |
| Project Manager | `alefragnani.project-manager` | 7 | 7 |
| Tokyo Night | `enkia.tokyo-night` | 7 | 7 |
| Spreadsheet Viewer | `grapecity.gc-excelviewer` | 7 | 7 |
| JavaScript (ES6) code snippets | `xabikos.javascriptsnippets` | 7 | 7 |
| Markdown Preview Mermaid Support | `bierner.markdown-mermaid` | 6 | 6 |
| npm Intellisense | `christian-kohler.npm-intellisense` | 6 | 6 |
| Continue - open-source AI code agent | `continue.continue` | 6 | 6 |
| Python Preview | `dongli.python-preview` | 6 | 6 |
| Git Extension Pack | `donjayamanne.git-extension-pack` | 6 | 6 |
| Apex Log Analyzer | `financialforce.lana` | 6 | 6 |
| Html Preview | `george-alisson.html-preview-vscode` | 6 | 6 |
| Image preview | `kisstkondoros.vscode-gutter-preview` | 6 | 6 |
| PDF Viewer | `mathematic.vscode-pdf` | 6 | 6 |
| Atom One Dark Theme | `akamud.vscode-theme-onedark` | 5 | 5 |
| Bookmarks | `alefragnani.bookmarks` | 5 | 5 |

## Como ajustar

- Si el marketplace la categoriza mal y es una herramienta de trabajo: añadirla a `WORK_TOOLS_UNCATEGORISED` en `build_policy.py`.
- Si es cosmetica que se cuela por categoria: añadirla a `COSMETIC_DENIED`.
- Para permitirla aunque hoy no la use nadie: `ESSENTIAL_EXTENSIONS`.
- Para permitir un fabricante entero: añadirlo a `VENDOR_PUBLISHERS`.
- Para excluir algo que entra por regla de publisher: añadirlo con valor `False`; la clave del ID concreto gana sobre la del publisher.
- Regenerar con `python build_policy.py && python build_report.py && python verify.py` y volver a revisar este informe.
