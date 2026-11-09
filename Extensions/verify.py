"""Comprobaciones sobre los ficheros generados. Ejecutar tras regenerar la politica.

    python verify.py

Verifica que la politica resuelve como lo hace VS Code (la clave mas especifica gana),
que los invariantes se cumplen en todos los niveles y que el HTML esta bien formado.
"""

from __future__ import annotations

import csv
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

from build_policy import TIERS, is_allowed

BASE_DIR = Path(__file__).resolve().parent
POLICY_DIR = BASE_DIR / "policy"
POLICY_JSON = POLICY_DIR / "extensions.allowed.json"
REPORT_HTML = BASE_DIR / "clean" / "informe.html"

# Se cumple en TODA politica generada, sea nivel de la escalera o perfil.
INVARIANTS = [
    ("github.copilot", True, "Copilot: la unica IA de terceros permitida"),
    ("github.copilot-chat", True, "Copilot Chat"),
    ("ms-python.python", True, "Microsoft"),
    ("github.vscode-pull-request-github", True, "GitHub entra por su publisher"),
    # Git en todos: es parte del trabajo, no un extra
    ("eamodio.gitlens", True, "git en todas las politicas"),
    ("mhutchie.git-graph", True, "git en todas las politicas"),
    ("donjayamanne.githistory", True, "git en todas las politicas"),
    ("codezombiech.gitignore", True, "git en todas las politicas"),
    # Prerequisito de red: detras del proxy corporativo, sin esto falla TLS
    ("ukoloff.win-ca", True, "certificados CA en todas las politicas"),
    # Nada de IA fuera de Copilot y Microsoft
    ("anthropic.claude-code", False, "IA no permitida"),
    ("openai.chatgpt", False, "IA no permitida"),
    ("google.geminicodeassist", False, "IA de fabricante denegada por ID"),
    ("tabnine.tabnine-vscode", False, "IA no permitida"),
    ("altimateai.vscode-altimate-mcp-server", False, "servidor MCP de terceros"),
    # Aspecto, snippets, packs y deprecadas, fuera en todas
    ("pkief.material-icon-theme", False, "tema de iconos"),
    ("tonybaloney.vscode-pets", False, "novedad"),
    ("xabikos.javascriptsnippets", False, "snippets"),
    ("donjayamanne.python-extension-pack", False, "pack de extensiones"),
    ("donjayamanne.python-environment-manager", False, "deprecada"),
    ("un-publisher-cualquiera.lo-que-sea", False, "deny-by-default"),
]

# Se cumple en los niveles de la escalera, pero no en los perfiles.
CHAIN_INVARIANTS = [
    ("redhat.java", True, "fabricante del stack Java"),
    ("dbaeumer.vscode-eslint", True, "cadena estandar de lint"),
    ("rust-lang.rust-analyzer", True, "soporte de lenguaje"),
    ("dart-code.dart-code", True, "Dart: Flutter depende de el"),
    ("bitlang.cobol", True, "COBOL de mainframe"),
]

# Comprobaciones propias de cada perfil, por slug.
PROFILE_CASES = {
    "vibecoding": [
        ("github.copilot", True, "el asistente sobre el que se apoya todo el perfil"),
        ("github.copilot-chat", True, "Copilot Chat"),
        ("ms-python.python", True, "Python oficial de Microsoft"),
        ("ms-toolsai.jupyter", True, "Jupyter oficial de Microsoft"),
        ("github.vscode-pull-request-github", True, "GitHub oficial"),
        ("eamodio.gitlens", True, "git tambien aqui"),
        ("esbenp.prettier-vscode", True, "formateo automatico"),
        ("usernamehw.errorlens", True, "ver el error en la linea"),
        ("ritwickdey.liveserver", True, "previsualizar la web"),
        ("mechatroner.rainbow-csv", True, "leer CSV"),
        ("redhat.java", False, "fabricante de stack: fuera del perfil"),
        ("rust-lang.rust-analyzer", False, "lenguaje de desarrollo: fuera del perfil"),
        ("liskinlabs.kuka-krl-extension", False, "lenguaje de nicho: fuera del perfil"),
        ("anthropic.claude-code", False, "solo Copilot"),
        ("openai.chatgpt", False, "solo Copilot"),
        ("pkief.material-icon-theme", False, "aspecto"),
    ]
}

VOID_TAGS = {"meta", "br", "hr", "img", "link", "input"}

# (id, permitido esperado, por que)
CASES = [
    # Microsoft y GitHub: permitidos al completo, incluida su IA
    ("ms-python.python", True, "publisher Microsoft"),
    ("ms-python.una-extension-futura", True, "el publisher permitido cubre lo nuevo"),
    ("github.copilot", True, "Copilot: la unica IA de terceros permitida"),
    ("github.copilot-chat", True, "Copilot Chat por publisher github"),
    ("visualstudioexptteam.vscodeintellicode", True, "IA de Microsoft (IntelliCode)"),
    ("ms-azuretools.vscode-azure-mcp-server", True, "servidor MCP de Microsoft"),
    # Fabricantes de los stacks corporativos
    ("redhat.java", True, "fabricante del stack Java"),
    ("vmware.vscode-spring-boot", True, "Spring Boot Tools"),
    ("salesforce.salesforcedx-vscode-apex", True, "el resto de salesforce sigue permitido"),
    ("amazonwebservices.aws-toolkit-vscode", True, "el resto de AWS sigue permitido"),
    # Capacidad de trabajo: entra sin mirar cuantos la usan
    ("dbaeumer.vscode-eslint", True, "lint"),
    ("esbenp.prettier-vscode", True, "formato"),
    ("rust-lang.rust-analyzer", True, "soporte de lenguaje Rust"),
    ("mechatroner.rainbow-csv", True, "acceso a datos"),
    ("liskinlabs.kuka-krl-extension", True,
     "lenguaje de robots KUKA con 1 usuario: declara Themes, pero manda la capacidad"),
    ("fanuc.karel-for-fanuc-robot", True, "lenguaje de robots FANUC con 2 usuarios"),
    ("dart-code.dart-code", True, "Dart: sin categorias, pero Flutter depende de el"),
    ("bitlang.cobol", True, "COBOL de mainframe"),
    ("ukoloff.win-ca", True, "certificados CA de Windows: sin esto falla TLS"),
    ("bscan.perlnavigator", True, "servidor de lenguaje Perl con 1 usuario"),
    ("mcu-debug.rtos-views", True, "depuracion embebida con 1 usuario"),
    # Herramientas de trabajo que el marketplace deja en "Other"
    ("eamodio.gitlens", True, "control de versiones"),
    ("mhutchie.git-graph", True, "control de versiones"),
    ("usernamehw.errorlens", True, "diagnosticos"),
    ("qwtel.sqlite-viewer", True, "acceso a datos"),
    ("hbenl.vscode-test-explorer", True, "pruebas"),
    # Toda la IA que no sea Copilot ni Microsoft
    ("anthropic.claude-code", False, "solo se permite Copilot y Microsoft"),
    ("openai.chatgpt", False, "solo se permite Copilot y Microsoft"),
    ("google.geminicodeassist", False, "IA de fabricante: el ID gana al publisher"),
    ("salesforce.salesforcedx-einstein-gpt", False, "IA de fabricante denegada por ID"),
    ("amazonwebservices.amazon-q-vscode", False, "IA de fabricante denegada por ID"),
    ("tabnine.tabnine-vscode", False, "asistente no permitido"),
    ("continue.continue", False, "agente no permitido"),
    ("ollama.ollama", False, "modelos locales"),
    ("altimateai.vscode-altimate-mcp-server", False, "servidor MCP de terceros"),
    ("leonkohli.snapsource", False, "exporta codigo a ChatGPT"),
    # Aspecto y conveniencia: fuera aunque tengan muchos usuarios
    ("pkief.material-icon-theme", False, "tema de iconos con 34 usuarios"),
    ("vscode-icons-team.vscode-icons", False, "iconos"),
    ("oderwat.indent-rainbow", False, "cosmetico"),
    ("aaron-bond.better-comments", False, "cosmetica que se colaba por la categoria Formatters"),
    ("tonybaloney.vscode-pets", False, "novedad"),
    ("xabikos.javascriptsnippets", False, "snippets"),
    ("donjayamanne.python-extension-pack", False, "pack de extensiones"),
    ("infinity1207.angular2-switcher", False, "atajos de teclado"),
    # Deprecadas
    ("donjayamanne.python-environment-manager", False,
     "deprecada; la sustituye ms-python.vscode-python-envs"),
    ("micro-focus-amc.mfcobol", False, "deprecada; la sustituye rocketsoftware.rocket-cobol"),
    # Reglas generales
    ("un-publisher-cualquiera.lo-que-sea", False, "deny-by-default"),
    ("mechatroner.otra-extension", False, "permiso por extension, no por publisher"),
]


class TagBalance(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[tuple[str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.errors.append((tag, self.stack[-3:]))
        else:
            self.stack.pop()


def check_policy_resolution() -> int:
    policy = json.loads(POLICY_JSON.read_text(encoding="utf-8"))["extensions.allowed"]
    failures = 0
    for extension_id, expected, why in CASES:
        actual = is_allowed(extension_id, policy)
        if actual != expected:
            failures += 1
            print(f"  FALLA {extension_id}: esperado {expected}, obtenido {actual} ({why})")
    print(f"  resolucion de la politica: {len(CASES) - failures}/{len(CASES)} casos correctos")
    return failures


def fleet_ids() -> list[str]:
    """IDs reales del inventario, para comparar niveles por efecto y no por sintaxis."""
    path = BASE_DIR / "clean" / "extensiones.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row["ExtensionId"] for row in csv.DictReader(handle, delimiter=";")]


def check_tiers() -> int:
    """Los invariantes valen en los tres niveles, y cada nivel es subconjunto del mayor."""
    failures = 0
    previous: set[str] | None = None
    for tier in TIERS:
        path = POLICY_DIR / f"extensions.allowed{tier.suffix}.json"
        if not path.exists():
            print(f"  FALLA falta {path.name}")
            failures += 1
            continue
        policy = json.loads(path.read_text(encoding="utf-8"))["extensions.allowed"]
        expectations = list(INVARIANTS)
        expectations += CHAIN_INVARIANTS if tier.chain else []
        for extension_id, expected, why in expectations:
            actual = is_allowed(extension_id, policy)
            if actual != expected:
                failures += 1
                print(f"  FALLA [{tier.nombre}] {extension_id}: esperado {expected} ({why})")
        for extension_id, expected, why in PROFILE_CASES.get(tier.slug, ()):
            actual = is_allowed(extension_id, policy)
            if actual != expected:
                failures += 1
                print(f"  FALLA [{tier.nombre}] {extension_id}: esperado {expected} ({why})")
        if not tier.chain:
            continue  # un perfil no pertenece a la escalera: no se compara por anidamiento
        # Anidamiento sobre extensiones reales, no sobre claves: un nivel puede expresar
        # el mismo permiso por publisher y otro por ID sin ser mas permisivo.
        allowed = {eid for eid in fleet_ids() if is_allowed(eid, policy)}
        if previous is not None and not allowed <= previous:
            extra = sorted(allowed - previous)[:5]
            print(f"  FALLA [{tier.nombre}] permite extensiones que el nivel mayor no: {extra}")
            failures += 1
        previous = allowed
    if not failures:
        niveles = ", ".join(t.nombre for t in TIERS)
        print(f"  niveles ({niveles}): invariantes y anidamiento correctos")
    return failures


def check_html() -> int:
    parser = TagBalance()
    parser.feed(REPORT_HTML.read_text(encoding="utf-8"))
    if parser.errors or parser.stack:
        print(f"  FALLA HTML mal formado: {parser.errors[:3]} sin cerrar={parser.stack}")
        return 1
    print("  informe.html bien formado")
    return 0


def main() -> int:
    missing = [p for p in (POLICY_JSON, REPORT_HTML) if not p.exists()]
    if missing:
        print("Faltan ficheros generados: " + ", ".join(str(p) for p in missing))
        print("Ejecuta: python clean_extensions.py && python build_policy.py && python build_report.py")
        return 1

    failures = check_policy_resolution() + check_tiers() + check_html()
    print("OK" if not failures else f"{failures} comprobaciones fallidas")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
