"""Genera el informe del inventario de extensiones a partir de los datos limpios.

Entrada : clean/*.csv + clean/data_quality.json  (salida de clean_extensions.py)
Salida  : clean/informe.html  (autocontenido)  y  INFORME.md  (resumen ejecutivo)
"""

from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "clean"
HTML_OUT = CLEAN_DIR / "informe.html"
MARKDOWN_OUT = BASE_DIR / "INFORME.md"

TOP_N = 25
# Politica corporativa de IA: solo GitHub Copilot y lo que publique Microsoft.
# Cualquier otro proveedor se reporta como no permitido.
MANAGED_AI_PROVIDERS = {"GitHub", "Microsoft (IntelliCode)"}

POLICY_FILE = BASE_DIR / "policy" / "extensions.allowed.json"

# Servidores MCP: exponen herramientas y datos internos a un agente de IA.
MCP_PATTERN = re.compile(r"\bmcp\b|-mcp|mcp-")

# Extensiones que guardan credenciales o abren sesion contra sistemas remotos.
# No implica que sean inseguras: marca donde viven secretos y accesos.
CREDENTIAL_PATTERN = re.compile(
    r"sqltools|dbclient|database-client|mysql|postgres|sqlite|mssql|oracle|mongo|snowflake"
    r"|remote-ssh|remote-wsl|remote-container|remote-explorer|sftp|\bftp\b|\bssh\b"
    r"|code-runner|kubernetes|docker|azure-account|\baws\b|zowe",
    re.I,
)


def read_csv(name: str) -> list[dict]:
    with (CLEAN_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def compute_metrics() -> dict:
    installations = read_csv("instalaciones.csv")
    extensions = read_csv("extensiones.csv")
    empty_machines = read_csv("equipos_sin_extensiones.csv")
    quality = json.loads((CLEAN_DIR / "data_quality.json").read_text(encoding="utf-8"))

    machines_with = {r["Equipo"] for r in installations}
    machines_without = {r["Equipo"] for r in empty_machines} - machines_with
    users_with = {r["Usuario"].lower() for r in installations}

    per_user = Counter((r["Equipo"], r["Usuario"].lower()) for r in installations)
    ai_users = {r["Usuario"].lower() for r in installations if r["EsAsistenteIA"] == "si"}

    provider_installs = Counter()
    provider_users = defaultdict(set)
    for row in installations:
        if row["EsAsistenteIA"] == "si":
            provider_installs[row["ProveedorIA"]] += 1
            provider_users[row["ProveedorIA"]].add(row["Usuario"].lower())

    category_installs = Counter(r["CategoriaPrincipal"] for r in installations)
    publisher_installs = Counter(r["Publisher"].lower() for r in installations)
    publisher_users = defaultdict(set)
    for row in installations:
        publisher_users[row["Publisher"].lower()].add(row["Usuario"].lower())

    fragmented = sorted(
        (e for e in extensions if int(e["NumVersiones"]) > 1),
        key=lambda e: (-int(e["NumVersiones"]), -int(e["Instalaciones"])),
    )

    return {
        "quality": quality,
        "installations": installations,
        "extensions": extensions,
        "total_installs": len(installations),
        "total_extensions": len(extensions),
        "machines_with": len(machines_with),
        "machines_without": len(machines_without),
        "machines_total": len(machines_with | machines_without),
        "users_with": len(users_with),
        "avg_per_user": len(installations) / len(per_user) if per_user else 0,
        "median_per_user": median([c for c in per_user.values()]),
        "max_per_user": max(per_user.values()) if per_user else 0,
        "solo_installs": sum(1 for e in extensions if int(e["Instalaciones"]) == 1),
        "ai_users": len(ai_users),
        "ai_share": len(ai_users) / len(users_with) * 100 if users_with else 0,
        "ai_installs": sum(1 for r in installations if r["EsAsistenteIA"] == "si"),
        "ai_tool_installs": sum(
            1 for r in installations if r["ClasificacionIA"] == "Herramienta con IA"
        ),
        "provider_rows": [
            {
                "proveedor": provider,
                "instalaciones": count,
                "usuarios": len(provider_users[provider]),
                "gestionado": provider in MANAGED_AI_PROVIDERS,
            }
            for provider, count in provider_installs.most_common()
        ],
        "category_rows": category_installs.most_common(12),
        "publisher_rows": [
            {"publisher": p, "instalaciones": c, "usuarios": len(publisher_users[p])}
            for p, c in publisher_installs.most_common(12)
        ],
        "top_extensions": extensions[:TOP_N],
        "fragmented": fragmented[:15],
        "derived_names": sum(1 for e in extensions if e["NombreOrigen"] == "derivado del ID"),
        "no_repo": sum(1 for e in extensions if not e["Repositorio"]),
        "security": compute_security(installations, extensions),
    }


def version_key(version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version or "")
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def load_policy() -> dict | None:
    """La politica es opcional: si aun no se ha generado, se omite esa columna."""
    if not POLICY_FILE.exists():
        return None
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))["extensions.allowed"]


def policy_blocks(extension_id: str, policy: dict | None) -> bool:
    if policy is None:
        return False
    if extension_id in policy:
        return policy[extension_id] is False
    publisher = extension_id.split(".", 1)[0]
    if publisher in policy:
        return policy[publisher] is False
    return policy.get("*", True) is False


def compute_security(installations: list[dict], extensions: list[dict]) -> dict:
    """Triage de exposicion a partir del inventario. No es un analisis de vulnerabilidades."""
    policy = load_policy()
    by_id = {e["ExtensionId"]: e for e in extensions}
    installs_by_ext = Counter(r["ExtensionId"] for r in installations)
    users_by_ext: dict[str, set[str]] = defaultdict(set)
    for row in installations:
        users_by_ext[row["ExtensionId"]].add(row["Usuario"].lower())

    def group(ids: set[str]) -> dict:
        ids = {eid for eid in ids if eid in installs_by_ext}
        return {
            "ids": sorted(ids, key=lambda eid: -len(users_by_ext[eid])),
            "extensiones": len(ids),
            "instalaciones": sum(installs_by_ext[eid] for eid in ids),
            "usuarios": len(set().union(*(users_by_ext[eid] for eid in ids)) if ids else set()),
            "bloqueadas": sum(1 for eid in ids if policy_blocks(eid, policy)),
        }

    unmanaged_ai = {
        e["ExtensionId"]
        for e in extensions
        if e["ClasificacionIA"] == "Asistente de codigo IA"
        and e["ProveedorIA"] not in MANAGED_AI_PROVIDERS
    }
    mcp = {
        e["ExtensionId"]
        for e in extensions
        if MCP_PATTERN.search(f"{e['ExtensionId']} {e['Nombre']}".lower())
    }
    no_repo = {e["ExtensionId"] for e in extensions if not e["Repositorio"]}
    unvetted = {
        e["ExtensionId"]
        for e in extensions
        if not e["Repositorio"] and int(e["UsuariosUnicos"]) <= 2
    }
    deprecated = {e["ExtensionId"] for e in extensions if "deprecat" in e["Nombre"].lower()}
    credentials = {
        e["ExtensionId"] for e in extensions if CREDENTIAL_PATTERN.search(e["ExtensionId"])
    }

    # Obsolescencia relativa: instalaciones por detras de la version mas nueva de la flota.
    # No se compara con el marketplace, solo consigo misma.
    stale_installs = 0
    stale_users: set[str] = set()
    stale_by_ext: Counter = Counter()
    for row in installations:
        newest = by_id.get(row["ExtensionId"], {}).get("VersionMasReciente", "")
        if newest and version_key(row["Version"]) < version_key(newest):
            stale_installs += 1
            stale_users.add(row["Usuario"].lower())
            stale_by_ext[row["ExtensionId"]] += 1

    return {
        "policy_loaded": policy is not None,
        "ia_no_gestionada": group(unmanaged_ai),
        "mcp": group(mcp),
        "sin_procedencia": group(no_repo),
        "sin_vetar": group(unvetted),
        "deprecadas": group(deprecated),
        "credenciales": group(credentials),
        "obsoletas_instalaciones": stale_installs,
        "obsoletas_usuarios": len(stale_users),
        "obsoletas_top": [
            (eid, count, by_id[eid]["Nombre"], by_id[eid]["NumVersiones"])
            for eid, count in stale_by_ext.most_common(10)
        ],
        "nombres": {e["ExtensionId"]: e["Nombre"] for e in extensions},
        "usuarios_por_ext": {eid: len(users) for eid, users in users_by_ext.items()},
        "installs_por_ext": installs_by_ext,
    }


def median(values: list[int]) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def bar(value: int, maximum: int) -> str:
    width = round(value / maximum * 100) if maximum else 0
    return f'<span class="bar" style="--w:{width}%"></span>'


def esc(value: str) -> str:
    return html.escape(str(value))


def d(value: float) -> str:
    """Decimal en formato espanol: 7,0."""
    return f"{value:.1f}".replace(".", ",")


def n(value: int) -> str:
    """Separador de miles en formato espanol: 7.559."""
    return f"{value:,}".replace(",", ".")


RISK_ROWS = [
    (
        "ia_no_gestionada",
        "alto",
        "Código fuente hacia terceros sin contrato",
        "Asistentes de IA de proveedores sin acuerdo corporativo. Cada uno envía fragmentos "
        "de código a una infraestructura distinta, con términos de retención y entrenamiento "
        "que nadie ha revisado.",
    ),
    (
        "mcp",
        "alto",
        "Servidores MCP",
        "Dan a un agente de IA acceso a herramientas y datos internos (bases de datos, "
        "Confluence, dbt). El marketplace no los categoriza como IA, así que pasan "
        "desapercibidos en cualquier revisión basada en categorías.",
    ),
    (
        "sin_vetar",
        "alto",
        "Sin procedencia y sin implantación",
        "Extensiones sin repositorio declarado y con 2 usuarios o menos. Es donde aparecen "
        "el typosquatting y los paquetes abandonados: nadie las revisa y nadie las echaría "
        "de menos.",
    ),
    (
        "credenciales",
        "medio",
        "Credenciales y acceso a sistemas",
        "Clientes de base de datos, sesiones remotas (SSH, WSL, contenedores) y ejecutores "
        "de código. No son inseguras por sí mismas: marcan dónde viven secretos y accesos "
        "fuera del gestor corporativo.",
    ),
    (
        "sin_procedencia",
        "medio",
        "Procedencia no verificable",
        "Sin repositorio declarado en el manifiesto: no se puede auditar el código ni "
        "seguir sus CVE.",
    ),
    (
        "deprecadas",
        "medio",
        "Marcadas como deprecadas",
        "El propio autor las declara sin mantenimiento. No recibirán parches.",
    ),
]


def risk_metrics(m: dict, key: str) -> dict:
    return m["security"][key]


def policy_cell(metrics: dict, policy_loaded: bool) -> str:
    if not policy_loaded:
        return "—"
    total = metrics["extensiones"]
    return f"{metrics['bloqueadas']}/{total}" if total else "—"


def top_exposures(sec: dict, limit: int = 12) -> list[tuple[str, str]]:
    """Extensiones concretas de las categorias de riesgo alto, por usuarios afectados."""
    labels = {
        "ia_no_gestionada": "IA no gestionada",
        "mcp": "Servidor MCP",
        "deprecadas": "Deprecada",
    }
    seen: dict[str, str] = {}
    for key, label in labels.items():
        for eid in sec[key]["ids"]:
            seen.setdefault(eid, label)
    ordered = sorted(seen.items(), key=lambda item: -sec["usuarios_por_ext"].get(item[0], 0))
    return ordered[:limit]


def build_html(m: dict) -> str:
    q = m["quality"]
    top_max = int(m["top_extensions"][0]["Instalaciones"]) if m["top_extensions"] else 1
    cat_max = m["category_rows"][0][1] if m["category_rows"] else 1
    pub_max = m["publisher_rows"][0]["instalaciones"] if m["publisher_rows"] else 1
    prov_max = m["provider_rows"][0]["instalaciones"] if m["provider_rows"] else 1

    top_rows = "\n".join(
        f"<tr><td class='num'>{i}</td><td><strong>{esc(e['Nombre'])}</strong>"
        f"<span class='id'>{esc(e['ExtensionId'])}</span></td>"
        f"<td class='num'>{e['Instalaciones']}</td>"
        f"<td class='num'>{e['UsuariosUnicos']}</td>"
        f"<td class='num'>{e['NumVersiones']}</td>"
        f"<td class='chart'>{bar(int(e['Instalaciones']), top_max)}</td></tr>"
        for i, e in enumerate(m["top_extensions"], 1)
    )
    cat_rows = "\n".join(
        f"<tr><td>{esc(name)}</td><td class='num'>{count}</td>"
        f"<td class='num'>{d(count / m['total_installs'] * 100)}%</td>"
        f"<td class='chart'>{bar(count, cat_max)}</td></tr>"
        for name, count in m["category_rows"]
    )
    pub_rows = "\n".join(
        f"<tr><td>{esc(p['publisher'])}</td><td class='num'>{p['instalaciones']}</td>"
        f"<td class='num'>{p['usuarios']}</td>"
        f"<td class='chart'>{bar(p['instalaciones'], pub_max)}</td></tr>"
        for p in m["publisher_rows"]
    )
    prov_rows = "\n".join(
        f"<tr><td>{esc(p['proveedor'])}</td>"
        f"<td>{'<span class=tag-ok>permitido</span>' if p['gestionado'] else '<span class=tag-warn>no permitido</span>'}</td>"
        f"<td class='num'>{p['instalaciones']}</td><td class='num'>{p['usuarios']}</td>"
        f"<td class='chart'>{bar(p['instalaciones'], prov_max)}</td></tr>"
        for p in m["provider_rows"]
    )
    frag_rows = "\n".join(
        f"<tr><td><strong>{esc(e['Nombre'])}</strong><span class='id'>{esc(e['ExtensionId'])}</span></td>"
        f"<td class='num'>{e['NumVersiones']}</td><td class='num'>{e['Instalaciones']}</td>"
        f"<td class='ver'>{esc(e['VersionMasAntigua'])} &rarr; {esc(e['VersionMasReciente'])}</td></tr>"
        for e in m["fragmented"]
    )

    sec = m["security"]
    risk_rows = "\n".join(
        f"<tr><td><span class='sev sev-{level}'>{level}</span></td>"
        f"<td><strong>{esc(title)}</strong><span class='why'>{esc(why)}</span></td>"
        f"<td class='num'>{risk_metrics(m, key)['extensiones']}</td>"
        f"<td class='num'>{risk_metrics(m, key)['instalaciones']}</td>"
        f"<td class='num'>{risk_metrics(m, key)['usuarios']}</td>"
        f"<td class='num'>{policy_cell(risk_metrics(m, key), sec['policy_loaded'])}</td></tr>"
        for key, level, title, why in RISK_ROWS
    )
    exposure_rows = "\n".join(
        f"<tr><td><strong>{esc(sec['nombres'].get(eid, eid))}</strong>"
        f"<span class='id'>{esc(eid)}</span></td>"
        f"<td class='num'>{sec['usuarios_por_ext'].get(eid, 0)}</td>"
        f"<td>{esc(label)}</td></tr>"
        for eid, label in top_exposures(sec)
    )
    stale_rows = "\n".join(
        f"<tr><td><strong>{esc(name)}</strong><span class='id'>{esc(eid)}</span></td>"
        f"<td class='num'>{count}</td><td class='num'>{versions}</td></tr>"
        for eid, count, name, versions in sec["obsoletas_top"]
    )

    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventario de extensiones VS Code</title>
<style>
  :root {{
    --bg: #fbfbfa; --panel: #fff; --ink: #1a1a18; --muted: #6b6a66;
    --line: #e6e4e0; --accent: #c05621; --accent-soft: #f0d9c9;
    --ok: #2f6f4f; --ok-soft: #dbeee4; --warn: #8a4b1d; --warn-soft: #f7e2d2;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #17161a; --panel: #201f24; --ink: #eceae6; --muted: #a3a09a;
      --line: #33313a; --accent: #e08d5b; --accent-soft: #4a3225;
      --ok: #7fc0a0; --ok-soft: #26402f; --warn: #e0a877; --warn-soft: #45301e;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #17161a; --panel: #201f24; --ink: #eceae6; --muted: #a3a09a;
    --line: #33313a; --accent: #e08d5b; --accent-soft: #4a3225;
    --ok: #7fc0a0; --ok-soft: #26402f; --warn: #e0a877; --warn-soft: #45301e;
  }}
  :root[data-theme="light"] {{
    --bg: #fbfbfa; --panel: #fff; --ink: #1a1a18; --muted: #6b6a66;
    --line: #e6e4e0; --accent: #c05621; --accent-soft: #f0d9c9;
    --ok: #2f6f4f; --ok-soft: #dbeee4; --warn: #8a4b1d; --warn-soft: #f7e2d2;
  }}
  body {{
    background: var(--bg); color: var(--ink); margin: 0;
    font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 48px 24px 96px; }}
  header {{ border-bottom: 2px solid var(--ink); padding-bottom: 20px; margin-bottom: 40px; }}
  h1 {{ font-size: clamp(28px, 5vw, 40px); line-height: 1.1; margin: 0 0 8px; letter-spacing: -.02em; }}
  .sub {{ color: var(--muted); font-size: 14px; }}
  h2 {{
    font-size: 13px; text-transform: uppercase; letter-spacing: .1em;
    color: var(--accent); margin: 48px 0 4px;
  }}
  h2 + .lede {{ color: var(--muted); font-size: 14px; margin: 0 0 20px; max-width: 62ch; }}
  .kpis {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
  .kpi {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px;
  }}
  .kpi b {{ display: block; font-size: 28px; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
  .kpi span {{ color: var(--muted); font-size: 12.5px; }}
  .scroll {{ overflow-x: auto; margin: 0 -4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; min-width: 480px; }}
  th {{
    text-align: left; font-size: 11.5px; text-transform: uppercase; letter-spacing: .07em;
    color: var(--muted); font-weight: 600; padding: 8px 10px; border-bottom: 1px solid var(--line);
  }}
  td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: baseline; }}
  tr:hover td {{ background: color-mix(in srgb, var(--accent-soft) 35%, transparent); }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .id, .ver {{ color: var(--muted); font: 12px ui-monospace, "Cascadia Code", Consolas, monospace; }}
  .id {{ display: block; }}
  .chart {{ width: 34%; min-width: 90px; }}
  .bar {{
    display: block; height: 7px; width: var(--w); min-width: 2px; border-radius: 4px;
    background: var(--accent);
  }}
  .tag-ok, .tag-warn, .sev {{
    font-size: 11.5px; padding: 2px 8px; border-radius: 20px; white-space: nowrap;
  }}
  .sev {{ text-transform: uppercase; letter-spacing: .05em; font-size: 10.5px; font-weight: 600; }}
  .sev-alto {{ background: var(--warn-soft); color: var(--warn); }}
  .sev-medio {{ background: var(--accent-soft); color: var(--accent); }}
  .why {{ display: block; color: var(--muted); font-size: 12.5px; margin-top: 3px; max-width: 52ch; }}
  .tag-ok {{ background: var(--ok-soft); color: var(--ok); }}
  .tag-warn {{ background: var(--warn-soft); color: var(--warn); }}
  .note {{
    background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--accent);
    border-radius: 8px; padding: 14px 18px; margin: 20px 0; font-size: 14px;
  }}
  .note ul {{ margin: 8px 0 0; padding-left: 20px; }}
  .note li {{ margin: 4px 0; }}
  code {{ font: 12.5px ui-monospace, Consolas, monospace; background: var(--accent-soft); padding: 1px 5px; border-radius: 4px; }}
  footer {{ margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }}
</style>

<div class="wrap">
<header>
  <h1>Inventario de extensiones VS Code</h1>
  <div class="sub">Flota corporativa &middot; datos depurados de <code>Ext_VCS_FINAL.csv</code> &middot; {date.today():%d/%m/%Y}</div>
</header>

<h2>Resumen</h2>
<p class="lede">De {n(m['machines_total'])} equipos inventariados, solo {n(m['machines_with'])} tienen extensiones de VS Code instaladas ({d(m['machines_with'] / m['machines_total'] * 100)}%). El resto se inventarió sin ninguna extensión.</p>
<div class="kpis">
  <div class="kpi"><b>{n(m['total_installs'])}</b><span>instalaciones limpias</span></div>
  <div class="kpi"><b>{n(m['total_extensions'])}</b><span>extensiones distintas</span></div>
  <div class="kpi"><b>{n(m['users_with'])}</b><span>usuarios con extensiones</span></div>
  <div class="kpi"><b>{d(m['avg_per_user'])}</b><span>extensiones por usuario (mediana {m['median_per_user']:.0f})</span></div>
  <div class="kpi"><b>{m['ai_share']:.0f}%</b><span>usuarios con asistente IA</span></div>
</div>

<h2>Limpieza aplicada</h2>
<p class="lede">El fichero de origen traía {n(q['source_rows'])} filas. Tras depurar quedan {n(m['total_installs'])} instalaciones reales.</p>
<div class="scroll"><table>
<tr><th>Problema detectado</th><th class="num">Filas</th><th>Tratamiento</th></tr>
<tr><td>Filas «No se encontraron extensiones»</td><td class="num">{n(q['empty_inventories'])}</td><td>Separadas a <code>equipos_sin_extensiones.csv</code> como pares equipo+usuario: son cobertura, no instalaciones</td></tr>
<tr><td>Duplicados (mismo equipo + usuario + extensión)</td><td class="num">{n(q['duplicates'])}</td><td>Colapsados a una instalación; se conserva la versión más alta</td></tr>
<tr><td>Registros truncados por escritura concurrente</td><td class="num">{q['malformed']}</td><td>Reparados con la ruta de instalación (usuario, versión e ID)</td></tr>
<tr><td>IDs con distinto uso de mayúsculas</td><td class="num">{n(q['casing_mismatch'])}</td><td>Normalizados a minúsculas para poder agrupar</td></tr>
<tr><td>Nombres sin traducir en el manifiesto (<code>%displayName%</code>)</td><td class="num">{n(q['placeholder_names'])}</td><td>Resueltos por ID; {m['derived_names']} extensiones quedan con nombre derivado</td></tr>
<tr><td>Manifiesto ilegible: ID con la version pegada</td><td class="num">{n(q['unreadable_manifest'])}</td><td>Separado el ID real (si no, Dart no llegaba a la política)</td></tr>
<tr><td>Texto con doble codificacion (UTF-8 leido como cp1252)</td><td class="num">{n(q['mojibake_fixed'])}</td><td>Reparado; afecta a nombres y categorias</td></tr>
<tr><td>Extensiones sin repositorio declarado</td><td class="num">{m['no_repo']}</td><td>Se mantienen; campo vacío marcado como tal</td></tr>
</table></div>

<h2>Extensiones más instaladas</h2>
<p class="lede">Top {TOP_N} por número de instalaciones. La columna «vers.» indica cuántas versiones distintas conviven en la flota.</p>
<div class="scroll"><table>
<tr><th class="num">#</th><th>Extensión</th><th class="num">Inst.</th><th class="num">Usuarios</th><th class="num">Vers.</th><th></th></tr>
{top_rows}
</table></div>

<h2>Adopción de IA</h2>
<p class="lede">{m['ai_users']} de {m['users_with']} usuarios ({m['ai_share']:.0f}%) tienen algún asistente de código con IA: {m['ai_installs']} instalaciones. Además hay {m['ai_tool_installs']} instalaciones de herramientas con funciones de IA (MCP, SDK, integraciones cloud) que no son asistentes.</p>
<div class="scroll"><table>
<tr><th>Proveedor</th><th>Estado</th><th class="num">Inst.</th><th class="num">Usuarios</th><th></th></tr>
{prov_rows}
</table></div>
<div class="note">
  <strong>La política corporativa permite un único asistente de terceros: GitHub Copilot.</strong>
  Se admite además la IA que publique Microsoft (IntelliCode, Azure MCP Server, Copilot for Azure).
  Todo lo demás queda denegado en <code>policy/</code>, incluidos los asistentes de fabricantes
  cuyo resto de extensiones sí están permitidas: cada uno envía código fuente a un tercero distinto.
</div>

<h2>Riesgo de seguridad</h2>
<p class="lede">Triage de exposición a partir del propio inventario. La columna «cubierto» indica cuántas de esas extensiones bloquea ya la política de <code>policy/</code>.</p>
<div class="scroll"><table>
<tr><th>Nivel</th><th>Vector</th><th class="num">Ext.</th><th class="num">Inst.</th><th class="num">Usuarios</th><th class="num">Cubierto</th></tr>
{risk_rows}
</table></div>

<div class="note">
  <strong>Software sin parchear es el vector con más alcance.</strong>
  {n(sec['obsoletas_instalaciones'])} instalaciones ({d(sec['obsoletas_instalaciones'] / m['total_installs'] * 100)}% del total),
  repartidas entre {sec['obsoletas_usuarios']} usuarios, ejecutan una versión anterior a la más
  nueva que ya existe en la flota. No es una comparación contra el marketplace: son equipos
  por detrás de sus propios compañeros, así que la actualización ya está validada internamente.
  Una lista blanca no arregla esto — hace falta activar la actualización automática de
  extensiones por política.
</div>

<div class="scroll"><table>
<tr><th>Extensión más desactualizada</th><th class="num">Inst. por detrás</th><th class="num">Versiones en flota</th></tr>
{stale_rows}
</table></div>

<h2>Exposición concreta</h2>
<p class="lede">Las extensiones detrás de los vectores de nivel alto, ordenadas por usuarios afectados. Es la lista corta sobre la que actuar.</p>
<div class="scroll"><table>
<tr><th>Extensión</th><th class="num">Usuarios</th><th>Motivo</th></tr>
{exposure_rows}
</table></div>

<div class="note">
  <strong>Alcance de este análisis.</strong> Se apoya solo en el inventario: identificadores,
  versiones, publishers, categorías y repositorios declarados.
  <ul>
    <li>No consulta CVE ni avisos de seguridad publicados.</li>
    <li>No comprueba el estado de publisher verificado ni la firma en el marketplace.</li>
    <li>No analiza el código de las extensiones ni su tráfico de red.</li>
    <li>«Desactualizada» es relativo a la propia flota, no a la última versión publicada.</li>
  </ul>
  Sirve para priorizar qué revisar, no para declarar nada seguro.
</div>

<h2>Fragmentación de versiones</h2>
<p class="lede">Extensiones con más dispersión de versiones. Indica equipos sin actualizar y superficie de parcheo desigual.</p>
<div class="scroll"><table>
<tr><th>Extensión</th><th class="num">Versiones</th><th class="num">Inst.</th><th>Rango</th></tr>
{frag_rows}
</table></div>

<h2>Categorías</h2>
<p class="lede">Categoría principal declarada por cada extensión, ponderada por instalaciones.</p>
<div class="scroll"><table>
<tr><th>Categoría</th><th class="num">Inst.</th><th class="num">%</th><th></th></tr>
{cat_rows}
</table></div>

<h2>Publishers</h2>
<div class="scroll"><table>
<tr><th>Publisher</th><th class="num">Inst.</th><th class="num">Usuarios</th><th></th></tr>
{pub_rows}
</table></div>

<h2>Ficheros generados</h2>
<div class="note">
  <ul>
    <li><code>clean/instalaciones.csv</code> — {n(m['total_installs'])} filas: una por equipo + usuario + extensión</li>
    <li><code>clean/extensiones.csv</code> — {n(m['total_extensions'])} filas: catálogo agregado con instalaciones, usuarios y versiones</li>
    <li><code>clean/usuarios.csv</code> — resumen por usuario con uso de IA</li>
    <li><code>clean/equipos_sin_extensiones.csv</code> — {n(m['machines_without'])} equipos inventariados sin extensiones</li>
    <li><code>clean/data_quality.json</code> — métricas de la depuración</li>
  </ul>
</div>

<footer>
  Generado con <code>clean_extensions.py</code> + <code>build_report.py</code> sobre {n(q['source_rows'])} filas de origen.
  Contiene identificadores de equipo y usuario: tratar como documento interno.
</footer>
</div>
"""


def build_markdown(m: dict) -> str:
    q = m["quality"]
    lines = [
        "# Inventario de extensiones VS Code — informe",
        "",
        f"_Generado el {date.today():%d/%m/%Y} a partir de `Ext_VCS_FINAL.csv` ({n(q['source_rows'])} filas)._",
        "",
        "## Resumen",
        "",
        f"- **{n(m['total_installs'])} instalaciones** limpias de **{n(m['total_extensions'])} extensiones** distintas.",
        f"- **{n(m['machines_with'])} de {n(m['machines_total'])} equipos** ({d(m['machines_with'] / m['machines_total'] * 100)}%) tienen extensiones; "
        f"{n(m['machines_without'])} se inventariaron sin ninguna.",
        f"- **{n(m['users_with'])} usuarios** con extensiones: media de {d(m['avg_per_user'])} por usuario "
        f"(mediana {m['median_per_user']:.0f}, máximo {m['max_per_user']}).",
        f"- **{m['ai_users']} usuarios ({m['ai_share']:.0f}%)** usan algún asistente de código con IA.",
        f"- **{m['solo_installs']} extensiones** están instaladas en un único equipo (cola larga).",
        "",
        "## Limpieza aplicada",
        "",
        "| Problema | Filas | Tratamiento |",
        "|---|---:|---|",
        f"| Filas «No se encontraron extensiones» | {n(q['empty_inventories'])} | Separadas a `equipos_sin_extensiones.csv` (pares equipo+usuario) |",
        f"| Duplicados equipo+usuario+extensión | {n(q['duplicates'])} | Colapsados; se conserva la versión más alta |",
        f"| Registros truncados (escritura concurrente) | {q['malformed']} | Reparados con la ruta de instalación |",
        f"| IDs con distinto casing | {n(q['casing_mismatch'])} | Normalizados a minúsculas |",
        f"| Nombres `%displayName%` sin traducir | {n(q['placeholder_names'])} | Resueltos por ID ({m['derived_names']} quedan derivados) |",
        f"| Manifiesto ilegible (ID con versión pegada) | {n(q['unreadable_manifest'])} | Separado el ID real |",
        f"| Texto con doble codificación | {n(q['mojibake_fixed'])} | Reparado (nombres y categorías) |",
        f"| Sin repositorio declarado | {m['no_repo']} | Se mantienen con el campo vacío |",
        "",
        "## Top 15 extensiones",
        "",
        "| # | Extensión | ID | Inst. | Usuarios | Versiones |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for i, e in enumerate(m["top_extensions"][:15], 1):
        lines.append(
            f"| {i} | {e['Nombre']} | `{e['ExtensionId']}` | {e['Instalaciones']} | "
            f"{e['UsuariosUnicos']} | {e['NumVersiones']} |"
        )

    lines += [
        "",
        "## Adopción de IA",
        "",
        f"{m['ai_users']} de {m['users_with']} usuarios ({m['ai_share']:.0f}%) tienen un asistente de código con IA "
        f"({m['ai_installs']} instalaciones). Hay además {m['ai_tool_installs']} instalaciones de herramientas con "
        "funciones de IA que no son asistentes (servidores MCP, SDK, integraciones cloud).",
        "",
        "| Proveedor | Estado | Instalaciones | Usuarios |",
        "|---|---|---:|---:|",
    ]
    for p in m["provider_rows"]:
        estado = "permitido" if p["gestionado"] else "**no permitido**"
        lines.append(f"| {p['proveedor']} | {estado} | {p['instalaciones']} | {p['usuarios']} |")

    lines += [
        "",
        "> **La política corporativa permite un único asistente de terceros: GitHub Copilot**, "
        "más la IA que publique Microsoft. Todo lo demás queda denegado en `policy/`, incluidos los "
        "asistentes de fabricantes cuyo resto de extensiones sí están permitidas: cada uno envía "
        "código fuente a un tercero distinto.",
        "",
        "## Riesgo de seguridad",
        "",
        "Triage de exposición a partir del propio inventario. «Cubierto» = cuántas de esas "
        "extensiones bloquea ya la política de `policy/`.",
        "",
        "| Nivel | Vector | Ext. | Inst. | Usuarios | Cubierto |",
        "|---|---|---:|---:|---:|---:|",
    ]
    sec = m["security"]
    for key, level, title, _ in RISK_ROWS:
        r = risk_metrics(m, key)
        lines.append(
            f"| {level.upper()} | {title} | {r['extensiones']} | {r['instalaciones']} | "
            f"{r['usuarios']} | {policy_cell(r, sec['policy_loaded'])} |"
        )

    lines += [
        "",
        f"**Software sin parchear es el vector con más alcance.** "
        f"{n(sec['obsoletas_instalaciones'])} instalaciones "
        f"({d(sec['obsoletas_instalaciones'] / m['total_installs'] * 100)}% del total), en "
        f"{sec['obsoletas_usuarios']} usuarios, ejecutan una versión anterior a la más nueva que "
        "ya existe en la flota — es decir, por detrás de sus propios compañeros, con la "
        "actualización ya validada internamente. Una lista blanca no arregla esto: hace falta "
        "activar la actualización automática de extensiones por política.",
        "",
        "| Extensión más desactualizada | Inst. por detrás | Versiones en flota |",
        "|---|---:|---:|",
    ]
    for eid, count, name, versions in sec["obsoletas_top"]:
        lines.append(f"| {name} (`{eid}`) | {count} | {versions} |")

    lines += [
        "",
        "### Exposición concreta",
        "",
        "Extensiones detrás de los vectores de nivel alto, por usuarios afectados.",
        "",
        "| Extensión | ID | Usuarios | Motivo |",
        "|---|---|---:|---|",
    ]
    for eid, label in top_exposures(sec):
        lines.append(
            f"| {sec['nombres'].get(eid, eid)} | `{eid}` | "
            f"{sec['usuarios_por_ext'].get(eid, 0)} | {label} |"
        )

    lines += [
        "",
        "> **Alcance.** Este análisis usa solo el inventario: identificadores, versiones, "
        "publishers, categorías y repositorios declarados. No consulta CVE ni avisos de "
        "seguridad, no comprueba publisher verificado ni firma en el marketplace, y no analiza "
        "el código ni el tráfico de las extensiones. «Desactualizada» es relativo a la propia "
        "flota, no a la última versión publicada. Sirve para priorizar qué revisar, no para "
        "declarar nada seguro.",
        "",
        "## Fragmentación de versiones",
        "",
        "| Extensión | Versiones | Inst. | Rango |",
        "|---|---:|---:|---|",
    ]
    for e in m["fragmented"][:10]:
        lines.append(
            f"| {e['Nombre']} | {e['NumVersiones']} | {e['Instalaciones']} | "
            f"{e['VersionMasAntigua']} → {e['VersionMasReciente']} |"
        )

    lines += [
        "",
        "## Ficheros",
        "",
        f"- `clean/instalaciones.csv` — {n(m['total_installs'])} filas (equipo + usuario + extensión)",
        f"- `clean/extensiones.csv` — {n(m['total_extensions'])} filas (catálogo agregado)",
        "- `clean/usuarios.csv` — resumen por usuario con uso de IA",
        f"- `clean/equipos_sin_extensiones.csv` — {n(m['machines_without'])} equipos sin extensiones",
        "- `clean/data_quality.json` — métricas de depuración",
        "- `clean/informe.html` — informe visual autocontenido",
        "- `policy/` — política de extensiones permitidas e informe de impacto",
        "",
        "Regenerar (el orden importa: el informe lee la política para el apartado de riesgo):",
        "",
        "```bash",
        "python clean_extensions.py",
        "python build_policy.py",
        "python build_report.py",
        "python verify.py",
        "```",
        "",
        "> Contiene identificadores de equipo y usuario: tratar como documento interno.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    metrics = compute_metrics()
    HTML_OUT.write_text(build_html(metrics), encoding="utf-8")
    MARKDOWN_OUT.write_text(build_markdown(metrics), encoding="utf-8")
    print(f"Informe HTML : {HTML_OUT}")
    print(f"Informe MD   : {MARKDOWN_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
