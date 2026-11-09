# Impacto de la politica de extensiones permitidas - VIBECODING

> Para perfiles que no programan y trabajan apoyados en Copilot. Copilot, todo lo oficial de Microsoft y GitHub, git, y una lista corta de basicos: formateo, errores a la vista, Markdown, previsualizacion web y lectura de datos. Ni fabricantes de stacks, ni lenguajes de nicho, ni cadenas de compilacion. No se deriva del inventario: estos usuarios aun no estan en la flota.

> **Aviso.** Este es un perfil para usuarios nuevos, no un nivel pensado para la flota actual. Las cifras de abajo simulan que pasaria si se aplicase a quienes ya trabajan hoy, y solo sirven para hacerse una idea de lo estrecho que es: no son una medida de su impacto real, porque su publico todavia no esta inventariado.

_Simulado el 30/07/2026 sobre el inventario limpio (5.466 instalaciones, 523 usuarios)._

## Resultado

- **3.457 de 5.466 instalaciones (63,2%) siguen permitidas.**
- **2009 instalaciones** de **717 extensiones** quedarian bloqueadas.
- **308 de 523 usuarios (59%)** perderian al menos una extension.
- 116 usuarios perderian 5 o mas: contactar antes del despliegue (ver `impacto_usuarios.vibecoding.csv`).

Este nivel no permite nada por categoria: la lista es cerrada. Entran Microsoft, GitHub, los fabricantes de los stacks corporativos y las extensiones curadas de lenguaje, lint, formato y depuracion. Cualquier otra cosa, incluido un lenguaje de nicho legitimo, tendra que pedirse por el canal de excepciones. Lo bloqueado es aspecto (temas, iconos, cosmetica), snippets y packs, previsualizadores que duplican funciones ya integradas, extensiones deprecadas, y toda la IA que no sea Copilot ni Microsoft.

El detalle por usuario esta en `impacto_usuarios.vibecoding.csv` para avisar o tramitar excepciones antes de aplicar.

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
| `bitlang.cobol` | Cobol | 4 |
| `dart-code.dart-code` | Dart Code | 2 |
| `lochbrunner.vscode-hdf5-viewer` | HDF5 Preview | 2 |
| `satoshiyamamoto.vscode-line-number` | Line Number | 1 |
| `googlecloudtools.datacloud` | Google Cloud Data Agent Kit | 1 |
| `philschatz.vscode-xslt` | XSLT Interactive Debugger | 1 |
| `gordonwalkedby.vbnet` | VB.NET Grammars and Snippets | 1 |
| `typescriptteam.native-preview` | TypeScript 7 | 1 |
| `saposs.sap-ux-sap-systems-ext` | Connection Manager for SAP Systems | 1 |
| `bscan.perlnavigator` | Perl Navigator | 1 |
| `flix.flix` | flix | 1 |

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

## Extensiones bloqueadas con mas usuarios (top 30 de 717)

Revisar esta tabla es lo que decide si hace falta ampliar la lista blanca.

| Extension | ID | Usuarios | Instalaciones |
|---|---|---:|---:|
| Material Icon Theme | `pkief.material-icon-theme` | 34 | 34 |
| Claude Code for VS Code | `anthropic.claude-code` | 28 | 28 |
| autoDocstring - Python Docstring Generator | `njpwerner.autodocstring` | 27 | 27 |
| Django | `batisteo.vscode-django` | 24 | 24 |
| Python Indent | `kevinrose.vsc-python-indent` | 24 | 24 |
| YAML | `redhat.vscode-yaml` | 23 | 23 |
| Codex – OpenAI’s coding agent | `openai.chatgpt` | 22 | 22 |
| Language Support for Java(TM) by Red Hat | `redhat.java` | 22 | 22 |
| XML | `redhat.vscode-xml` | 22 | 22 |
| CMake | `twxs.cmake` | 20 | 20 |
| Jinja | `wholroyd.jinja` | 20 | 20 |
| Python Environment Manager (deprecated) | `donjayamanne.python-environment-manager` | 19 | 19 |
| Python Extension Pack | `donjayamanne.python-extension-pack` | 19 | 19 |
| XML Tools | `dotjoshjohnson.xml` | 19 | 19 |
| IBM Db2 for z/OS Developer Extension | `ibm.db2forzosdeveloperextension` | 18 | 18 |
| indent-rainbow | `oderwat.indent-rainbow` | 17 | 17 |
| json | `zainchen.json` | 17 | 17 |
| markdownlint | `davidanson.vscode-markdownlint` | 16 | 16 |
| ESLint | `dbaeumer.vscode-eslint` | 15 | 15 |
| Code Runner | `formulahendry.code-runner` | 15 | 15 |
| vscode-icons | `vscode-icons-team.vscode-icons` | 15 | 15 |
| HTML CSS Support | `ecmel.vscode-html-css` | 14 | 14 |
| Debugger for Firefox | `firefox-devtools.vscode-firefox-debug` | 14 | 14 |
| Snowflake | `snowflake.snowflake-vsc` | 14 | 14 |
| IBM Z Open Editor | `ibm.zopeneditor` | 12 | 12 |
| Open in External App | `yutengjing.open-in-external-app` | 12 | 12 |
| Extension For Zowe | `zowe.vscode-extension-for-zowe` | 12 | 12 |
| PlatformIO IDE | `platformio.platformio-ide` | 11 | 11 |
| CodeLLDB | `vadimcn.vscode-lldb` | 11 | 11 |
| Better Comments | `aaron-bond.better-comments` | 10 | 10 |

## Como ajustar

- Si el marketplace la categoriza mal y es una herramienta de trabajo: añadirla a `WORK_TOOLS_UNCATEGORISED` en `build_policy.py`.
- Si es cosmetica que se cuela por categoria: añadirla a `COSMETIC_DENIED`.
- Para permitirla aunque hoy no la use nadie: `ESSENTIAL_EXTENSIONS`.
- Para permitir un fabricante entero: añadirlo a `VENDOR_PUBLISHERS`.
- Para excluir algo que entra por regla de publisher: añadirlo con valor `False`; la clave del ID concreto gana sobre la del publisher.
- Regenerar con `python build_policy.py && python build_report.py && python verify.py` y volver a revisar este informe.
