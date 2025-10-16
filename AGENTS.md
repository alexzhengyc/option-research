# Repository Guidelines

## Project Structure & Module Organization
- Core logic lives under `lib/`, split into `signals.py`, `scoring.py`, and `polygon_client.py`; keep new signal math and API integrations alongside related modules.
- Scheduled entrypoints are in `jobs/`; each script should remain runnable via `python jobs/<name>.py`.
- Runtime configuration sits in `config/`, while matching database migrations reside in `supabase/`; update both together when schemas or secrets change.
- `examples/` hosts runnable scoring walkthroughs, and `tests/` mirrors the `lib/` and `jobs/` layout for pytest coverage.
- Coordinate API changes with the `dashboard/` React team before altering endpoints or payloads.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate` — bootstrap a virtualenv for local development.
- `pip install -r requirements.txt && pip install -e .[dev]` — install runtime dependencies plus dev extras in editable mode.
- `pytest` — run the full automated suite; add `-k name` for targeted checks.
- `python jobs/post_close.py` and `python jobs/pre_market.py --update-scores` — execute production pipelines; append `--date YYYY-MM-DD` for backfills.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation, snake_case for functions and variables, and PascalCase for classes.
- Maintain type hints and concise docstrings consistent with existing `lib/` modules.
- Prefer vectorized pandas/numpy operations; avoid mutating global state outside `config/`.

## Testing Guidelines
- Use pytest; mirror new modules with `tests/test_<module>.py` and functions named `test_<behavior>()`.
- Guard external API dependencies with fixtures or `@pytest.mark.skipif` conditions.
- Validate scoring adjustments against realistic fixtures (see `tests/test_signals.py`) before shipping.

## Commit & Pull Request Guidelines
- Keep commit messages short, present-tense, and task-focused, e.g., `add delta spread guardrails`.
- PRs should bundle related code, config, and migrations, include a concise summary, linked issue or ticket, executed test commands, and dashboard screenshots when UI changes occur.
- Call out required secret updates or schema migrations up front.

## Security & Configuration Tips
- Store all credentials in `.env`; never commit keys to the repo.
- Document Supabase migration downgrade paths and coordinate deployments with database maintainers.
