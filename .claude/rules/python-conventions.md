---
paths:
  - "src/**/*.py"
  - "scripts/**/*.py"
---
# Python Conventions

> **Scope**: This project is primarily shell scripts and plugin definitions. These rules apply to Python files under `src/` and `scripts/`.

## Type System

- Type hints required on all function signatures (parameters and return types).
- Prefer Pydantic models or `dataclasses` for structured data. `TypedDict` is acceptable but not preferred over those two. All three are preferred over plain `dict`.
- Use `Enum` or `StrEnum` over string constants for fixed value sets.
- Use `Protocol` for structural typing where duck typing is needed.
- Use PEP 604 union syntax (`X | None`). Python 3.14 has deferred evaluation of annotations natively (PEP 649/749), so `from __future__ import annotations` is unnecessary.
- Use `typing.TYPE_CHECKING` guard for import-only type references to avoid circular imports.
- Prefer `collections.abc` types (`Sequence`, `Mapping`, `Iterable`) over concrete types in function signatures.

## Function Signatures

- Use keyword-only arguments (after `*`) when a function accepts more than 2-3 parameters. This enforces named arguments at call sites and prevents positional-order mistakes.
- For functions with many related parameters, prefer grouping them into a dataclass or Pydantic model instead of a flat parameter list.

## Naming

- Classes: `PascalCase`.
- Functions, methods, variables: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Private attributes/methods: single leading underscore `_name`.
- Avoid abbreviations unless they are universally understood (`db`, `id`, `url`).

## Standard Library Preferences

- `pathlib.Path` over `os.path`.
- `dataclasses` or `attrs` for simple data containers.
- `enum.StrEnum` for string enumerations.
- `contextlib.asynccontextmanager` for async resource management.
- `functools.cached_property` for expensive computed properties.

## Comments and Docstrings

- Code is the primary documentation. Prefer clear naming and structure over comments or docstrings.
- Docstrings only where the interface is non-obvious: ABCs, Protocols, and public API entry points consumed by external callers.
- When a docstring is used, keep it minimal -- one-liner preferred. Multi-line only when parameters or return values are genuinely unclear from the signature and type hints.
