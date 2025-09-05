# Skysolve Next: Code Optimization Analysis and Refactor Plan

## Code Review Summary

This document summarizes code quality issues and optimization opportunities identified in the `skysolve_next` codebase, along with a prioritized refactor plan.

---

## Issues & Opportunities

### 1. Code Structure & Organization
- Separation of concerns is lacking in some modules; business logic, I/O, and configuration are mixed.
- Duplicated logic (e.g., `write_status` in multiple files).

### 2. Error Handling
- Broad `except Exception` blocks; prefer specific exceptions.
- Errors are sometimes only logged or returned as strings, not raised or handled structurally.

### 3. Type Annotations & Typing
- Inconsistent use of type hints.
- Some parameters and return values lack type annotations.

### 4. Logging
- Logger setup is repeated; should be centralized.
- Log messages could use more granularity and context.

### 5. Configuration Management
- `reload_if_changed` logic is convoluted; could be simplified.
- Hardcoded file paths; use `pathlib.Path`.

### 6. API & Data Validation
- Inconsistent use of Pydantic models for request/response validation.
- Input validation is sometimes insufficient.

### 7. Concurrency & Threading
- Shared state is not always protected by locks.
- Mix of async and sync endpoints; prefer async for I/O-bound operations.

### 8. Miscellaneous
- Magic numbers/strings; use named constants.
- Code duplication (e.g., RA/Dec formatting logic).
- Lack of test coverage for core modules.

### 9. Performance
- Repeated file I/O for settings/status; consider caching or batching.
- Solver fallback logic is incomplete or commented out.

---

## Prioritized Refactor Plan

### High Priority
- Refactor duplicated logic (e.g., `write_status`) into shared utilities.
- Add input validation and use Pydantic models for all API endpoints.
- Protect shared state with locks where needed.
- Centralize logger configuration.
- Add unit and integration tests for core modules.

### Medium Priority
- Replace hardcoded file paths with `pathlib.Path`.
- Add/complete type annotations throughout the codebase.
- Refactor RA/Dec formatting logic into a shared utility.
- Simplify and clarify `reload_if_changed` logic.
- Use named constants for magic numbers/strings.

### Low Priority
- Optimize file I/O (batch updates, caching if needed).
- Improve logging granularity and context.
- Review and improve error handling (use custom exceptions where appropriate).
- Ensure async endpoints for I/O-bound FastAPI routes.
- Complete and robustly implement solver fallback logic.

---

This plan should guide incremental improvements to code quality, maintainability, and performance in the `skysolve_next` project.
