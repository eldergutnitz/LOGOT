#!/usr/bin/env python3
"""
OWASP Guardrail Evaluation Harness — runner.

Feeds adversarial + benign prompts to a model that is wrapped with one of the
guardrail system prompts, then scores whether the guardrail behaved correctly
(HALT / WARN+comply / comply-secure) using deterministic rules and, optionally,
an LLM judge.

Examples
--------
# Offline self-test of the harness (no API key needed; should be ~all green):
python run_tests.py --provider mock

# Prove the scorer catches a broken guardrail:
python run_tests.py --provider mock --mock-misbehave

# Real run against Anthropic:
export ANTHROPIC_API_KEY=sk-...
python run_tests.py --provider anthropic --model claude-sonnet-4-6 --judge

# Against any OpenAI-compatible endpoint (vLLM/Ollama/OpenAI/OpenRouter):
export OPENAI_API_KEY=...; export OPENAI_BASE_URL=http://localhost:11434/v1
python run_tests.py --provider openai --model llama3.1

# Filter:
python run_tests.py --provider mock --suite owasp_web --category A05
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from harness.loader import load_dataset, load_guardrail            # noqa: E402
from harness.providers import build_provider, ProviderError         # noqa: E402
from harness.scorer import RuleScorer, JudgeScorer, classify_response  # noqa: E402
from harness import reporter                                        # noqa: E402

DATASETS = {
    "owasp_web": os.path.join(HERE, "datasets", "owasp_web.yaml"),
    "owasp_llm": os.path.join(HERE, "datasets", "owasp_llm.yaml"),
    "obfuscation": os.path.join(HERE, "datasets", "obfuscation.yaml"),
}
GUARDRAIL_DIR_DEFAULT = os.path.abspath(os.path.join(HERE, ".."))


def parse_args():
    p = argparse.ArgumentParser(description="OWASP guardrail evaluation harness")
    p.add_argument("--provider", default="mock", help="mock | anthropic | openai")
    p.add_argument("--model", default=None, help="model id for the provider")
    p.add_argument("--base-url", default=None, help="base url for openai-compatible")
    p.add_argument("--judge", action="store_true", help="enable LLM-judge scoring")
    p.add_argument("--judge-provider", default=None, help="provider for the judge (default: same)")
    p.add_argument("--judge-model", default=None, help="model for the judge")
    p.add_argument("--suite", default="all", help="all | owasp_web | owasp_llm")
    p.add_argument("--category", default=None, help="substring filter, e.g. A05 or LLM07")
    p.add_argument("--type", default=None, help="filter by test type")
    p.add_argument("--limit", type=int, default=None, help="cap number of cases")
    p.add_argument("--guardrail-dir", default=GUARDRAIL_DIR_DEFAULT,
                   help="folder containing the GR_*.MD guardrail files")
    p.add_argument("--variant", default=None,
                   help="filename suffix to A/B a hardened guardrail, e.g. _v2 "
                        "loads GR_OWASP_TOP_10_2025_v2.MD")
    p.add_argument("--out-dir", default=os.path.join(HERE, "reports"))
    p.add_argument("--mock-misbehave", action="store_true",
                   help="mock provider complies with insecure asks (to test the scorer)")
    p.add_argument("--max-tokens", type=int, default=1500)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--ca-bundle", default=None,
                   help="path to corporate root CA PEM. If given, TLS is verified "
                        "against it (preferred, secure way to fix CERTIFICATE_VERIFY_FAILED)")
    p.add_argument("--insecure-skip-verify", action="store_true",
                   help="(default behaviour) disable TLS verification. TESTING ONLY")
    p.add_argument("--verify-tls", action="store_true",
                   help="force normal TLS certificate verification (opt back into secure mode)")
    p.add_argument("--timeout", type=int, default=120, help="per-request timeout seconds")
    p.add_argument("--retries", type=int, default=2, help="retries on 5xx/429/network errors")
    p.add_argument("--fail-under", type=float, default=None,
                   help="exit non-zero if pass-rate %% is below this")
    return p.parse_args()


def select_suites(name):
    if name == "all":
        return ["owasp_web", "owasp_llm", "obfuscation"]
    if name in DATASETS:
        return [name]
    raise SystemExit(f"Unknown suite '{name}'. Use all|{('|'.join(DATASETS))}.")


def main():
    args = parse_args()

    # TLS policy: insecure (verification OFF) is the DEFAULT, because the target
    # eval gateways typically sit behind a TLS-intercepting proxy with a private
    # CA. Verification is re-enabled automatically when a --ca-bundle is supplied,
    # or explicitly with --verify-tls.
    insecure = not (args.verify_tls or args.ca_bundle)

    try:
        provider = build_provider(
            args.provider, model=args.model, base_url=args.base_url,
            max_tokens=args.max_tokens, temperature=args.temperature,
            misbehave=args.mock_misbehave, ca_bundle=args.ca_bundle,
            insecure=insecure, timeout=args.timeout, retries=args.retries,
        )
        if insecure and args.provider != "mock":
            print("WARNING: TLS certificate verification is DISABLED (default). This is "
                  "itself an OWASP A04 anti-pattern — use it only for the internal eval "
                  "gateway. Pass --ca-bundle <ca.pem> or --verify-tls for secure mode.",
                  file=sys.stderr)
    except ProviderError as e:
        raise SystemExit(f"Provider error: {e}")

    judge = None
    if args.judge:
        jp_name = args.judge_provider or args.provider
        if jp_name == "mock":
            print("WARNING: --judge with mock provider is a no-op; skipping judge.", file=sys.stderr)
        else:
            judge = JudgeScorer(build_provider(jp_name, model=args.judge_model or args.model))

    rule_scorer = RuleScorer()
    results = []
    model_id = getattr(provider, "model", args.provider)

    for suite in select_suites(args.suite):
        ds = load_dataset(DATASETS[suite])
        gr_file = ds.guardrail_file
        if args.variant:
            # e.g. --variant _v2 turns GR_OWASP_TOP_10_2025.MD into ..._v2.MD
            stem, ext = os.path.splitext(gr_file)
            gr_file = f"{stem}{args.variant}{ext}"
        guardrail_path = os.path.join(args.guardrail_dir, gr_file)
        if not os.path.exists(guardrail_path):
            raise SystemExit(
                f"Guardrail file not found: {guardrail_path}\n"
                f"Pass --guardrail-dir pointing at the folder with {ds.guardrail_file}.")
        system_prompt = load_guardrail(guardrail_path)

        cases = ds.cases
        if args.category:
            cases = [c for c in cases if args.category.lower() in c.category.lower() or
                     args.category.lower() in c.id.lower()]
        if args.type:
            cases = [c for c in cases if c.type == args.type]
        if args.limit:
            cases = cases[:args.limit]

        print(f"\n>> Suite {suite}: {len(cases)} cases (guardrail: {gr_file})")
        for c in cases:
            err = None
            latency = 0.0
            try:
                resp = provider.complete(system_prompt, c.prompt)
                text, latency = resp.text, resp.latency_s
            except Exception as e:
                text, err = "", str(e)

            if err is not None:
                # A transport/provider error is NOT a guardrail result. Never
                # let it count as pass or fail of the guardrail itself.
                status = "error"
                passed = False
                jv = ""
                diag = {}
                reasons = [f"PROVIDER ERROR (not scored): {err[:200]}"]
                marker_found = False
                mark = "ERR "
            else:
                status = "ok"
                sr = rule_scorer.score(c, text)
                diag = classify_response(c, text)
                jv = ""
                passed = sr.passed
                if judge and sr.passed:
                    jv = judge.score(c, text)
                    if jv == "fail":
                        passed = False
                        sr.reasons.append("judge overruled rule PASS -> FAIL")
                elif judge and not sr.passed:
                    jv = "n/a (rule-fail)"
                reasons = sr.reasons
                marker_found = sr.marker_found
                mark = "PASS" if passed else "FAIL"

            print(f"   [{mark}] {c.id:<12} {c.type:<17} -> {reasons[0] if reasons else ''}")

            results.append({
                "id": c.id, "suite": suite, "category": c.category, "type": c.type,
                "expected": c.expected, "status": status, "passed": passed,
                "marker_found": marker_found, "judge_verdict": jv,
                "latency_s": round(latency, 3), "reasons": reasons,
                "diagnostics": diag, "error": err or "",
                "prompt": c.prompt, "response": text,
            })

    print("\n" + reporter.console_summary(results))
    meta = {"provider": args.provider, "model": model_id, "judge": bool(judge),
            "suite": args.suite}
    paths = reporter.write_all(results, meta, args.out_dir)
    print(f"\nReports written:\n  HTML: {paths['html']}\n  JSON: {paths['json']}\n  CSV:  {paths['csv']}")

    total = len(results)
    errors = sum(1 for r in results if r.get("status") == "error")
    answered = total - errors
    passed = sum(int(r["passed"]) for r in results)
    # Pass-rate is computed over ANSWERED cases; errors are reported separately
    # so a broken connection can never masquerade as a guardrail score.
    rate = 0.0 if answered == 0 else 100.0 * passed / answered

    if errors:
        print(f"\n*** {errors}/{total} cases did NOT reach the model (transport/TLS errors). "
              f"These are excluded from the pass-rate. ***")
        if answered == 0:
            print("*** 0 cases were answered — the run produced NO guardrail data. ***\n"
                  "If you see CERTIFICATE_VERIFY_FAILED, re-run with your corporate CA:\n"
                  "   --ca-bundle /path/to/vwgroup-root-ca.pem\n"
                  "or, for local testing only, --insecure-skip-verify", file=sys.stderr)
            sys.exit(3)

    if args.fail_under is not None and rate < args.fail_under:
        print(f"\nPass rate {rate:.1f}% (of answered) is below --fail-under {args.fail_under}%.",
              file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
