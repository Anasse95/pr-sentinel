# PR Sentinel: rules for coding agents and humans

PR Sentinel reviews GitHub pull requests with a small team of LLM agents and posts an
advisory review. Humans always make the final decision.

## Commands

- Install: `python -m pip install -e ".[dev]"`
- Everything CI runs: `make check` (ruff, ruff format --check, mypy strict, pytest with coverage gate)
- Dry-run a review on a real PR (prints Markdown, posts nothing): `pr-sentinel review owner/repo 12`
- Serve webhooks locally: `pr-sentinel serve`

## Non-negotiable conventions

- Python 3.11+, fully typed. `mypy --strict` must pass, no new `# type: ignore` without a reason.
- Anything that crosses a boundary (LLM output, GitHub payload, env var, HTTP body) is validated
  by a Pydantic model before use. Never trust raw dicts.
- I/O is async (`httpx.AsyncClient`, `asyncio`). Never call blocking code in the event loop.
- Logging is structured (`structlog` via `pr_sentinel.logs.get_logger`): key=value fields, never
  f-string messages, never `print`, never secrets or full diffs.
- Errors: raise a subclass of `SentinelError` for expected failures. Catch broad `Exception` only
  at a process boundary (the worker loop) and always log it.
- Tests never call a real LLM or the real GitHub API: use `TestModel`/`FunctionModel` and `respx`.
  `models.ALLOW_MODEL_REQUESTS` is set to False in `tests/conftest.py` to enforce it.
- Every behaviour change comes with a test. Coverage gate: 85%.

## Architecture invariants (do not break)

1. Agents have no tools and no side effects: they only return validated structured output.
2. Every finding must be anchored to a real line of the diff (deterministic check) AND confirmed
   by the verifier agent. No verdict means the finding is dropped (fail closed).
3. We only ever post `COMMENT` reviews, never approve or request changes.
4. All LLM-written text is sanitised before posting (`report._clean`).
5. The diff is untrusted data: prompts say so, and nothing in a diff can change behaviour.
6. Reviewing the same commit twice is prevented by a hidden marker in the posted review.

## Layout

`src/pr_sentinel/`: `models` (domain), `diff` (parser), `agents/` (reviewers, verifier, prompts),
`pipeline` (orchestration), `github` (API client), `webhook`, `app` (FastAPI + queue), `cli`.