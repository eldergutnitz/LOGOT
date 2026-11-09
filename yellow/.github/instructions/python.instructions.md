---
applyTo: "**/*.py"
---

# Python — Level 2

Approved shapes: **Streamlit** for internal data apps, **FastAPI** or **Flask** for internal APIs and
plain Python for jobs and ETL, with **PostgreSQL** as the database.

## Baseline

- Python **3.11+**, PEP 8, `snake_case`. Full type hints on every public function; run `mypy` or
  `pyright` in CI.
- Pin dependencies with a committed lockfile (`uv.lock` or a hash-pinned `requirements.txt`).
  Official PyPI only — no VCS or URL installs.
- `ruff` for lint and format. Use `logging`, not `print()`.

## Security

- **Secrets** from environment or vault via `os.environ` / `st.secrets`. Validate every required
  secret at startup and raise if it is missing — fail closed, never fall back to a default.
- **Never** `eval`, `exec`, `pickle.loads` on untrusted data, `yaml.load` without `SafeLoader`,
  `subprocess` with `shell=True`, or a `setup.py` that decodes-and-runs.
- SQL through parameterised drivers or the ORM — never f-strings or `%` into a query.
- Validate every boundary with **Pydantic** models; never trust an API response or request payload.
- Catch narrow exceptions. Never `except Exception: pass`. Log with context, re-raise or fail closed.

## Streamlit

- Streamlit reruns the whole script on every interaction — put expensive work behind
  `@st.cache_data` (serialisable results) or `@st.cache_resource` (connections, models), with a `ttl`.
- Database connections belong in `@st.cache_resource`, never opened per rerun.
- `secrets.toml` is **git-ignored**, never committed.
- Streamlit has **no built-in authorisation**. Access control is enforced by the deployment behind
  **ISAM / CloudIDP / GRP**; never gate on a password typed into a widget.
- `unsafe_allow_html=True` is forbidden for any value that is not a hard-coded literal.
- Keep `st.session_state` keys explicit and namespaced; treat everything in it as user-controlled.

## Testing

Use `pytest`, with fixtures for setup, `monkeypatch` for environment variables and
`respx`/`responses` for HTTP. Test logic and data access as you build. Before review, cover
malformed payloads, unauthorised callers and missing secrets for the changed code, and meet the
repository's coverage threshold if one is set. Run data-access tests against a local PostgreSQL, not
a different in-memory dialect. For Streamlit, extract logic into plain functions and test those.
