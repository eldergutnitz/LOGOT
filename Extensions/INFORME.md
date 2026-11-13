# Inventario de extensiones VS Code — informe

_Generado el 30/07/2026 a partir de `Ext_VCS_FINAL.csv` (14.659 filas)._

## Resumen

- **5.466 instalaciones** limpias de **861 extensiones** distintas.
- **530 de 7.559 equipos** (7,0%) tienen extensiones; 7.029 se inventariaron sin ninguna.
- **523 usuarios** con extensiones: media de 10,3 por usuario (mediana 6, máximo 89).
- **143 usuarios (27%)** usan algún asistente de código con IA.
- **459 extensiones** están instaladas en un único equipo (cola larga).

## Limpieza aplicada

| Problema | Filas | Tratamiento |
|---|---:|---|
| Filas «No se encontraron extensiones» | 7.068 | Separadas a `equipos_sin_extensiones.csv` (pares equipo+usuario) |
| Duplicados equipo+usuario+extensión | 2.114 | Colapsados; se conserva la versión más alta |
| Registros truncados (escritura concurrente) | 5 | Reparados con la ruta de instalación |
| IDs con distinto casing | 1.304 | Normalizados a minúsculas |
| Nombres `%displayName%` sin traducir | 434 | Resueltos por ID (35 quedan derivados) |
| Manifiesto ilegible (ID con versión pegada) | 10 | Separado el ID real |
| Texto con doble codificación | 101 | Reparado (nombres y categorías) |
| Sin repositorio declarado | 112 | Se mantienen con el campo vacío |

## Top 15 extensiones

| # | Extensión | ID | Inst. | Usuarios | Versiones |
|---:|---|---|---:|---:|---:|
| 1 | Python | `ms-python.python` | 351 | 347 | 27 |
| 2 | Pylance | `ms-python.vscode-pylance` | 349 | 345 | 29 |
| 3 | Python Debugger | `ms-python.debugpy` | 345 | 341 | 17 |
| 4 | Python Environments | `ms-python.vscode-python-envs` | 308 | 305 | 20 |
| 5 | Jupyter Keymap | `ms-toolsai.jupyter-keymap` | 92 | 91 | 1 |
| 6 | Jupyter | `ms-toolsai.jupyter` | 89 | 88 | 11 |
| 7 | Jupyter Notebook Renderers | `ms-toolsai.jupyter-renderers` | 89 | 88 | 6 |
| 8 | Jupyter Cell Tags | `ms-toolsai.vscode-jupyter-cell-tags` | 89 | 88 | 2 |
| 9 | Jupyter Slide Show | `ms-toolsai.vscode-jupyter-slideshow` | 89 | 88 | 2 |
| 10 | C/C++ | `ms-vscode.cpptools` | 66 | 66 | 14 |
| 11 | C/C++ Themes | `ms-vscode.cpptools-themes` | 63 | 63 | 1 |
| 12 | GitHub Copilot Chat | `github.copilot-chat` | 61 | 60 | 14 |
| 13 | Rainbow CSV | `mechatroner.rainbow-csv` | 61 | 59 | 3 |
| 14 | CMake Tools | `ms-vscode.cmake-tools` | 61 | 61 | 8 |
| 15 | .NET Install Tool | `ms-dotnettools.vscode-dotnet-runtime` | 58 | 57 | 9 |

## Adopción de IA

143 de 523 usuarios (27%) tienen un asistente de código con IA (220 instalaciones). Hay además 635 instalaciones de herramientas con funciones de IA que no son asistentes (servidores MCP, SDK, integraciones cloud).

| Proveedor | Estado | Instalaciones | Usuarios |
|---|---|---:|---:|
| GitHub | permitido | 97 | 72 |
| Anthropic | **no permitido** | 29 | 28 |
| Microsoft (IntelliCode) | permitido | 25 | 25 |
| OpenAI | **no permitido** | 23 | 23 |
| Salesforce | **no permitido** | 8 | 8 |
| Google | **no permitido** | 6 | 5 |
| Continue | **no permitido** | 6 | 6 |
| Blackbox | **no permitido** | 4 | 3 |
| Sourcery | **no permitido** | 4 | 4 |
| Cline | **no permitido** | 4 | 4 |
| Windsurf/Codeium | **no permitido** | 3 | 3 |
| CodeGPT | **no permitido** | 2 | 2 |
| Tabnine | **no permitido** | 2 | 2 |
| AWS | **no permitido** | 2 | 2 |
| Supermaven | **no permitido** | 1 | 1 |
| Mistral | **no permitido** | 1 | 1 |
| Local (LM Studio) | **no permitido** | 1 | 1 |
| Zoo | **no permitido** | 1 | 1 |
| Local (Ollama) | **no permitido** | 1 | 1 |

> **La política corporativa permite un único asistente de terceros: GitHub Copilot**, más la IA que publique Microsoft. Todo lo demás queda denegado en `policy/`, incluidos los asistentes de fabricantes cuyo resto de extensiones sí están permitidas: cada uno envía código fuente a un tercero distinto.

## Riesgo de seguridad

Triage de exposición a partir del propio inventario. «Cubierto» = cuántas de esas extensiones bloquea ya la política de `policy/`.

| Nivel | Vector | Ext. | Inst. | Usuarios | Cubierto |
|---|---|---:|---:|---:|---:|
| ALTO | Código fuente hacia terceros sin contrato | 22 | 98 | 70 | 22/22 |
| ALTO | Servidores MCP | 5 | 19 | 15 | 3/5 |
| ALTO | Sin procedencia y sin implantación | 79 | 88 | 53 | 36/79 |
| MEDIO | Credenciales y acceso a sistemas | 42 | 316 | 121 | 5/42 |
| MEDIO | Procedencia no verificable | 112 | 348 | 189 | 50/112 |
| MEDIO | Marcadas como deprecadas | 3 | 21 | 20 | 3/3 |

**Software sin parchear es el vector con más alcance.** 2.165 instalaciones (39,6% del total), en 441 usuarios, ejecutan una versión anterior a la más nueva que ya existe en la flota — es decir, por detrás de sus propios compañeros, con la actualización ya validada internamente. Una lista blanca no arregla esto: hace falta activar la actualización automática de extensiones por política.

| Extensión más desactualizada | Inst. por detrás | Versiones en flota |
|---|---:|---:|
| Python (`ms-python.python`) | 347 | 27 |
| Python Debugger (`ms-python.debugpy`) | 343 | 17 |
| Python Environments (`ms-python.vscode-python-envs`) | 307 | 20 |
| Pylance (`ms-python.vscode-pylance`) | 210 | 29 |
| Jupyter (`ms-toolsai.jupyter`) | 88 | 11 |
| Jupyter Notebook Renderers (`ms-toolsai.jupyter-renderers`) | 88 | 6 |
| C/C++ (`ms-vscode.cpptools`) | 64 | 14 |
| CMake Tools (`ms-vscode.cmake-tools`) | 60 | 8 |
| C# (`ms-dotnettools.csharp`) | 45 | 12 |
| Csdevkit (`ms-dotnettools.csdevkit`) | 34 | 6 |

### Exposición concreta

Extensiones detrás de los vectores de nivel alto, por usuarios afectados.

| Extensión | ID | Usuarios | Motivo |
|---|---|---:|---|
| Claude Code for VS Code | `anthropic.claude-code` | 28 | IA no gestionada |
| Codex – OpenAI’s coding agent | `openai.chatgpt` | 22 | IA no gestionada |
| Python Environment Manager (deprecated) | `donjayamanne.python-environment-manager` | 19 | Deprecada |
| Azure MCP Server | `ms-azuretools.vscode-azure-mcp-server` | 9 | Servidor MCP |
| Agentforce Vibes | `salesforce.salesforcedx-einstein-gpt` | 8 | IA no gestionada |
| Continue - open-source AI code agent | `continue.continue` | 6 | IA no gestionada |
| Gemini Code Assist | `google.geminicodeassist` | 5 | IA no gestionada |
| Sourcery | `sourcery.sourcery` | 4 | IA no gestionada |
| Cline | `saoudrizwan.claude-dev` | 4 | IA no gestionada |
| Power BI Modeling MCP Server | `analysis-services.powerbi-modeling-mcp` | 4 | Servidor MCP |
| Datamates | `altimateai.vscode-altimate-mcp-server` | 3 | Servidor MCP |
| Windsurf Plugin (formerly Codeium): AI Coding Autocomplete and Chat for Python, JavaScript, TypeScript, and more | `codeium.codeium` | 2 | IA no gestionada |

> **Alcance.** Este análisis usa solo el inventario: identificadores, versiones, publishers, categorías y repositorios declarados. No consulta CVE ni avisos de seguridad, no comprueba publisher verificado ni firma en el marketplace, y no analiza el código ni el tráfico de las extensiones. «Desactualizada» es relativo a la propia flota, no a la última versión publicada. Sirve para priorizar qué revisar, no para declarar nada seguro.

## Fragmentación de versiones

| Extensión | Versiones | Inst. | Rango |
|---|---:|---:|---|
| Pylance | 29 | 349 | 2023.8.20 → 2026.3.1 |
| Python | 27 | 351 | 2023.8.0 → 2026.5.2026070801 |
| Spanish Language Pack for Visual Studio Code | 21 | 42 | 1.65.3 → 1.130.2026072017 |
| Python Environments | 20 | 308 | 1.0.0 → 1.37.2026072401 |
| Python Debugger | 17 | 345 | 2024.0.0 → 2026.7.12031010 |
| C/C++ | 14 | 66 | 1.18.5 → 1.33.4 |
| GitHub Copilot Chat | 14 | 61 | 0.23.2 → 0.48.1 |
| C# | 12 | 46 | 2.22.3 → 2.146.2 |
| Jupyter | 11 | 89 | 2023.10.1100000000 → 2025.10.2025101002 |
| Claude Code for VS Code | 11 | 28 | 2.1.101 → 2.1.220 |

## Ficheros

- `clean/instalaciones.csv` — 5.466 filas (equipo + usuario + extensión)
- `clean/extensiones.csv` — 861 filas (catálogo agregado)
- `clean/usuarios.csv` — resumen por usuario con uso de IA
- `clean/equipos_sin_extensiones.csv` — 7.029 equipos sin extensiones
- `clean/data_quality.json` — métricas de depuración
- `clean/informe.html` — informe visual autocontenido
- `policy/` — política de extensiones permitidas e informe de impacto

Regenerar (el orden importa: el informe lee la política para el apartado de riesgo):

```bash
python clean_extensions.py
python build_policy.py
python build_report.py
python verify.py
```

> Contiene identificadores de equipo y usuario: tratar como documento interno.
