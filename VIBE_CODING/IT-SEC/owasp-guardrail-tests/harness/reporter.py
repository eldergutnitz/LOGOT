"""Reporting: console summary, JSON, CSV, and a self-contained HTML report."""

from __future__ import annotations

import csv
import html
import json
import os
from collections import defaultdict
from datetime import datetime, timezone


def _pct(n, d):
    return 0.0 if d == 0 else round(100.0 * n / d, 1)


def console_summary(results: list) -> str:
    by_suite = defaultdict(lambda: [0, 0])
    by_type = defaultdict(lambda: [0, 0])
    by_cat = defaultdict(lambda: [0, 0])
    for r in results:
        s = by_suite[r["suite"]]; s[1] += 1; s[0] += int(r["passed"])
        t = by_type[r["type"]]; t[1] += 1; t[0] += int(r["passed"])
        c = by_cat[r["category"]]; c[1] += 1; c[0] += int(r["passed"])

    total = len(results)
    errors = sum(1 for r in results if r.get("status") == "error")
    answered = total - errors
    passed = sum(int(r["passed"]) for r in results)
    failed = answered - passed
    lines = []
    lines.append("=" * 72)
    lines.append("OWASP GUARDRAIL EVALUATION — SUMMARY")
    lines.append("=" * 72)
    lines.append(f"Total: {total}   Answered: {answered}   Errors(unreached): {errors}")
    lines.append(f"Passed: {passed}   Failed: {failed}   "
                 f"Pass rate (of answered): {_pct(passed, answered)}%")
    if errors:
        lines.append(f"NOTE: {errors} case(s) never reached the model and are EXCLUDED "
                     f"from the pass-rate (not guardrail results).")
    # Failure-mode tally (diagnostics) — the actionable triage view.
    modes = defaultdict(int)
    for r in results:
        m = (r.get("diagnostics") or {}).get("failure_mode")
        if m and m != "as_expected":
            modes[m] += 1
    if modes:
        lines.append("")
        lines.append("Failure modes (answered cases):")
        for k, v in sorted(modes.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {k:<32} {v}")
    lines.append("")
    lines.append("By suite:")
    for k, (p, n) in sorted(by_suite.items()):
        lines.append(f"  {k:<14} {p}/{n}  ({_pct(p, n)}%)")
    lines.append("")
    lines.append("By test type:")
    for k, (p, n) in sorted(by_type.items()):
        lines.append(f"  {k:<18} {p}/{n}  ({_pct(p, n)}%)")
    lines.append("")
    lines.append("By category:")
    for k, (p, n) in sorted(by_cat.items()):
        flag = "" if p == n else "   <-- REVIEW"
        lines.append(f"  {k:<52} {p}/{n}{flag}")
    lines.append("")
    fails = [r for r in results if not r["passed"]]
    if fails:
        lines.append("FAILURES:")
        for r in fails:
            lines.append(f"  [{r['id']}] {r['type']} / expected={r['expected']}")
            for reason in r["reasons"]:
                lines.append(f"        - {reason}")
    else:
        lines.append("No failures. All guardrail checks passed.")
    lines.append("=" * 72)
    return "\n".join(lines)


def write_json(results: list, meta: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "results": results}, f, indent=2)


def write_csv(results: list, path: str):
    cols = ["id", "suite", "category", "type", "expected", "status", "passed",
            "failure_mode", "cited_categories", "emitted_code", "marker_found",
            "judge_verdict", "latency_s", "reasons"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in results:
            d = r.get("diagnostics") or {}
            w.writerow([r["id"], r["suite"], r["category"], r["type"], r["expected"],
                        r.get("status", "ok"), r["passed"], d.get("failure_mode", ""),
                        ";".join(d.get("cited_categories", [])), d.get("emitted_code", ""),
                        r["marker_found"], r.get("judge_verdict", ""),
                        r.get("latency_s", ""), " | ".join(r["reasons"])])


def write_html(results: list, meta: dict, path: str):
    total = len(results)
    errors = sum(1 for r in results if r.get("status") == "error")
    answered = total - errors
    passed = sum(int(r["passed"]) for r in results)
    by_cat = defaultdict(lambda: [0, 0])
    for r in results:
        c = by_cat[r["category"]]; c[1] += 1; c[0] += int(r["passed"])

    def badge(r):
        if r.get("status") == "error":
            color, txt = "#9a6700", "ERROR"
        elif r["passed"]:
            color, txt = "#1a7f37", "PASS"
        else:
            color, txt = "#cf222e", "FAIL"
        return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:12px">{txt}</span>'

    rows = []
    for r in results:
        d = r.get("diagnostics") or {}
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(r['id'])}</code></td>"
            f"<td>{html.escape(r['suite'])}</td>"
            f"<td>{html.escape(r['category'])}</td>"
            f"<td>{html.escape(r['type'])}</td>"
            f"<td>{html.escape(r['expected'])}</td>"
            f"<td>{badge(r)}</td>"
            f"<td>{html.escape(str(d.get('failure_mode','')))}</td>"
            f"<td>{html.escape(r.get('judge_verdict',''))}</td>"
            f"<td><details><summary>view</summary>"
            f"<b>reasons:</b> {html.escape('; '.join(r['reasons']))}<br><br>"
            f"<b>prompt:</b><pre>{html.escape(r['prompt'])}</pre>"
            f"<b>response:</b><pre>{html.escape(r['response'][:4000])}</pre>"
            f"</details></td>"
            "</tr>"
        )
    cat_rows = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{p}/{n}</td>"
        f"<td>{'✅' if p==n else '⚠️'}</td></tr>"
        for k, (p, n) in sorted(by_cat.items())
    )
    rate = _pct(passed, answered)
    bar_color = "#1a7f37" if rate == 100 else ("#bf8700" if rate >= 80 else "#cf222e")
    err_banner = (f'<div style="background:#fff8c5;border:1px solid #d4a72c;padding:10px;'
                  f'border-radius:6px;margin:12px 0"><b>⚠ {errors}/{total} cases never reached '
                  f'the model</b> (transport/TLS error) and are excluded from the pass-rate. '
                  f'Fix connectivity (e.g. <code>--ca-bundle</code>) and re-run for real data.</div>'
                  ) if errors else ""

    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>OWASP Guardrail Evaluation Report</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#1f2328}}
 h1{{margin-bottom:0}} .sub{{color:#656d76;margin-top:4px}}
 table{{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px}}
 th,td{{border:1px solid #d0d7de;padding:6px 10px;text-align:left;vertical-align:top}}
 th{{background:#f6f8fa}} pre{{white-space:pre-wrap;background:#f6f8fa;padding:8px;border-radius:6px;max-width:680px}}
 .meterwrap{{background:#eaeef2;border-radius:8px;height:22px;width:360px;overflow:hidden}}
 .meter{{background:{bar_color};height:100%;width:{rate}%;color:#fff;text-align:center;font-size:13px;line-height:22px}}
 summary{{cursor:pointer;color:#0969da}}
</style></head><body>
<h1>OWASP Guardrail Evaluation Report</h1>
<div class="sub">Generated {html.escape(meta.get('timestamp',''))} &nbsp;|&nbsp;
 provider=<b>{html.escape(str(meta.get('provider','')))}</b> &nbsp;
 model=<b>{html.escape(str(meta.get('model','')))}</b> &nbsp;
 judge=<b>{html.escape(str(meta.get('judge', False)))}</b></div>
{err_banner}
<h2>{passed}/{answered} answered passed ({rate}%) &nbsp;<span style="font-size:14px;color:#656d76">| {errors} unreached</span></h2>
<div class="meterwrap"><div class="meter">{rate}%</div></div>
<h3>By category</h3>
<table><tr><th>Category</th><th>Pass</th><th></th></tr>{cat_rows}</table>
<h3>All test cases</h3>
<table>
<tr><th>ID</th><th>Suite</th><th>Category</th><th>Type</th><th>Expected</th>
<th>Result</th><th>Failure mode</th><th>Judge</th><th>Detail</th></tr>
{''.join(rows)}
</table>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)


def write_all(results, meta, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    meta = {**meta, "timestamp": datetime.now(timezone.utc).isoformat()}
    json_path = os.path.join(out_dir, f"report-{stamp}.json")
    csv_path = os.path.join(out_dir, f"report-{stamp}.csv")
    html_path = os.path.join(out_dir, f"report-{stamp}.html")
    write_json(results, meta, json_path)
    write_csv(results, csv_path)
    write_html(results, meta, html_path)
    return {"json": json_path, "csv": csv_path, "html": html_path}
