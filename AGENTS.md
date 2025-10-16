# Repository Guidelines

## Project Structure & Module Organization
- `lib/`: core Python package containing signal math, scoring logic, and API clients (`signals.py`, `scoring.py`, `polygon_client.py`).
- `jobs/`: schedulable entrypoints for the post-close and pre-market pipelines.
- `config/` and `supabase/`: runtime configuration helpers and database migrations; update these together when schemas or secrets change.
- `examples/`: self-contained scripts demonstrating how to score earnings events.
- `tests/`: pytest suite mirroring the `lib/` and `jobs/` modules; add new files under matching directories.
- `dashboard/`: React dashboard artifacts; coordinate API changes with the frontend team before breaking endpoints.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate`: standard development environment.
- `pip install -r requirements.txt && pip install -e .[dev]`: install runtime deps plus dev extras in editable mode.
- `pytest`: run the full suite; use `-k` filters for targeted checks.
- `python jobs/post_close.py` and `python jobs/pre_market.py --update-scores`: execute production pipelines; add `--date YYYY-MM-DD` for historical runs.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation, meaningful snake_case for variables/functions, and PascalCase for classes.
- Maintain type hints and docstrings as seen across `lib/`. Prefer pure functions with explicit inputs/outputs to ease testing.
- Use pandas/numpy vector operations where practical; avoid silent mutation of global state outside `config/`.

## Testing Guidelines
- Pytest is the standard. Mirror new modules with `tests/test_<module>.py` files and name functions `test_<behavior>()`.
- Verify new scoring logic against realistic fixtures (see `tests/test_signals.py`), especially when adjusting OI, delta, or expiry calculations.
- Document any dependency on external APIs with `@pytest.mark.skipif` safeguards or recorded fixtures.

## Commit & Pull Request Guidelines
- Keep commit messages concise, present-tense, and task-focused (e.g., `add delta spread guardrails` as seen in `git log`).
- Group related code, config, and migration changes in a single pull request; include a summary, data sources touched, and screenshots for dashboard updates.
- Link issues or job tickets in the PR description, and note test commands executed (`pytest`, pipeline dry-runs). Highlight required secret or schema updates upfront.

## Environment & Secrets
- Store API credentials in `.env`; never hardcode keys in Python or dashboard assets.
- When updating Supabase schemas (`supabase/migrations/`), document the expected downgrade path and coordinate with database maintainers before deployment.
