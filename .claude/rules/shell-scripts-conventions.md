---
paths:
  - "plugins/**/*.sh"
  - ".claude/hooks/*.sh"
---
# Shell Script Conventions

Rules for deterministic shell scripts in `plugins/` and `.claude/hooks/`.

## Header

Every script starts with:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

## I/O Contract

- **Inputs:** environment variables with `:?` guards for required values (e.g., `${GITHUB_TOKEN:?}`).
- **Stdout:** structured JSON via `jq`. Scripts produce machine-readable output consumed by other tools. Side-effect-only scripts (those that return only an exit code with no novel data) are exempt from the JSON stdout requirement.
- **Stderr:** human-readable diagnostics and progress messages.
- **Exit codes:** `0` = success, `1` = expected failure (bad input, missing resource), `2` = unexpected failure (network error, tool crash).

## Behavior

- Idempotent. Running a script twice with the same inputs produces the same result.
- No interactive prompts. Scripts must work unattended.
- No color codes or ANSI escape sequences. Output is consumed by other programs, not humans.

## Naming

- Format: `<verb>-<noun>.sh` (e.g., `create-branch.sh`, `list-issues.sh`).
- Group by domain in `plugins/common/scripts/` and `plugins/common/providers/`; by skill in `plugins/*/skills/*/scripts/`.

## Security

- Never log secrets or tokens. Mask or omit sensitive values from stderr.
- Validate all external input (env vars, API responses) before using in commands.
- Quote all variable expansions: `"${var}"`, not `$var`.

## Dependencies

Assumed available: `jq`, `curl`, `git`, `gh`. Document any additional dependencies in a comment at the top of the script.

## Linting

All scripts must pass `shellcheck`. No suppressed warnings without a justifying comment. Shellcheck directives do not support inline comments after `--`. Put the explanation on a separate comment line above the directive:

```bash
# word splitting is intentional here
# shellcheck disable=SC2086
```
