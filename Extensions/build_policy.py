"""Genera la politica de extensiones permitidas (extensions.allowed) para VS Code.

Entrada : clean/instalaciones.csv (salida de clean_extensions.py)
Salida  : policy/extensions.allowed.json    politica estricta, desplegable
          policy/extensions.allowed.jsonc   misma politica anotada, para revision
          policy/IMPACTO.md                 analisis de impacto sobre la flota actual
          policy/impacto_usuarios.csv       usuarios afectados, para comunicacion previa

La politica es deny-by-default ("*": false). Se permite en tres niveles:
  1. Publisher completo  -> Microsoft, GitHub y los fabricantes de los stacks corporativos.
  2. Extension concreta  -> las que aportan una capacidad de trabajo (lenguaje,
                            depuracion, lint, formato, tests, VCS, datos), sin mirar
                            cuantas personas las usan.
  3. Denegacion explicita-> toda la IA que no sea Copilot ni Microsoft (documenta la
                            intencion, y es lo unico que frena a la IA de un fabricante
                            cuyo publisher si esta permitido).
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "clean"
POLICY_DIR = BASE_DIR / "policy"

# Servidores MCP: exponen herramientas y datos internos a un agente de IA.
MCP_PATTERN = re.compile(r"\bmcp\b|-mcp|mcp-")

# Se permite por CAPACIDAD, no por cuantos la usen. El numero de usuarios no decide:
# un unico especialista de robotica con la extension de KUKA KRL la necesita tanto como
# los 59 usuarios de Rainbow CSV, y un tema con 34 usuarios no lo necesita nadie.
#
# Entra si aporta una capacidad de trabajo:
WORK_CATEGORIES = {
    "Programming Languages",
    "Languages",
    "Debuggers",
    "Linters",
    "Formatters",
    "Testing",
    "SCM Providers",
    "Data Science",
    "Notebooks",
}

# Aspecto, no capacidad: por si sola no abre la puerta. Pero no veta: hay extensiones
# de lenguaje que declaran "Themes" solo porque incluyen un tema de color.
VISUAL_CATEGORIES = {"Themes"}

# El taxonomia del marketplace no es fiable en ningun sentido, asi que hay dos listas
# curadas que corrigen sus fallos conocidos:
#   - WORK_TOOLS_UNCATEGORISED: herramientas de trabajo que el marketplace mete en "Other".
#   - COSMETIC_DENIED: cosmetica que se cuela en una categoria de trabajo.

# --- Nivel 1: publishers de confianza -------------------------------------------------

# Publishers de Microsoft con prefijo ms-* presentes en la flota.
MICROSOFT_PUBLISHERS = [
    "microsoft",
    "ms-azure-load-testing",
    "ms-azureaispeech",
    "ms-azuretools",
    "ms-ceintl",
    "ms-copilotstudio",
    "ms-dotnettools",
    "ms-edgedevtools",
    "ms-kubernetes-tools",
    "ms-mssql",
    "ms-ossdata",
    "ms-playwright",
    "ms-python",
    "ms-sarifvscode",
    "ms-toolsai",
    "ms-vscode",
    "ms-vscode-remote",
    "ms-vsliveshare",
    "ms-windows-ai-studio",
]

# Equipos de producto de Microsoft que publican con otro ID de publisher.
# Verificar en el marketplace antes de ampliar esta lista.
MICROSOFT_PRODUCT_TEAMS = [
    "analysis-services",     # Power BI / Analysis Services
    "microsoft-isvexptools",  # Power Platform Tools
    "powerappstools",
    "powerquery",
    "teamsdevapp",           # Microsoft 365 Agents Toolkit
    "visualstudioexptteam",  # IntelliCode
    "visualstudiotoolsforunity",
    "vscjava",               # equipo Java de Microsoft
]

# Fabricantes de los stacks corporativos. Se permiten al completo por el mismo motivo
# que Microsoft: son el proveedor del lenguaje o la plataforma sobre la que se trabaja.
# Su IA propia queda denegada aparte, por ID (la clave del ID gana sobre la del publisher).
VENDOR_PUBLISHERS = [
    "amazonwebservices",
    "angular",
    "atlassian",
    "broadcommfd",   # COBOL / mainframe
    "dbtlabsinc",
    "docker",
    "dynatrace",
    "figma",
    "google",
    "googlecloudtools",
    "grapecity",
    "graphql",
    "hashicorp",
    "ibm",
    "oracle",
    "platformio",
    "postman",
    "redhat",
    "salesforce",
    "sapos",
    "saposs",
    "sapse",
    "snowflake",
    "sonarsource",
    "unity",
    "vmware",        # Spring Boot Tools
    "vue",
    "zowe",
]

# --- Nivel 2: asistentes de IA --------------------------------------------------------

# Politica de IA: solo GitHub Copilot y lo que publique Microsoft. Todo lo demas, denegado.
#   - Copilot y Copilot Chat entran por el publisher "github".
#   - La IA de Microsoft (IntelliCode, Azure MCP Server, Copilot for Azure, modernizacion
#     de Java) entra por los publishers ms-* y equipos de producto.
# Esta lista queda vacia a proposito: no hay ningun asistente aprobado fuera de ahi.
AI_APPROVED: dict[str, str] = {}

# Denegados. El "*": false ya los bloquearia, pero listarlos deja constancia de la
# decision y sobrevive a que alguien afloje la politica mas adelante. Los que pertenecen
# a un publisher permitido (google, salesforce, amazonwebservices, anthropic) SOLO se
# bloquean gracias a estas entradas por ID.
AI_DENIED = {
    "anthropic.claude-code": "Claude Code (Anthropic)",
    "openai.chatgpt": "Codex (OpenAI)",
    "google.geminicodeassist": "Gemini Code Assist (Google)",
    "google.gemini-cli-vscode-ide-companion": "Gemini CLI Companion (Google)",
    "amazonwebservices.amazon-q-vscode": "Amazon Q (AWS)",
    "salesforce.salesforcedx-einstein-gpt": "Agentforce Vibes (Salesforce)",
    "blackboxapp.blackbox": "Blackbox",
    "blackboxapp.blackboxagent": "Blackbox",
    "codeium.codeium": "Windsurf / Codeium",
    "codeium.codeium-enterprise-updater": "Windsurf / Codeium",
    "danielsanmedium.dscodegpt": "CodeGPT",
    "danlambiase.lmstudio-copilot-provider": "modelos locales LM Studio",
    "mistralai.mistral-vibe-code": "Mistral",
    "ollama.ollama": "modelos locales Ollama",
    "saoudrizwan.claude-dev": "Cline",
    "silasnevstad.gpthelper": "GPT Helper",
    "sourcery.sourcery": "Sourcery",
    "supermaven.supermaven": "Supermaven",
    "tabnine.tabnine-vscode": "Tabnine",
    "zoocodeorganization.zoo-code": "Zoo Code",
    "andrepimenta.claude-code-chat": "cliente Claude de terceros",
    "leonkohli.snapsource": "Copy4AI: exporta codigo a servicios externos",
    "continue.continue": "Continue (agente open-source, modelo a eleccion del usuario)",
    "mintlify.document": "Mintlify: genera documentacion enviando el codigo a su API",
}

# Ya no queda ninguna decision de IA abierta: la politica es Copilot y Microsoft.
AI_PENDING: dict[str, str] = {}

# --- Nivel 3: extensiones permitidas por decision, agrupadas por capacidad -----------

# Cada grupo es una capacidad. Los niveles de politica (ver TIERS) eligen que grupos
# entran, asi que anadir una extension al grupo correcto la coloca sola en su nivel.
#
# Aqui van dos cosas que la regla por categorias no resuelve sola:
#   - herramientas de trabajo que el marketplace deja en "Other" (Git Graph, win-ca...),
#   - la cadena estandar, que se permite aunque hoy no la tenga instalada nadie.
CURATED_BY_GROUP: dict[str, dict[str, str]] = {
    "cadena": {
        "dbaeumer.vscode-eslint": "ESLint",
        "esbenp.prettier-vscode": "Prettier",
        "charliermarsh.ruff": "Ruff (lint/format Python)",
        "davidanson.vscode-markdownlint": "markdownlint",
        "timonwong.shellcheck": "ShellCheck",
        "editorconfig.editorconfig": "EditorConfig",
        "streetsidesoftware.code-spell-checker": "Code Spell Checker",
        "streetsidesoftware.code-spell-checker-spanish": "diccionario espanol del corrector",
        "usernamehw.errorlens": "diagnosticos en linea",
        "cheshirekow.cmake-format": "formateador de CMake",
        "taoklerks.poor-mans-t-sql-formatter-vscode": "formateador T-SQL",
    },
    "lenguajes": {
        "rust-lang.rust-analyzer": "Rust",
        "tamasfe.even-better-toml": "TOML",
        "twxs.cmake": "sintaxis CMake",
        "batisteo.vscode-django": "Django",
        "wholroyd.jinja": "plantillas Jinja",
        "samuelcolvin.jinjahtml": "plantillas Jinja en HTML",
        "ecmel.vscode-html-css": "HTML CSS Support",
        "dotjoshjohnson.xml": "XML Tools",
        "reditorsupport.r": "R",
        "reditorsupport.r-syntax": "sintaxis R",
        "slevesque.shader": "lenguajes de shader",
        "jianfajun.dax-language": "DAX (Power BI)",
        "huyza.dax-language": "DAX (Power BI)",
        # Sin categorias declaradas: su manifiesto no se pudo leer
        "dart-code.dart-code": "lenguaje Dart (Flutter depende de el)",
        "bitlang.cobol": "lenguaje COBOL",
        "gordonwalkedby.vbnet": "gramatica VB.NET",
        "typescriptteam.native-preview": "TypeScript 7 (preview nativo)",
        "flix.flix": "lenguaje Flix",
        "bscan.perlnavigator": "servidor de lenguaje Perl",
        "bpruitt-goddard.mermaid-markdown-syntax-highlighting": "sintaxis Mermaid",
        # Robotica industrial y automocion: un solo especialista, pero sin esto no trabaja
        "fanuc.karel-for-fanuc-robot": "lenguaje KAREL de robots FANUC",
        # Cadenas de compilacion
        "fougas.msys2": "soporte MSYS2 / MinGW / Clang",
        "chipcode-nl.gcc-arm-windows": "toolchain ARM para Windows",
        "brapifra.c-compiler": "compilador C",
    },
    "depuracion": {
        "vadimcn.vscode-lldb": "CodeLLDB",
        "firefox-devtools.vscode-firefox-debug": "depurador de Firefox",
        "philschatz.vscode-xslt": "depurador XSLT",
        "bmc.devx-workbench-code-debug": "depuracion BMC DevX (mainframe)",
        "furkansalk.qemu-gdb-debug": "depuracion QEMU + GDB",
        "mcu-debug.memory-view": "vista de memoria en depuracion embebida",
        "mcu-debug.rtos-views": "vistas de RTOS en depuracion embebida",
        "mcu-debug.debug-tracker-vscode": "seguimiento de sesiones de depuracion",
    },
    "red": {
        # Sin esto, TLS falla detras del proxy corporativo que inspecciona certificados
        "ukoloff.win-ca": "inyecta los certificados CA de Windows",
    },
    "pruebas": {
        "hbenl.vscode-test-explorer": "Test Explorer UI",
        "littlefoxteam.vscode-python-test-adapter": "explorador de tests Python",
        "vitest.explorer": "Vitest",
        "simontest.simontest": "generacion de tests unitarios",
    },
    # Control de versiones: entra en TODOS los niveles. Git es parte del trabajo, no un
    # extra. Las extensiones de GitHub (Codespaces, Pull Requests, Actions, CodeQL) ya
    # entran por el publisher "github", permitido en los tres niveles.
    "vcs": {
        "eamodio.gitlens": "GitLens",
        "mhutchie.git-graph": "Git Graph",
        "donjayamanne.githistory": "Git History",
        "codezombiech.gitignore": "plantillas .gitignore",
    },
    # Utilidades de git que aparecieron en el inventario. Van con los perfiles tecnicos:
    # en vibecoding solo estorbarian, porque ahi nadie las ha pedido.
    "vcs_extra": {
        "gxl.git-graph-3": "Git Graph v3",
        "solomonkinard.git-blame": "Git Blame",
        "howardzuo.vscode-git-tags": "etiquetas de Git",
        "git-brain.git-brain": "Git Brain",
        "henriquebruno.github-repository-manager": "gestor de repositorios",
        "ziyasal.vscode-open-in-github": "abrir el fichero en GitHub / GitLab / Bitbucket",
        "mccarter.start-git-bash": "abrir git-bash desde el editor",
        "vsls-contrib.gitdoc": "GitDoc",
        "heroprotagonist.pandiff-vscode": "comparacion enriquecida de textos",
        "atlassian.atlascode": "Bitbucket y Jira (revision de pull requests)",
    },
    "datos": {
        "mechatroner.rainbow-csv": "Rainbow CSV",
        "mtxr.sqltools": "SQLTools",
        "mtxr.sqltools-driver-mssql": "driver SQL Server de SQLTools",
        "mtxr.sqltools-driver-sqlite": "driver SQLite de SQLTools",
        "cweijan.vscode-database-client2": "Database Client",
        "cweijan.dbclient-jdbc": "Database Client (JDBC)",
        "cweijan.vscode-mysql-client2": "cliente MySQL",
        "cweijan.vscode-postgresql-client2": "cliente PostgreSQL",
        "qwtel.sqlite-viewer": "visor SQLite",
        "alexcvzz.vscode-sqlite": "SQLite",
        "dvirtz.parquet-viewer": "visor Parquet",
        "lochbrunner.vscode-hdf5-viewer": "visor de datos HDF5",
    },
    "python": {
        "njpwerner.autodocstring": "generacion de docstrings",
        "kevinrose.vsc-python-indent": "indentacion Python",
        "njqdev.vscode-python-typehint": "type hints",
        "mgesbert.python-path": "rutas de import",
    },
    "web_api": {
        "humao.rest-client": "REST Client",
        "rangav.vscode-thunder-client": "Thunder Client",
        "postman.postman-for-vscode": "Postman",
        "ritwickdey.liveserver": "Live Server",
        "christian-kohler.path-intellisense": "autocompletado de rutas",
        "christian-kohler.npm-intellisense": "autocompletado de paquetes npm",
        "cyrilletuzi.angular-schematics": "schematics de Angular",
        "quicktype.quicktype": "genera tipos a partir de JSON",
    },
    "docs": {
        "yzhang.markdown-all-in-one": "Markdown All in One",
        "bierner.markdown-mermaid": "diagramas Mermaid en Markdown",
        "jebbs.plantuml": "PlantUML",
        "hediet.vscode-drawio": "Draw.io",
        "james-yu.latex-workshop": "LaTeX Workshop",
        "asciidoctor.asciidoctor-vscode": "Asciidoctor",
        "tomoki1207.pdf": "visor PDF",
    },
    # Perfil vibecoding: gente que no programa y se apoya en Copilot. No sale del
    # inventario (esos usuarios aun no existen en la flota), sale de que necesita alguien
    # que escribe con un asistente: ver errores, formatear, previsualizar y leer datos.
    "basicos": {
        "esbenp.prettier-vscode": "formatea el codigo automaticamente",
        "usernamehw.errorlens": "ensena el error en la propia linea",
        "streetsidesoftware.code-spell-checker": "corrector ortografico",
        "streetsidesoftware.code-spell-checker-spanish": "diccionario espanol",
        "editorconfig.editorconfig": "respeta el estilo del repositorio",
        "christian-kohler.path-intellisense": "autocompleta rutas de fichero",
        "yzhang.markdown-all-in-one": "escribir documentacion en Markdown",
        "bierner.markdown-mermaid": "diagramas dentro del Markdown",
        "hediet.vscode-drawio": "diagramas Draw.io",
        "ritwickdey.liveserver": "ver la pagina web en el navegador",
        "mechatroner.rainbow-csv": "leer ficheros CSV",
        "grapecity.gc-excelviewer": "abrir hojas de calculo",
        "tomoki1207.pdf": "leer PDF sin salir del editor",
    },
    "stack": {
        "financialforce.lana": "Apex Log Analyzer (Salesforce)",
        "vignaeshrama.sfdx-package-xml-generator": "generador package.xml (Salesforce)",
        "dbtlabsinc.dbt": "dbt (transformacion de datos)",
        "grapecity.gc-excelviewer": "visor de hojas de calculo",
        "seanmcshane.jar-viewer-and-decompiler": "visor y descompilador de JAR",
    },
}

GROUP_LABELS = {
    "cadena": "Cadena estandar: lint, formato y calidad",
    "lenguajes": "Soporte de lenguaje y cadenas de compilacion",
    "depuracion": "Depuradores",
    "red": "Red corporativa",
    "pruebas": "Pruebas",
    "vcs": "Control de versiones",
    "datos": "Acceso a datos",
    "python": "Autoria en Python",
    "web_api": "Desarrollo web y clientes de API",
    "docs": "Documentacion y diagramas",
    "stack": "Herramientas de stacks corporativos",
    "vcs_extra": "Utilidades adicionales de git",
    "basicos": "Basicos para perfiles no tecnicos",
}

# Cosmetica y redundancias que se cuelan en una categoria de trabajo.
COSMETIC_DENIED = {
    "aaron-bond.better-comments": "colorea comentarios; es aspecto, no capacidad",
    "obenjiro.arrr": "sin proposito identificable",
    "tht13.python": "redundante con la extension oficial de Python de Microsoft",
    "dongli.python-preview": "previsualizador; duplica el depurador",
    "george-alisson.html-preview-vscode": "previsualizador; lo cubre Live Server",
}

# --- Niveles de politica --------------------------------------------------------------

# Fabricantes de los stacks sobre los que se trabaja de verdad.
CORE_VENDORS = [
    "broadcommfd", "docker", "hashicorp", "ibm", "oracle", "redhat", "salesforce",
    "sapos", "saposs", "sapse", "snowflake", "sonarsource", "vmware", "zowe",
]
# Frameworks y plataformas de uso extendido.
EXTENDED_VENDORS = CORE_VENDORS + [
    "amazonwebservices", "angular", "dbtlabsinc", "google", "graphql", "platformio",
    "postman", "vue",
]


@dataclass(frozen=True)
class Tier:
    """Un nivel de restriccion. El nivel completo lleva el sufijo vacio."""

    slug: str
    nombre: str
    resumen: str
    vendors: tuple[str, ...]
    categories: frozenset[str]
    groups: tuple[str, ...]
    require_repository: bool
    # Si es False, solo entra lo curado a mano: nada se permite por categoria.
    auto_include_by_category: bool = True
    # Los niveles de la escalera van de mas a menos permisivo y cada uno es subconjunto
    # del anterior. Un perfil (chain=False) es otra cosa: una lista pensada para un tipo
    # de usuario concreto, que no tiene por que encajar en esa escalera.
    chain: bool = True
    # Un perfil no se deriva del inventario, asi que no se anota cuantos lo usan hoy.
    derived_from_fleet: bool = True

    @property
    def suffix(self) -> str:
        return f".{self.slug}" if self.slug else ""


MINIMAL_GROUPS = ("cadena", "lenguajes", "depuracion", "red", "vcs", "vcs_extra")
REDUCED_GROUPS = MINIMAL_GROUPS + ("pruebas", "datos", "python")
FULL_GROUPS = REDUCED_GROUPS + ("web_api", "docs", "stack")

TIERS = (
    Tier(
        slug="",
        nombre="Completa",
        resumen=(
            "Todo lo que aporta una capacidad de trabajo. Bloquea aspecto, snippets, "
            "packs, deprecadas y la IA no permitida."
        ),
        vendors=tuple(VENDOR_PUBLISHERS),
        categories=frozenset(WORK_CATEGORIES),
        groups=FULL_GROUPS,
        require_repository=False,
    ),
    Tier(
        slug="reducida",
        nombre="Reducida",
        resumen=(
            "Desarrollo, pruebas y acceso a datos, ademas del control de versiones que "
            "llevan todos los niveles. Fuera quedan documentacion, diagramas, clientes de "
            "API, los fabricantes secundarios y todo lo que no declara repositorio."
        ),
        vendors=tuple(EXTENDED_VENDORS),
        categories=frozenset(
            {
                "Programming Languages",
                "Languages",
                "Debuggers",
                "Linters",
                "Formatters",
                "Testing",
                "SCM Providers",
            }
        ),
        groups=REDUCED_GROUPS,
        require_repository=True,
    ),
    Tier(
        slug="minima",
        nombre="Minima",
        resumen=(
            "Git y la cadena de edicion, y poco mas. Nada entra por categoria: solo "
            "Microsoft, GitHub, los fabricantes de los "
            "stacks corporativos y una lista cerrada de lenguaje, lint, formato, "
            "depuracion y control de versiones. Cualquier lenguaje de nicho que no este "
            "en esa lista tendra que pedirse por el canal de excepciones."
        ),
        vendors=tuple(CORE_VENDORS),
        categories=frozenset(
            {"Programming Languages", "Languages", "Debuggers", "Linters", "Formatters"}
        ),
        groups=MINIMAL_GROUPS,
        require_repository=True,
        auto_include_by_category=False,
    ),
    Tier(
        slug="vibecoding",
        nombre="Vibecoding",
        resumen=(
            "Para perfiles que no programan y trabajan apoyados en Copilot. Copilot, todo "
            "lo oficial de Microsoft y GitHub, git, y una lista corta de basicos: "
            "formateo, errores a la vista, Markdown, previsualizacion web y lectura de "
            "datos. Ni fabricantes de stacks, ni lenguajes de nicho, ni cadenas de "
            "compilacion. No se deriva del inventario: estos usuarios aun no estan en la "
            "flota."
        ),
        vendors=(),
        categories=frozenset(),
        groups=("basicos", "vcs", "red"),
        require_repository=True,
        auto_include_by_category=False,
        chain=False,
        derived_from_fleet=False,
    ),
)


def curated_for(tier: Tier) -> dict[str, str]:
    """Extensiones curadas que entran en este nivel, con su motivo."""
    allowed: dict[str, str] = {}
    for group in tier.groups:
        allowed.update(CURATED_BY_GROUP[group])
    return allowed


def read_installations() -> list[dict]:
    with (CLEAN_DIR / "instalaciones.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def build_policy(installations: list[dict], tier: Tier) -> tuple[dict, dict]:
    """Devuelve (politica, contexto) donde contexto lleva los datos para el informe."""
    curated = curated_for(tier)
    trusted = set(MICROSOFT_PUBLISHERS) | set(MICROSOFT_PRODUCT_TEAMS) | set(tier.vendors)
    trusted.add("github")

    users_by_ext: dict[str, set[str]] = defaultdict(set)
    installs_by_ext: Counter = Counter()
    names: dict[str, str] = {}
    ai_class: dict[str, str] = {}
    categories_by_ext: dict[str, str] = {}
    repos_by_ext: dict[str, str] = {}
    for row in installations:
        extension_id = row["ExtensionId"]
        users_by_ext[extension_id].add(row["Usuario"].lower())
        installs_by_ext[extension_id] += 1
        names[extension_id] = row["Nombre"]
        ai_class[extension_id] = row["ClasificacionIA"]
        categories_by_ext[extension_id] = row["Categorias"]
        repos_by_ext[extension_id] = row["Repositorio"]

    explicit = set(AI_APPROVED) | set(curated)
    decided = explicit | set(AI_DENIED) | set(AI_PENDING) | set(COSMETIC_DENIED)

    def is_mcp_server(extension_id: str) -> bool:
        # Dan acceso a herramientas y datos internos a un agente, aunque el marketplace
        # no los categorice como IA.
        haystack = f"{extension_id} {names.get(extension_id, '')}".lower()
        return MCP_PATTERN.search(haystack) is not None

    def is_ai_related(extension_id: str) -> bool:
        """Amplio: incluye la etiqueta del marketplace. Solo para informar."""
        return ai_class.get(extension_id) != "Sin IA" or is_mcp_server(extension_id)

    def blocks_auto_inclusion(extension_id: str) -> bool:
        """Estricto: solo asistentes reales y servidores MCP.

        La etiqueta "Machine Learning" del marketplace no basta para bloquear: la llevan
        herramientas que no procesan codigo con IA (gestores de entornos Python,
        depuradores). Bloquearlas por la etiqueta era un falso positivo.
        """
        return ai_class.get(extension_id) == "Asistente de codigo IA" or is_mcp_server(
            extension_id
        )

    # Comprobacion de coherencia: nada esencial puede ser una extension con IA.
    ai_in_curated = sorted(eid for eid in curated if is_ai_related(eid))
    if ai_in_curated:
        raise SystemExit(
            "CURATED_BY_GROUP no puede contener extensiones con IA: " + ", ".join(ai_in_curated)
        )

    def provides_capability(extension_id: str) -> bool:
        """Aporta una capacidad de trabajo: lenguaje, depuracion, lint, tests, datos...

        No mira cuantos la usan. Un solo especialista de robotica necesita su extension
        de KUKA KRL igual que 59 personas necesitan Rainbow CSV.
        """
        if extension_id.split(".", 1)[0] in trusted or extension_id in decided:
            return False
        if extension_id in COSMETIC_DENIED or blocks_auto_inclusion(extension_id):
            return False
        if "deprecat" in names.get(extension_id, "").lower():
            return False
        if tier.require_repository and not repos_by_ext.get(extension_id):
            # Sin repositorio declarado no se puede auditar el codigo ni seguir sus CVE.
            return False
        categories = category_set(extension_id)
        # La capacidad manda sobre la etiqueta visual: la extension de KUKA KRL declara
        # "Themes" porque incluye un tema de color, pero es soporte de lenguaje. Vetar
        # por "Themes" dejaba fuera a los especialistas de robotica.
        if categories & tier.categories:
            return True
        return False

    def category_set(extension_id: str) -> set[str]:
        return {c.strip() for c in categories_by_ext.get(extension_id, "").split(",") if c.strip()}

    by_capability = (
        sorted(eid for eid in users_by_ext if provides_capability(eid))
        if tier.auto_include_by_category
        else []
    )

    # Sin repositorio declarado: no se puede auditar el codigo ni seguir sus CVE.
    # No se bloquean automaticamente porque varias son de fabricantes reales
    # (Rocket COBOL, Parasoft, Tenable, Fanuc) y bloquearlas pararia a un especialista.
    # Sin categorias declaradas: la regla por capacidad no puede clasificarlas, asi que
    # caen del lado de "bloqueada". Hay que mirarlas a mano.
    uncategorised = sorted(
        (
            (eid, names.get(eid, eid), len(users_by_ext[eid]))
            for eid in users_by_ext
            if not category_set(eid)
            and eid.split(".", 1)[0] not in trusted
            and eid not in decided
            and eid not in curated
        ),
        key=lambda item: -item[2],
    )

    no_provenance = sorted(
        (
            (eid, names.get(eid, eid), len(users_by_ext[eid]))
            for eid in by_capability
            if not repos_by_ext.get(eid)
        ),
        key=lambda item: -item[2],
    )

    # Asistentes y servidores MCP que entran permitidos por la regla de publisher del
    # fabricante. No los bloquea nada: conviene saber que estan dentro y por que.
    # Se dejan fuera las herramientas que solo llevan la etiqueta "Machine Learning"
    # del marketplace (Python, Jupyter...): no son superficie de agente.
    def agent_surface(eid: str) -> str | None:
        if ai_class[eid] == "Asistente de codigo IA":
            return "Asistente de codigo IA"
        if MCP_PATTERN.search(f"{eid} {names.get(eid, '')}".lower()):
            return "Servidor MCP"
        return None

    allowed_by_publisher = sorted(
        (
            (eid, agent_surface(eid), len(users_by_ext[eid]))
            for eid in users_by_ext
            if eid.split(".", 1)[0] in trusted
            and eid not in decided
            and agent_surface(eid) is not None
        ),
        key=lambda item: -item[2],
    )

    policy: dict[str, object] = {}
    policy["github"] = True
    for publisher in MICROSOFT_PUBLISHERS + MICROSOFT_PRODUCT_TEAMS:
        policy[publisher] = True
    for publisher in tier.vendors:
        policy[publisher] = True
    for extension_id in AI_APPROVED:
        policy[extension_id] = True
    allowed_extensions = set(curated) | set(by_capability)
    for extension_id in sorted(allowed_extensions):
        policy[extension_id] = "stable"
    for extension_id in sorted(set(AI_DENIED) | set(AI_PENDING)):
        policy[extension_id] = False
    policy["*"] = False

    context = {
        "tier": tier,
        "curated": curated,
        "users_by_ext": users_by_ext,
        "installs_by_ext": installs_by_ext,
        "names": names,
        "trusted": trusted,
        "by_capability": by_capability,
        "no_provenance": no_provenance,
        "uncategorised": uncategorised,
        "allowed_by_publisher": allowed_by_publisher,
        "allowed_ids": explicit | set(by_capability),
    }
    return policy, context


def n(value: int) -> str:
    """Separador de miles en formato espanol: 5.469."""
    return f"{value:,}".replace(",", ".")


def d(value: float) -> str:
    """Decimal en formato espanol: 88,2."""
    return f"{value:.1f}".replace(".", ",")


def is_allowed(extension_id: str, policy: dict) -> bool:
    """Reproduce la resolucion de VS Code: la clave mas especifica gana."""
    if extension_id in policy:
        return policy[extension_id] is not False
    publisher = extension_id.split(".", 1)[0]
    if publisher in policy:
        return policy[publisher] is not False
    return policy.get("*", True) is not False


def build_jsonc(policy: dict, context: dict) -> str:
    """Misma politica con comentarios de seccion, para revisar y versionar."""
    tier: Tier = context["tier"]
    curated: dict[str, str] = context["curated"]
    lines = [
        f"// Politica de extensiones permitidas para VS Code - "
        f"{'perfil' if not tier.chain else 'nivel'} {tier.nombre.upper()}.",
        f"// {tier.resumen}",
        f"// Generada el {date.today():%d/%m/%Y} a partir del inventario real de la flota.",
        "// Deny-by-default: lo que no aparece aqui queda bloqueado por \"*\": false.",
        "// Valores: true = cualquier version | \"stable\" = solo versiones estables | false = denegado.",
        "{",
        '  "extensions.allowed": {',
        "",
        "    // --- Primera parte: GitHub -------------------------------------------------",
        '    "github": true,',
        "",
        "    // --- Primera parte: Microsoft (publishers ms-*) -----------------------------",
    ]
    lines += [f'    "{p}": true,' for p in MICROSOFT_PUBLISHERS]
    lines += [
        "",
        "    // --- Microsoft con otro ID de publisher (verificar antes de ampliar) --------",
    ]
    lines += [f'    "{p}": true,' for p in MICROSOFT_PRODUCT_TEAMS]
    if tier.vendors:
        lines += [
            "",
            "    // --- Fabricantes de los stacks corporativos ------------------------------",
        ]
        lines += [f'    "{p}": true,' for p in tier.vendors]

    for group in tier.groups:
        entries = {k: v for k, v in CURATED_BY_GROUP[group].items()}
        if not entries:
            continue
        header = f"    // --- {GROUP_LABELS[group]} "
        lines += ["", header + "-" * max(4, 80 - len(header))]
        lines += [
            f'    "{eid}": "stable",  // {entries[eid]}{usage(eid, context)}'
            for eid in sorted(entries)
        ]

    if tier.auto_include_by_category:
        lines += [
            "",
            "    // --- Capacidad de trabajo segun categoria del marketplace ------------------",
            f"    // Categorias que cuentan aqui: {', '.join(sorted(tier.categories))}.",
            "    // Entra sin mirar cuantos la usan: el unico especialista de KUKA KRL o de",
            "    // COBOL la necesita igual que los 59 usuarios de Rainbow CSV.",
        ]
        lines += [
            f'    "{eid}": "stable",{comment(eid, context)}'
            for eid in context["by_capability"]
            if eid not in curated
        ]
    else:
        lines += [
            "",
            "    // --- Nada mas: este nivel no permite nada por categoria ---------------------",
            "    // La lista de arriba es cerrada. Lo demas se pide por el canal de excepciones.",
        ]
    lines += [
        "",
        "    // --- IA denegada: solo se permite Copilot y lo que publique Microsoft --------",
        "    // Las que pertenecen a un publisher permitido (Anthropic, Google, AWS,",
        "    // Salesforce) SOLO quedan bloqueadas por estas entradas por ID.",
    ]
    lines += [
        f'    "{eid}": false, // {label}'
        f'{usage(eid, context)}'
        for eid, label in sorted(AI_DENIED.items())
    ]
    lines += [
        "",
        "    // --- Todo lo demas, bloqueado -------------------------------------------------",
        '    "*": false',
        "  }",
        "}",
        "",
    ]
    return "\n".join(lines)


def usage(extension_id: str, context: dict) -> str:
    if not context["tier"].derived_from_fleet:
        return ""  # un perfil no se justifica por cuanta gente lo usa hoy
    users = len(context["users_by_ext"].get(extension_id, set()))
    return f" ({users} usuarios)" if users else " (no presente en la flota)"


def comment(extension_id: str, context: dict) -> str:
    name = context["names"].get(extension_id, extension_id)
    if not context["tier"].derived_from_fleet:
        return f"  // {name}"
    users = len(context["users_by_ext"].get(extension_id, set()))
    return f"  // {name} ({users} usuarios)"


def narrative(tier: Tier) -> str:
    """Explica, para este nivel, que se permite y que no."""
    common = (
        "Lo bloqueado es aspecto (temas, iconos, cosmetica), snippets y packs, "
        "previsualizadores que duplican funciones ya integradas, extensiones deprecadas, "
        "y toda la IA que no sea Copilot ni Microsoft."
    )
    if not tier.auto_include_by_category:
        return (
            "Este nivel no permite nada por categoria: la lista es cerrada. Entran "
            "Microsoft, GitHub, los fabricantes de los stacks corporativos y las "
            "extensiones curadas de lenguaje, lint, formato y depuracion. Cualquier otra "
            "cosa, incluido un lenguaje de nicho legitimo, tendra que pedirse por el canal "
            f"de excepciones. {common}"
        )
    capacidades = ", ".join(sorted(tier.categories))
    extra = (
        " Ademas se exige repositorio declarado: lo que no se puede auditar, no entra."
        if tier.require_repository
        else ""
    )
    return (
        "Se permite por capacidad, no por implantacion: una extension entra aunque la use "
        f"una sola persona. Categorias que cuentan en este nivel: {capacidades}. "
        f"{common}{extra}"
    )


def build_impact(policy: dict, context: dict, installations: list[dict]) -> tuple[str, list[dict]]:
    tier: Tier = context["tier"]
    installs_by_ext = context["installs_by_ext"]
    users_by_ext = context["users_by_ext"]
    names = context["names"]

    blocked_ids = sorted(
        (eid for eid in installs_by_ext if not is_allowed(eid, policy)),
        key=lambda eid: (-len(users_by_ext[eid]), eid),
    )
    blocked_set = set(blocked_ids)
    blocked_installs = sum(installs_by_ext[eid] for eid in blocked_ids)
    total_installs = len(installations)

    affected: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in installations:
        if row["ExtensionId"] in blocked_set:
            affected[(row["Equipo"], row["Usuario"])].append(row["Nombre"])

    total_users = len({r["Usuario"].lower() for r in installations})
    affected_users = len({usuario.lower() for _, usuario in affected})
    heavy = sum(1 for items in affected.values() if len(items) >= 5)

    ai_pending_users = {
        eid: len(users_by_ext.get(eid, set())) for eid in AI_PENDING
    }
    ai_denied_users = sorted(
        (
            (eid, label, len(users_by_ext.get(eid, set())))
            for eid, label in AI_DENIED.items()
            if users_by_ext.get(eid)
        ),
        key=lambda item: -item[2],
    )

    lines = [
        f"# Impacto de la politica de extensiones permitidas - {tier.nombre.upper()}",
        "",
        f"> {tier.resumen}",
        "",
    ]
    if not tier.derived_from_fleet:
        lines += [
            "> **Aviso.** Este es un perfil para usuarios nuevos, no un nivel pensado para "
            "la flota actual. Las cifras de abajo simulan que pasaria si se aplicase a "
            "quienes ya trabajan hoy, y solo sirven para hacerse una idea de lo estrecho "
            "que es: no son una medida de su impacto real, porque su publico todavia no "
            "esta inventariado.",
            "",
        ]
    lines += [
        f"_Simulado el {date.today():%d/%m/%Y} sobre el inventario limpio "
        f"({n(total_installs)} instalaciones, {total_users} usuarios)._",
        "",
        "## Resultado",
        "",
        f"- **{n(total_installs - blocked_installs)} de {n(total_installs)} instalaciones "
        f"({d((total_installs - blocked_installs) / total_installs * 100)}%) siguen permitidas.**",
        f"- **{blocked_installs} instalaciones** de **{len(blocked_ids)} extensiones** quedarian bloqueadas.",
        f"- **{affected_users} de {total_users} usuarios ({affected_users / total_users * 100:.0f}%)** "
        "perderian al menos una extension.",
        f"- {heavy} usuarios perderian 5 o mas: contactar antes del despliegue "
        f"(ver `impacto_usuarios{tier.suffix}.csv`).",
        "",
        narrative(tier),
        "",
        f"El detalle por usuario esta en `impacto_usuarios{tier.suffix}.csv` para avisar o "
        "tramitar excepciones antes de aplicar.",
        "",
        "## Asistentes de IA",
        "",
        "**Politica: solo GitHub Copilot y lo que publique Microsoft.** Todo lo demas queda "
        "denegado, incluidos los asistentes de fabricantes cuyo publisher si esta permitido "
        "para el resto de sus extensiones.",
        "",
        "| Extension | Proveedor | Usuarios que lo pierden |",
        "|---|---|---:|",
    ]
    for eid, label, count in ai_denied_users:
        lines.append(f"| `{eid}` | {label} | {count} |")
    if not ai_denied_users:
        lines.append("| — | — | 0 |")

    uncat = context["uncategorised"]
    if uncat:
        lines += [
            "",
            "### Sin categorias declaradas: revisar a mano",
            "",
            "La regla permite por capacidad, y estas extensiones no declaran ninguna "
            "categoria en su manifiesto. Quedan bloqueadas por defecto, pero puede haber "
            "herramientas de trabajo entre ellas: añadirlas a `WORK_TOOLS_UNCATEGORISED` "
            "si lo son.",
            "",
            "| Extension | Nombre | Usuarios |",
            "|---|---|---:|",
        ]
        for eid, name, count in uncat[:15]:
            lines.append(f"| `{eid}` | {name} | {count} |")

    prov = context["no_provenance"]
    if prov:
        lines += [
            "",
            "### Permitidas pero sin repositorio declarado",
            "",
            "Aportan capacidad de trabajo, asi que entran, pero no declaran repositorio: "
            "no se puede auditar su codigo ni seguir sus CVE. No se bloquean "
            "automaticamente porque varias son de fabricantes reales (Rocket COBOL, "
            "Parasoft, Tenable, Fanuc) y bloquearlas pararia a un especialista. "
            "Conviene verificarlas una a una.",
            "",
            "| Extension | Nombre | Usuarios |",
            "|---|---|---:|",
        ]
        for eid, name, count in prov[:15]:
            lines.append(f"| `{eid}` | {name} | {count} |")

    riding = context["allowed_by_publisher"]
    if riding:
        lines += [
            "",
            "### Extensiones con IA permitidas por la regla de publisher",
            "",
            "Entran porque su fabricante esta permitido al completo. No las bloquea nada; "
            "figuran aqui para que su presencia sea una decision y no un efecto colateral. "
            "Para excluir alguna, basta una entrada propia en `false`: la clave del ID "
            "concreto gana sobre la del publisher.",
            "",
            "| Extension | Clasificacion | Usuarios |",
            "|---|---|---:|",
        ]
        for eid, clasificacion, count in riding[:20]:
            lines.append(f"| `{eid}` | {clasificacion} | {count} |")

    lines += [
        "",
        f"## Extensiones bloqueadas con mas usuarios (top 30 de {len(blocked_ids)})",
        "",
        "Revisar esta tabla es lo que decide si hace falta ampliar la lista blanca.",
        "",
        "| Extension | ID | Usuarios | Instalaciones |",
        "|---|---|---:|---:|",
    ]
    for eid in blocked_ids[:30]:
        lines.append(
            f"| {names.get(eid, '')} | `{eid}` | {len(users_by_ext[eid])} | {installs_by_ext[eid]} |"
        )

    lines += [
        "",
        "## Como ajustar",
        "",
        "- Si el marketplace la categoriza mal y es una herramienta de trabajo: añadirla a "
        "`WORK_TOOLS_UNCATEGORISED` en `build_policy.py`.",
        "- Si es cosmetica que se cuela por categoria: añadirla a `COSMETIC_DENIED`.",
        "- Para permitirla aunque hoy no la use nadie: `ESSENTIAL_EXTENSIONS`.",
        "- Para permitir un fabricante entero: añadirlo a `VENDOR_PUBLISHERS`.",
        "- Para excluir algo que entra por regla de publisher: añadirlo con valor `False`; "
        "la clave del ID concreto gana sobre la del publisher.",
        "- Regenerar con `python build_policy.py && python build_report.py && python verify.py` "
        "y volver a revisar este informe.",
        "",
    ]

    user_rows = [
        {
            "Equipo": equipo,
            "Usuario": usuario,
            "ExtensionesBloqueadas": len(items),
            "Detalle": " | ".join(sorted(items)),
        }
        for (equipo, usuario), items in affected.items()
    ]
    user_rows.sort(key=lambda r: -r["ExtensionesBloqueadas"])
    return "\n".join(lines), user_rows


def write_tier(installations: list[dict], tier: Tier) -> dict:
    """Genera los ficheros de un nivel y devuelve sus metricas."""
    policy, context = build_policy(installations, tier)
    suffix = tier.suffix

    strict = {"extensions.allowed": policy}
    (POLICY_DIR / f"extensions.allowed{suffix}.json").write_text(
        json.dumps(strict, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (POLICY_DIR / f"extensions.allowed{suffix}.jsonc").write_text(
        build_jsonc(policy, context), encoding="utf-8"
    )
    impact, user_rows = build_impact(policy, context, installations)
    (POLICY_DIR / f"IMPACTO{suffix}.md").write_text(impact, encoding="utf-8")
    with (POLICY_DIR / f"impacto_usuarios{suffix}.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Equipo", "Usuario", "ExtensionesBloqueadas", "Detalle"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(user_rows)

    allowed_installs = sum(1 for r in installations if is_allowed(r["ExtensionId"], policy))
    blocked_ids = {
        r["ExtensionId"] for r in installations if not is_allowed(r["ExtensionId"], policy)
    }
    return {
        "tier": tier,
        "entradas": len(policy),
        "cobertura": allowed_installs / len(installations) * 100,
        "instalaciones_permitidas": allowed_installs,
        "extensiones_bloqueadas": len(blocked_ids),
        "usuarios_afectados": len(user_rows),
        "usuarios_muy_afectados": sum(1 for r in user_rows if r["ExtensionesBloqueadas"] >= 5),
    }


def build_comparison(metrics: list[dict], installations: list[dict]) -> str:
    total_users = len({r["Usuario"].lower() for r in installations})
    lines = [
        "# Niveles de politica: cual elegir",
        "",
        f"_Simulado el {date.today():%d/%m/%Y} sobre {n(len(installations))} instalaciones "
        f"y {total_users} usuarios._",
        "",
        "Los tres niveles comparten la misma politica de IA (**solo GitHub Copilot y lo que "
        "publique Microsoft**) y el mismo criterio de fondo: se permite por capacidad de "
        "trabajo, nunca por numero de usuarios. Lo que cambia es cuanta capacidad se "
        "considera imprescindible.",
        "",
        "| Nivel | Entradas | Cobertura | Ext. bloqueadas | Usuarios afectados | Pierden 5+ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for m in (x for x in metrics if x["tier"].chain):
        tier: Tier = m["tier"]
        nombre = f"**{tier.nombre}**" if not tier.slug else tier.nombre
        lines.append(
            f"| {nombre} | {m['entradas']} | {d(m['cobertura'])}% | "
            f"{m['extensiones_bloqueadas']} | {m['usuarios_afectados']} | "
            f"{m['usuarios_muy_afectados']} |"
        )

    profiles = [x for x in metrics if not x["tier"].chain]
    if profiles:
        lines += [
            "",
            "## Perfiles",
            "",
            "Un perfil no es un escalon mas de esa lista: es una politica pensada para un "
            "tipo de usuario concreto. No se deriva del inventario y no tiene por que ser "
            "subconjunto de los niveles de arriba.",
            "",
            "| Perfil | Entradas | Para quien |",
            "|---|---:|---|",
        ]
        for m in profiles:
            lines.append(f"| **{m['tier'].nombre}** | {m['entradas']} | {m['tier'].resumen} |")

    lines += ["", "## Que incluye cada uno", ""]
    header = "| Capacidad | " + " | ".join(m["tier"].nombre for m in metrics) + " |"
    lines += [header, "|---|" + "---|" * len(metrics)]
    used_groups = list(FULL_GROUPS) + [
        g for m in metrics for g in m["tier"].groups if g not in FULL_GROUPS
    ]
    seen: set[str] = set()
    for group in [g for g in used_groups if not (g in seen or seen.add(g))]:
        cells = ["si" if group in m["tier"].groups else "—" for m in metrics]
        lines.append(f"| {GROUP_LABELS[group]} | " + " | ".join(cells) + " |")
    cells = [
        "si" if m["tier"].auto_include_by_category else "no (lista cerrada)" for m in metrics
    ]
    lines.append("| *Admite altas por categoria* | " + " | ".join(cells) + " |")
    cells = ["si" if m["tier"].require_repository else "no" for m in metrics]
    lines.append("| *Exige repositorio declarado* | " + " | ".join(cells) + " |")
    cells = [str(len(m["tier"].vendors)) for m in metrics]
    lines.append("| *Fabricantes permitidos* | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Ficheros de cada nivel",
        "",
        "| Nivel | Politica | Anotada | Impacto |",
        "|---|---|---|---|",
    ]
    for m in metrics:
        suffix = m["tier"].suffix
        lines.append(
            f"| {m['tier'].nombre} | `extensions.allowed{suffix}.json` | "
            f"`extensions.allowed{suffix}.jsonc` | `IMPACTO{suffix}.md` |"
        )

    lines += ["", "## En que se diferencian", ""]
    for m in metrics:
        lines += [f"### {m['tier'].nombre}", "", m["tier"].resumen, ""]

    lines += [
        "## Recomendacion",
        "",
        "**Vibecoding** es independiente: se asigna a quien no programa, no se \"sube\" ni "
        "se \"baja\" desde los otros niveles.",
        "",
        "Para el resto de la flota, empezar por **Completa**: ya bloquea la IA no autorizada, la cosmetica, los "
        "packs, los snippets y las deprecadas, que es donde esta el riesgo real, y deja "
        "trabajar a todo el mundo. **Reducida** y **Minima** existen para endurecer "
        "despues, cuando el canal de excepciones este rodado y se sepa que se pide de "
        "verdad. Saltar directamente a Minima significa 5 o mas extensiones perdidas para "
        "muchos usuarios el primer dia.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    installations = read_installations()
    POLICY_DIR.mkdir(exist_ok=True)

    metrics = [write_tier(installations, tier) for tier in TIERS]
    (POLICY_DIR / "COMPARATIVA.md").write_text(
        build_comparison(metrics, installations), encoding="utf-8"
    )

    print(f"{'Nivel':<12} {'entradas':>9} {'cobertura':>10} {'afectados':>10}")
    for m in metrics:
        print(
            f"{m['tier'].nombre:<12} {m['entradas']:>9} "
            f"{m['cobertura']:>9.1f}% {m['usuarios_afectados']:>10}"
        )
    print(f"\nSalida en: {POLICY_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
