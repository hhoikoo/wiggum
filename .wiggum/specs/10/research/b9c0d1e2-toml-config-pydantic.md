# Research: TOML Configuration with Pydantic Validation

## Question

Best practices for TOML configuration in Python CLI tools using pydantic for validation.

## Findings

### Loading TOML with tomllib

- `tomllib` in stdlib since Python 3.11 -- no dependency needed for Python 3.14+
- `load()` from binary file object, `loads()` from string
- Files must be opened in `"rb"` mode

### Validating with Pydantic

Standard pattern: `BaseModel` (not `BaseSettings`) when loading manually.

```python
import tomllib
from pathlib import Path
from pydantic import BaseModel, Field

class Config(BaseModel):
    debug: bool = False
    workers: int = Field(default=4, ge=1, le=64)

def load_config(path: Path) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return Config.model_validate(raw)
```

- Nested config handled natively -- pydantic fills sub-models from nested TOML tables
- Missing sub-tables fall back to sub-model defaults
- `Field()` constraints for domain validation beyond type checking

### Layering: Defaults < Config File < CLI

Two approaches:
1. **pydantic-settings** (`BaseSettings` + `settings_customise_sources`): handles multi-source layering with customizable priority tuple. Adds a dependency but eliminates ~50 lines of merge boilerplate.
2. **Manual**: load TOML to dict, merge CLI overrides on top, pass to `model_validate()`. Simpler, no extra dependency.

Standard precedence (highest to lowest): constructor args > CLI args > env vars > TOML config > field defaults.

### Config File Discovery

Industry-standard algorithm (used by ruff, black, uv, mypy, pytest):
1. Start from cwd
2. Walk upward through `Path.parents`
3. Check for sentinel file at each level
4. Stop at first match or at `.git` directory

```python
def find_config(name: str = ".wiggum/config.toml", start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / name
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None
```

Multiple candidates: check both `wiggum.toml` and `pyproject.toml [tool.wiggum]` at each level (how ruff does it). For `pyproject.toml`, verify the `[tool.wiggum]` table exists.

User-level config: `$XDG_CONFIG_HOME/wiggum/config.toml` via `platformdirs`.

### Recommendations

- Use `tomllib` directly (no dependency for Python 3.14+)
- Use `pydantic.BaseModel.model_validate()` for validation
- Sentinel-based upward walk stopping at `.git` for discovery
- Layer: field defaults < config file < CLI overrides
- Consider `pydantic-settings` only if env var support or multi-file deep merge needed

## Sources

- Python tomllib docs
- Pydantic settings docs
- Ruff configuration docs
- uv configuration docs
