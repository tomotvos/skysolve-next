# copilot-instructions.md

> Repo-level guidance for developer agents (Copilot / VS Code agent mode) and humans.
> This file intentionally *does not* hard-code task priorities. Instead it points to the canonical implementation checklist and instructs agents to check items off there as they are completed: `docs/SKYSOLVE_NEXT_IMPLEMENTATION_PLAN.md` (or `docs/` equivalent).

## Where to look first (required)
1. Functional requirements: `docs/*.md`
1. Architecture overview: top-level package `skysolve_next/` and these directories: `solvers/`, `publish/`, `workers/`, `onstep/`, `web/`, `config/`, `scripts/`, `docs/`.
1. Legacy reference implementation: `skysolve_legacy`
1. Before starting any new work, be **fully** aware of the requirements, existing codebase and its structure.

---

## Development & runtime targets
- **Develop on macOS** (local dev, faster iteration). 
**Deploy to Raspberry Pi (Raspbian / Raspberry Pi OS)** for runtime/production. The repository must support both platforms:
  - Target Python runtime: **Python 3.11** (use the same minor version on Mac and Pi).
  - Use a venv created with `python3.11 -m venv --copies .venv` to avoid symlink issues with Homebrew Python on macOS.
  - Camera hardware access / drivers are Pi-specific: for local dev on macOS, use mocks or pre-recorded images. Tests must avoid requiring physical camera hardware.

---

## Code quality & standardized Python directives (must-haves)
Add/configure these tools and rules in the repository (pyproject.toml + pre-commit) and enforce in CI:

1. **Formatting**
   - `black` (use default 88 char line length or 100 if the team prefers). Configure in `pyproject.toml`.
   - `isort` for import ordering (configured to work with `black`).
   - Provide `pre-commit` hooks that run `black --check`, `isort --check`, and basic `ruff` checks on commit.

2. **Linting / Static analysis**
   - Use `ruff` as primary linter (fast) and optionally `flake8` for any rules not covered. Keep rules strict but pragmatic.
   - `mypy` for type checking. Use `mypy.ini` or `pyproject.toml` config. Start with `strict = False` but enable `disallow_untyped_defs = True` for new modules gradually.
   - Add `pyproject.toml` entries for `tool.ruff`, `tool.isort`, `tool.black`, and `tool.mypy`.

3. **Type hints and docstrings**
   - New modules and public functions should include type hints.
   - Add concise docstrings (reStructuredText or Google style) for modules, classes, and public functions.

4. **Logging and error handling**
   - Use the `logging` module with structured messages when useful. Do not use print() for production code.
   - Log at appropriate levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
   - Avoid broad `except:` catches. Catch and handle expected exceptions and re-raise or log unexpected ones.

5. **Dependency management**
   - Use `pyproject.toml` + `poetry` or `pip` with `requirements.txt` for reproducible installs.
   - Pin direct dependencies in `requirements.txt` for reproducible Pi installs; allow looser versions in `pyproject.toml` if using constraints file.

6. **Packaging**
   - Keep `pyproject.toml` or `setup.cfg` accurate. Ensure `pip install -e .` works on Python 3.11 in a fresh venv.
   - Add `scripts/run_skysolve.sh` that starts workers with absolute interpreter path (`$PWD/.venv/bin/python -u -m ...`) to avoid Homebrew vs venv confusion.

7. **Pre-commit & CI checks**
   - Add `pre-commit` hooks for `black`, `isort`, `ruff`, and running `pytest -q` for quick tests (optional).
   - CI must run: formatting check, lint, mypy (typecheck), unit tests (pytest), and coverage measurement.

---

## Unit tests & testing strategy (guidelines)
Tests are required. Use `pytest` and follow these conventions:

1. **Test organization**
   - `tests/` root. Mirrored structure to `skysolve_next/`, e.g. `tests/solvers/test_astrometry_adapter.py`, `tests/publish/test_lx200_server.py`, `tests/onstep/test_client.py`.
   - Use `conftest.py` for reusable fixtures (e.g., `dummy_image_path`, `mock_solver`, `temp_config`, `mock_onstep_server`).

2. **Mock external systems**
   - **Network**: mock socket operations or run lightweight in-process mock servers (use `pytest` fixtures that run a mock TCP server on an ephemeral port).
   - **Astrometry / Tetra**: do not call real solvers in unit tests. Instead, stub subprocess calls or provide a local fake solver that returns canned outputs. For integration tests, mark them `@pytest.mark.integration` and run them separately (not in the default CI job).
   - **OnStep**: provide a mock OnStep server in tests/mocks that asserts messages received.

3. **Test patterns**
   - Small, fast unit tests should dominate. Integration tests that require native solvers or system packages should be optional and gated.
   - Use `tmp_path` for files, `caplog` for logging assertions, and `monkeypatch` for env or subprocess mocking.
   - Use parametrized tests to cover edge cases (timeouts, malformed responses).

4. **Coverage**
   - Aim for a baseline coverage (e.g., 80%) on core modules (solvers, LX200 server, OnStep client). Be pragmatic — tests for complex native solver pipelines may be integration-only.

5. **Test commands**
   - Local: `pytest -q`
   - With coverage: `pytest --cov=skysolve_next --cov-report=term-missing`

---

## CI / GitHub Actions recommendations
- Matrix: run tests on `ubuntu-latest` and `macos-latest` for Python 3.11; optionally add a self-hosted runner for RPi integration tests.
- Jobs:
  - `lint` (ruff/black/isort checks)
  - `typecheck` (mypy)
  - `unittest` (pytest)
  - `integration` (optional, gated by label or secret)
- Set artifact job to build Pi-friendly tarball or wheel for releases.

---

## Development workflow (quick commands)
```bash
# create reproducible venv (mac or Pi)
python3.11 -m venv --copies .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e .[dev]   # or pip install -r requirements-dev.txt

# formatting / linting
black .
isort .
ruff .

# run tests
pytest -q

# run the web UI and worker (in two terminals)
export SKYSOLVE_MODE=demo
export WEB_PORT=5001
./.venv/bin/python -u -m skysolve_next.web.app
./.venv/bin/python -u -m skysolve_next.workers.solve_worker
```

---

## Platform-specific notes (Mac vs Pi)
- **macOS (developer):**
  - Use Homebrew to install Python 3.11 if not available: `brew install python@3.11`.
  - Beware of Homebrew Python and venv symlink behavior — prefer `venv --copies`.
  - Firewall: provide PF instructions for testing and mention `socketfilterfw` for app-level changes in docs when necessary.

- **Raspberry Pi (deployment):**
  - Use `python3.11` (install via apt or pyenv if necessary). Create venv with `--copies`.
  - System deps: `libjpeg-dev`, `build-essential`, `git`, and any astrometry index dependencies. Document exact packages in `scripts/install_pi.sh`.
  - Use `systemd` unit file template in `packaging/systemd/skysolve.service` to run the runner script.

---

## Commit/PR conventions (reminder)
- Branches: `feature/<short>`, `fix/<short>`, `chore/<short>`.
- PR title: `<area>: short description` (e.g., `solvers: add astrometry adapter`).
- Include test plan and instructions to run in PR description. Reference the Implementation Plan checklist item(s) completed.

---

## Where to record progress & issues
- Implementation progress: update `docs/SKYSOLVE_NEXT_IMPLEMENTATION_PLAN.md` — check items off as completed and add brief notes about implementation decisions or blockers.
- Bugs & tasks: use the repo issue tracker; reference checklist items and PR numbers.

---

## Final note
This file is intentionally lightweight and stable. **Do not** duplicate task lists here — always use `docs/SKYSOLVE_NEXT_IMPLEMENTATION_PLAN.md` as the canonical checklist. Keep this file focused on reproducible developer practices, code quality rules, testing guidance, and Mac↔Pi portability notes.

# EOF
