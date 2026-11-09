"""
Dataset + guardrail loading.

A tiny YAML subset parser is bundled so the harness runs with zero pip installs.
If PyYAML is available it is used (more robust); otherwise the bundled parser
handles the structure used by the shipped datasets (lists of mappings, block
scalars with '>'). Keep datasets in that style and you need no dependencies.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except Exception:  # pragma: no cover
    _HAVE_YAML = False


@dataclass
class TestCase:
    id: str
    category: str
    type: str
    expected: str
    prompt: str
    assertions: dict = field(default_factory=dict)
    suite: str = ""


@dataclass
class Dataset:
    suite: str
    guardrail_file: str
    cases: list


def load_guardrail(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_dataset(path: str) -> Dataset:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    data = _parse_yaml(raw)
    suite = data.get("suite", "")
    cases = []
    for c in data.get("cases", []):
        cases.append(TestCase(
            id=c["id"],
            category=c.get("category", ""),
            type=c.get("type", ""),
            expected=c.get("expected", ""),
            prompt=" ".join(str(c.get("prompt", "")).split()),
            assertions=c.get("assertions", {}) or {},
            suite=suite,
        ))
    return Dataset(suite=suite, guardrail_file=data.get("guardrail_file", ""), cases=cases)


# --------------------------------------------------------------------------- #
# YAML handling
# --------------------------------------------------------------------------- #
def _parse_yaml(raw: str) -> dict:
    if _HAVE_YAML:
        return yaml.safe_load(raw)
    return _MiniYAML(raw).parse()


class _MiniYAML:
    """
    Minimal YAML parser covering exactly the constructs used by the shipped
    datasets: top-level scalars, a 'cases:' list of mappings, nested mappings
    (assertions), nested lists (expect_any / forbid / expect_all), and block
    scalars introduced with '>'. Not a general YAML implementation.
    """

    def __init__(self, raw: str):
        self.lines = [ln.rstrip("\n") for ln in raw.split("\n")]
        self.i = 0

    def parse(self) -> dict:
        return self._parse_block(0)

    def _strip_comment(self, s: str) -> str:
        # Remove unquoted trailing comments.
        out, in_s, in_d = [], False, False
        for ch in s:
            if ch == "'" and not in_d:
                in_s = not in_s
            elif ch == '"' and not in_s:
                in_d = not in_d
            elif ch == "#" and not in_s and not in_d:
                break
            out.append(ch)
        return "".join(out)

    def _indent(self, line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def _next_meaningful(self, start: int):
        j = start
        while j < len(self.lines):
            content = self._strip_comment(self.lines[j])
            if content.strip() == "":
                j += 1
                continue
            return j, content
        return None, None

    def _parse_block(self, min_indent: int):
        # Decide whether this block is a list or a mapping by peeking.
        j, content = self._next_meaningful(self.i)
        if j is None:
            return {}
        indent = self._indent(content)
        if indent < min_indent:
            return {}
        if content.lstrip().startswith("- "):
            return self._parse_list(indent)
        return self._parse_map(indent)

    def _parse_map(self, indent: int) -> dict:
        result = {}
        while self.i < len(self.lines):
            j, content = self._next_meaningful(self.i)
            if j is None:
                break
            cur = self._indent(content)
            if cur < indent:
                break
            if cur > indent:
                self.i = j + 1
                continue
            self.i = j
            stripped = content.strip()
            if stripped.startswith("- "):
                break
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            self.i = j + 1
            if val == ">" or val == "|" or val.startswith(">") or val.startswith("|"):
                result[key] = self._read_block_scalar(indent)
            elif val == "":
                # Nested structure or empty.
                nxt_j, nxt_content = self._next_meaningful(self.i)
                if nxt_j is not None and self._indent(nxt_content) > indent:
                    result[key] = self._parse_block(self._indent(nxt_content))
                else:
                    result[key] = {}
            else:
                result[key] = _scalar(val)
        return result

    def _parse_list(self, indent: int) -> list:
        items = []
        while self.i < len(self.lines):
            j, content = self._next_meaningful(self.i)
            if j is None:
                break
            cur = self._indent(content)
            if cur < indent or not content.strip().startswith("- "):
                break
            # Rewrite "- key: val" as a mapping line at indent+2.
            rest = content.strip()[2:]
            inner_indent = indent + 2
            self.lines[j] = " " * inner_indent + rest
            self.i = j
            if ":" in rest and not rest.startswith(("'", '"')):
                item = self._parse_map(inner_indent)
            else:
                self.i = j + 1
                item = _scalar(rest.strip())
            items.append(item)
        return items

    def _read_block_scalar(self, parent_indent: int) -> str:
        out = []
        block_indent = None
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() == "":
                out.append("")
                self.i += 1
                continue
            ind = self._indent(line)
            if ind <= parent_indent:
                break
            if block_indent is None:
                block_indent = ind
            out.append(line[block_indent:])
            self.i += 1
        # Folded style: join with spaces.
        return " ".join(s.strip() for s in out if s.strip() != "").strip()


def _scalar(v: str):
    if len(v) >= 2 and v[0] == v[-1] == '"':
        # Double-quoted: process YAML escape sequences.
        inner = v[1:-1]
        return (inner.replace('\\\\', '\x00')      # protect literal backslashes
                     .replace('\\"', '"')
                     .replace('\\n', '\n')
                     .replace('\\t', '\t')
                     .replace('\x00', '\\'))
    if len(v) >= 2 and v[0] == v[-1] == "'":
        # Single-quoted: only '' -> ' ; no other escapes.
        return v[1:-1].replace("''", "'")
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~", ""):
        return None
    return v
