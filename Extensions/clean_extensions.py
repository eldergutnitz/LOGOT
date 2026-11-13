"""Limpieza y normalizacion del inventario de extensiones VS Code.

Entrada : Ext_VCS_FINAL.csv  (CSV ';' con BOM, exportado de la flota corporativa)
Salida  : clean/*.csv  (datos limpios + agregados)  y  clean/data_quality.json

Problemas conocidos en el fichero de origen y como se tratan:
  1. Registros truncados por escritura concurrente -> se reparan con la ruta instalada.
  2. Lineas "No se encontraron extensiones" -> no son extensiones, se separan.
  3. IDs con distinto casing (GitHub.copilot vs github.copilot) -> se normaliza a minusculas.
  4. Filas duplicadas (mismo equipo+usuario+extension) -> se colapsan a una instalacion.
  5. Nombres sin traducir del manifest (%displayName%) -> se resuelven por ID.
  6. Categorias multivalor en un solo campo -> se normaliza y se extrae categoria principal.
  7. Texto UTF-8 releido como cp1252 ("GitLens a,-" Git") -> se repara.
  8. Manifiesto ilegible ("ERROR" y el ID con la version pegada) -> se separa el ID real.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "Ext_VCS_FINAL.csv"
OUTPUT_DIR = BASE_DIR / "clean"

DELIMITER = ";"
EXPECTED_FIELDS = 10
NO_EXTENSIONS_MARKER = "No se encontraron extensiones"
PLACEHOLDER_NAME_PATTERN = re.compile(r"^%.*%$")
USER_FROM_PATH_PATTERN = re.compile(r"[\\/]Users[\\/]([^\\/]+)", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)")

# Asistentes/agentes de codigo con IA -> ID: proveedor. Se reportan aparte por gobernanza.
AI_ASSISTANTS = {
    "github.copilot": "GitHub",
    "github.copilot-chat": "GitHub",
    "ms-azuretools.vscode-azure-github-copilot": "GitHub",
    "vscjava.migrate-java-to-azure": "GitHub",
    "vscjava.vscode-java-upgrade": "GitHub",
    "danlambiase.lmstudio-copilot-provider": "Local (LM Studio)",
    "anthropic.claude-code": "Anthropic",
    "andrepimenta.claude-code-chat": "Anthropic",
    "saoudrizwan.claude-dev": "Cline",
    "rooveterinaryinc.roo-cline": "Roo Code",
    "kilocode.kilo-code": "Kilo Code",
    "openai.chatgpt": "OpenAI",
    "silasnevstad.gpthelper": "OpenAI",
    "danielsanmedium.dscodegpt": "CodeGPT",
    "google.geminicodeassist": "Google",
    "google.gemini-cli-vscode-ide-companion": "Google",
    "amazonwebservices.amazon-q-vscode": "AWS",
    "codeium.codeium": "Windsurf/Codeium",
    "codeium.codeium-enterprise-updater": "Windsurf/Codeium",
    "tabnine.tabnine-vscode": "Tabnine",
    "supermaven.supermaven": "Supermaven",
    "continue.continue": "Continue",
    "sourcegraph.cody-ai": "Sourcegraph",
    "blackboxapp.blackbox": "Blackbox",
    "blackboxapp.blackboxagent": "Blackbox",
    "mistralai.mistral-vibe-code": "Mistral",
    "zoocodeorganization.zoo-code": "Zoo",
    "salesforce.salesforcedx-einstein-gpt": "Salesforce",
    "sourcery.sourcery": "Sourcery",
    "ollama.ollama": "Local (Ollama)",
    "visualstudioexptteam.vscodeintellicode": "Microsoft (IntelliCode)",
}

# Categorias del marketplace que marcan una extension como herramienta IA (no asistente).
AI_TOOLING_CATEGORIES = {"AI", "Chat", "Machine Learning"}


def read_records(path: Path) -> tuple[list[list[str]], list[list[str]]]:
    """Devuelve (registros con 10 campos, registros malformados)."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=DELIMITER)
        next(reader)  # cabecera
        well_formed: list[list[str]] = []
        malformed: list[list[str]] = []
        for row in reader:
            if not any(field.strip() for field in row):
                continue
            (well_formed if len(row) == EXPECTED_FIELDS else malformed).append(row)
    return well_formed, malformed


def repair_truncated(rows: list[list[str]]) -> list[dict[str, str]]:
    """Repara registros partidos a media linea.

    El truncamiento pierde la cabecera del registro, pero conserva la cola:
    ... descripcion ; Categorias ; Repositorio ; ID ; RutaInstalada
    El usuario se recupera de la ruta instalada; el equipo se resuelve despues.
    """
    repaired: list[dict[str, str]] = []
    for row in rows:
        if len(row) < 4:
            continue
        categories, repository, extension_id, install_path = row[-4:]
        if not extension_id or not install_path:
            continue
        match = USER_FROM_PATH_PATTERN.search(install_path)
        repaired.append(
            {
                "Equipo": "",
                "Usuario": match.group(1) if match else "",
                "Nombre": "",
                "Publisher": "",
                "Version": extract_version_from_path(install_path, extension_id),
                "Descripcion": "",
                "Categorias": categories,
                "Repositorio": repository,
                "ID": extension_id,
                "RutaInstalada": install_path,
                "_reparado": "si",
            }
        )
    return repaired


def extract_version_from_path(install_path: str, extension_id: str) -> str:
    """La carpeta de instalacion termina en <id>-<version>[-<plataforma>]."""
    folder = install_path.rstrip("\\/").split("\\")[-1].split("/")[-1]
    prefix = f"{extension_id.lower()}-"
    if folder.lower().startswith(prefix):
        remainder = folder[len(prefix):]
        match = re.match(r"^\d+\.\d+\.\d+(?:[-+.\w]*?)(?=-win32|-darwin|-linux|-alpine|$)", remainder)
        if match:
            return match.group(0)
    return ""


def _cp1252_high_chars() -> frozenset[str]:
    """Caracteres que produce cp1252 al leer un byte >= 0x80 (incluye el euro, comillas...)."""
    chars = set()
    for byte in range(0x80, 0x100):
        try:
            chars.add(bytes([byte]).decode("cp1252"))
        except UnicodeDecodeError:
            chars.add(chr(byte))  # los controles C1 que cp1252 no define
    return frozenset(chars)


CP1252_HIGH = _cp1252_high_chars()


def looks_like_mojibake(text: str) -> bool:
    """Dos caracteres altos seguidos: firma de UTF-8 releido byte a byte.

    El acentuado normal ("Espanol", "Francais") nunca encadena dos, asi que no se toca.
    """
    return any(a in CP1252_HIGH and b in CP1252_HIGH for a, b in zip(text, text[1:]))


def fix_mojibake(text: str) -> str:
    """Repara texto UTF-8 que se guardo interpretado como cp1252."""
    if not looks_like_mojibake(text):
        return text
    raw = bytearray()
    for char in text:
        codepoint = ord(char)
        if 0x80 <= codepoint <= 0x9F:
            # cp1252 no define los controles C1; ahi el byte original es el codepoint.
            raw.append(codepoint)
            continue
        try:
            raw.extend(char.encode("cp1252"))
        except UnicodeEncodeError:
            return text
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return text


# Cuando el inventario no pudo leer el package.json de una extension escribio "ERROR"
# en los campos de texto y uso el nombre de la carpeta como ID, que lleva la version
# pegada: "dart-code.dart-code-3.134.0" en vez de "dart-code.dart-code".
ERROR_SENTINEL = "ERROR"
ID_WITH_VERSION_PATTERN = re.compile(r"^(?P<id>.+?)-(?P<version>\d+\.\d+\.\d+[-+.\w]*)$")


def blank_if_error(value: str) -> str:
    return "" if value.strip() == ERROR_SENTINEL else value


def split_id_and_version(extension_id: str) -> tuple[str, str]:
    """Separa el ID real de la version pegada por el fallback del inventario.

    Sin esto, Dart aparece como "dart-code.dart-code-3.134.0" y su ID real nunca
    llega a la politica: los desarrolladores de Flutter se quedarian sin el.
    """
    match = ID_WITH_VERSION_PATTERN.match(extension_id)
    if not match:
        return extension_id, ""
    return match.group("id"), match.group("version")


def normalize_categories(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def version_sort_key(version: str) -> tuple:
    match = VERSION_PATTERN.match(version or "")
    numeric = tuple(int(part) for part in match.groups()) if match else (0, 0, 0)
    return numeric + (version or "",)


def humanize_id(extension_id: str) -> str:
    """Nombre legible a partir del ID cuando el manifest no esta traducido."""
    name = extension_id.split(".", 1)[-1]
    name = re.sub(r"^(vscode|vs)[-.]", "", name)
    name = re.sub(r"[-.]?(vscode|extension)$", "", name)
    return " ".join(word.capitalize() for word in re.split(r"[-_.]+", name) if word)


def build_catalog(installations: list[dict]) -> dict[str, dict]:
    """Metadatos canonicos por extension: el valor mas frecuente y no vacio gana."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in installations:
        grouped[row["ExtensionId"]].append(row)

    catalog: dict[str, dict] = {}
    for extension_id, rows in grouped.items():
        def most_common(field: str) -> str:
            values = [r[field] for r in rows if r[field]]
            return Counter(values).most_common(1)[0][0] if values else ""

        names = [
            r["Nombre"]
            for r in rows
            if r["Nombre"] and not PLACEHOLDER_NAME_PATTERN.match(r["Nombre"])
        ]
        display_name = Counter(names).most_common(1)[0][0] if names else humanize_id(extension_id)
        categories = most_common("Categorias")
        catalog[extension_id] = {
            "Nombre": display_name,
            "NombreOrigen": "manifiesto" if names else "derivado del ID",
            "Publisher": most_common("Publisher") or extension_id.split(".", 1)[0],
            "Categorias": categories,
            "CategoriaPrincipal": normalize_categories(categories)[0] if categories else "Sin categoria",
            "Repositorio": most_common("Repositorio"),
            "ClasificacionIA": classify_ai(extension_id, categories),
            "ProveedorIA": AI_ASSISTANTS.get(extension_id, ""),
        }
    return catalog


def classify_ai(extension_id: str, categories: str) -> str:
    if extension_id in AI_ASSISTANTS:
        return "Asistente de codigo IA"
    if AI_TOOLING_CATEGORIES & set(normalize_categories(categories)):
        return "Herramienta con IA"
    return "Sin IA"


def main() -> int:
    if not SOURCE_FILE.exists():
        print(f"No se encuentra {SOURCE_FILE}", file=sys.stderr)
        return 1

    well_formed, malformed = read_records(SOURCE_FILE)
    header = [
        "Equipo", "Usuario", "Nombre", "Publisher", "Version",
        "Descripcion", "Categorias", "Repositorio", "ID", "RutaInstalada",
    ]
    records = [dict(zip(header, row)) for row in well_formed]
    repaired_records = repair_truncated(malformed)

    # Equipo de cada usuario, para reasignar los registros reparados.
    machine_by_user: dict[str, str] = {}
    for record in records:
        if record["Usuario"] and record["Equipo"]:
            machine_by_user.setdefault(record["Usuario"].lower(), record["Equipo"])
    for record in repaired_records:
        record["Equipo"] = machine_by_user.get(record["Usuario"].lower(), "DESCONOCIDO")

    records.extend(repaired_records)

    # Separar inventarios vacios (equipos sin ninguna extension instalada).
    empty_inventories = [r for r in records if r["Nombre"] == NO_EXTENSIONS_MARKER or not r["ID"]]
    raw_installations = [r for r in records if r not in empty_inventories]

    # Normalizacion + deduplicacion por (equipo, usuario, extension).
    deduplicated: dict[tuple[str, str, str], dict] = {}
    duplicate_count = 0
    casing_mismatch = 0
    placeholder_names = 0
    mojibake_fixed = 0
    unreadable_manifest = 0
    for record in raw_installations:
        extension_id = record["ID"].strip().lower()
        if record["ID"].strip() != extension_id:
            casing_mismatch += 1
        if PLACEHOLDER_NAME_PATTERN.match(record["Nombre"].strip()):
            placeholder_names += 1
        if looks_like_mojibake(record["Nombre"]) or looks_like_mojibake(record["Categorias"]):
            mojibake_fixed += 1

        name = blank_if_error(record["Nombre"].strip())
        publisher = blank_if_error(record["Publisher"].strip())
        version = blank_if_error(record["Version"].strip())
        if not name and not version:
            # Manifiesto ilegible: el ID trae la version pegada del nombre de carpeta.
            extension_id, recovered = split_id_and_version(extension_id)
            if recovered:
                version = recovered
                unreadable_manifest += 1

        row = {
            "Equipo": record["Equipo"].strip().upper(),
            "Usuario": record["Usuario"].strip(),
            "ExtensionId": extension_id,
            "Nombre": fix_mojibake(name),
            "Publisher": publisher,
            "Version": version,
            "Categorias": fix_mojibake(record["Categorias"].strip()),
            "Repositorio": record["Repositorio"].strip(),
            "RutaInstalada": record["RutaInstalada"].strip(),
            "Reparado": record.get("_reparado", "no"),
        }
        key = (row["Equipo"], row["Usuario"].lower(), extension_id)
        existing = deduplicated.get(key)
        if existing is None:
            deduplicated[key] = row
            continue
        duplicate_count += 1
        # Conflicto: nos quedamos con la version mas alta instalada.
        if version_sort_key(row["Version"]) > version_sort_key(existing["Version"]):
            deduplicated[key] = row

    installations = list(deduplicated.values())
    catalog = build_catalog(installations)

    # Aplicar metadatos canonicos a cada instalacion.
    for row in installations:
        meta = catalog[row["ExtensionId"]]
        row["Nombre"] = meta["Nombre"]
        row["Publisher"] = meta["Publisher"]
        row["Categorias"] = meta["Categorias"]
        row["CategoriaPrincipal"] = meta["CategoriaPrincipal"]
        row["Repositorio"] = meta["Repositorio"]
        row["NombreOrigen"] = meta["NombreOrigen"]
        row["ClasificacionIA"] = meta["ClasificacionIA"]
        row["ProveedorIA"] = meta["ProveedorIA"]
        row["EsAsistenteIA"] = "si" if meta["ClasificacionIA"] == "Asistente de codigo IA" else "no"

    installations.sort(key=lambda r: (r["Equipo"], r["Usuario"].lower(), r["ExtensionId"]))

    # Equipos sin extensiones (deduplicados por equipo+usuario).
    empty_rows = sorted(
        {
            (r["Equipo"].strip().upper(), r["Usuario"].strip())
            for r in empty_inventories
            if r["Equipo"].strip()
        }
    )
    machines_with_extensions = {r["Equipo"] for r in installations}
    empty_rows = [pair for pair in empty_rows if pair[0] not in machines_with_extensions]

    OUTPUT_DIR.mkdir(exist_ok=True)
    write_installations(installations)
    write_extension_summary(installations, catalog)
    write_user_summary(installations)
    write_empty_machines(empty_rows)
    quality = write_quality_report(
        source_rows=len(well_formed) + len(malformed),
        malformed=len(malformed),
        repaired=len(repaired_records),
        empty_inventories=len(empty_rows),
        raw_installations=len(raw_installations),
        installations=len(installations),
        duplicates=duplicate_count,
        casing_mismatch=casing_mismatch,
        placeholder_names=placeholder_names,
        mojibake_fixed=mojibake_fixed,
        unreadable_manifest=unreadable_manifest,
        catalog=catalog,
        rows=installations,
    )

    print(f"Instalaciones limpias : {len(installations)}")
    print(f"Extensiones unicas    : {len(catalog)}")
    print(f"Duplicados eliminados : {duplicate_count}")
    print(f"Equipos sin extension : {len(empty_rows)}")
    print(f"Salida en             : {OUTPUT_DIR}")
    return 0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=DELIMITER)
        writer.writeheader()
        writer.writerows(rows)


def write_installations(rows: list[dict]) -> None:
    fields = [
        "Equipo", "Usuario", "ExtensionId", "Nombre", "Publisher", "Version",
        "CategoriaPrincipal", "Categorias", "Repositorio", "ClasificacionIA",
        "ProveedorIA", "EsAsistenteIA", "NombreOrigen", "RutaInstalada", "Reparado",
    ]
    write_csv(OUTPUT_DIR / "instalaciones.csv", fields, [{f: r[f] for f in fields} for r in rows])


def write_extension_summary(rows: list[dict], catalog: dict[str, dict]) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["ExtensionId"]].append(row)

    summary = []
    for extension_id, group in grouped.items():
        versions = sorted({r["Version"] for r in group if r["Version"]}, key=version_sort_key)
        meta = catalog[extension_id]
        summary.append(
            {
                "ExtensionId": extension_id,
                "Nombre": meta["Nombre"],
                "Publisher": meta["Publisher"],
                "Instalaciones": len(group),
                "UsuariosUnicos": len({r["Usuario"].lower() for r in group}),
                "EquiposUnicos": len({r["Equipo"] for r in group}),
                "NumVersiones": len(versions),
                "VersionMasReciente": versions[-1] if versions else "",
                "VersionMasAntigua": versions[0] if versions else "",
                "CategoriaPrincipal": meta["CategoriaPrincipal"],
                "Categorias": meta["Categorias"],
                "Repositorio": meta["Repositorio"],
                "ClasificacionIA": meta["ClasificacionIA"],
                "ProveedorIA": meta["ProveedorIA"],
                "NombreOrigen": meta["NombreOrigen"],
            }
        )
    summary.sort(key=lambda r: (-r["Instalaciones"], r["ExtensionId"]))
    write_csv(OUTPUT_DIR / "extensiones.csv", list(summary[0].keys()), summary)


def write_user_summary(rows: list[dict]) -> None:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["Equipo"], row["Usuario"])].append(row)

    summary = [
        {
            "Equipo": equipo,
            "Usuario": usuario,
            "NumExtensiones": len(group),
            "UsaAsistenteIA": "si" if any(r["EsAsistenteIA"] == "si" for r in group) else "no",
            "AsistentesIA": ", ".join(
                sorted({r["Nombre"] for r in group if r["EsAsistenteIA"] == "si"})
            ),
            "CategoriaDominante": Counter(r["CategoriaPrincipal"] for r in group).most_common(1)[0][0],
        }
        for (equipo, usuario), group in grouped.items()
    ]
    summary.sort(key=lambda r: (-r["NumExtensiones"], r["Equipo"]))
    write_csv(OUTPUT_DIR / "usuarios.csv", list(summary[0].keys()), summary)


def write_empty_machines(pairs: list[tuple[str, str]]) -> None:
    rows = [{"Equipo": equipo, "Usuario": usuario} for equipo, usuario in pairs]
    write_csv(OUTPUT_DIR / "equipos_sin_extensiones.csv", ["Equipo", "Usuario"], rows)


def write_quality_report(**kwargs) -> dict:
    rows = kwargs.pop("rows")
    catalog = kwargs.pop("catalog")
    version_spread = Counter()
    per_extension_versions: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["Version"]:
            per_extension_versions[row["ExtensionId"]].add(row["Version"])
    for extension_id, versions in per_extension_versions.items():
        version_spread[extension_id] = len(versions)

    quality = {
        **kwargs,
        "extensiones_unicas": len(catalog),
        "equipos_con_extensiones": len({r["Equipo"] for r in rows}),
        "usuarios_con_extensiones": len({r["Usuario"].lower() for r in rows}),
        "sin_repositorio": sum(1 for r in rows if not r["Repositorio"]),
        "nombre_resuelto_por_id": sum(
            1 for meta in catalog.values() if meta["NombreOrigen"] == "derivado del ID"
        ),
        "top_dispersion_versiones": version_spread.most_common(15),
    }
    (OUTPUT_DIR / "data_quality.json").write_text(
        json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return quality


if __name__ == "__main__":
    raise SystemExit(main())
