# Workspace Instructions for skysolve-next

## 1. Source Code Organization
- **Main Application**: All new and updated code should reside in the `skysolve_next/` directory, following its substructure (e.g., `core/`, `solver/`, `web/`, `workers/`).
- **Legacy Code**: The `skysolve_legacy/` directory contains not only older scripts, but also the reference implementation for the "next" solution. Consult this directory for original logic, algorithms, or behavior that must be preserved or ported. Do not modify unless explicitly required.
- **Tests**: All unit and integration tests are located in the `tests/` directory. Any code changes must be accompanied by relevant tests here.
- **Static Assets**: Images, styles, and static files are under `images/` and `skysolve_next/web/static/`.
- **Templates**: HTML templates are in `skysolve_next/web/templates/`.
- **Docs & Scripts**: Documentation is in `docs/`; utility scripts are in `scripts/`.

## 2. Requirements for Code Changes
- **Understand the Problem**: Review related code, documentation, and requirements before making changes.
- **Backward Compatibility**: Ensure changes do not break existing functionality unless refactoring is explicitly requested.
- **Documentation**: Update or add docstrings and comments as needed. Update `docs/` if the change affects user-facing features or APIs.
- **Configuration**: If changes require new settings, update `settings.json` and document them.

## 3. Testing
- **Test Coverage**: All new features and bug fixes must include or update unit tests in `tests/`.
- **Test Execution**: Run all tests (`pytest` recommended) after any code change. Ensure all tests pass before considering the change complete.
- **Test Quality**: Write clear, isolated, and meaningful tests. Use mocks/stubs for external dependencies.

## 4. Python Code Standards
- **Formatting**: Follow PEP8 and use tools like `black` or `flake8` for formatting and linting.
- **Type Hints**: Use type annotations where possible for clarity and static analysis.
- **Imports**: Organize imports (standard library, third-party, local) and remove unused imports.
- **Error Handling**: Use explicit exception handling and meaningful error messages.
- **Dependencies**: Add new dependencies to `pyproject.toml` and ensure they are documented.

## 5. General Best Practices
- **Atomic Commits**: Make small, focused commits with clear messages.
- **Code Review**: All changes should be reviewed, either by a peer or via self-review.
- **Security**: Never commit secrets or credentials. Use `.env` or configuration files for sensitive data.
- **Environment**: Use virtual environments (`.venv`) for Python dependencies.

## 6. Getting Started
- Review this file and the project structure before making changes.
- If unsure, check the README or relevant documentation in `docs/`.
- When in doubt, ask for clarification or add a TODO comment for follow-up.

---
This file is intended to help you quickly understand the workspace and maintain high standards for code quality, testing, and collaboration.
