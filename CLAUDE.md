# Wiggum

## Delegation Policy

**STRICT RULE -- no exceptions.** When a skill (`.claude/skills/` or `plugins/wiggum/skills/`) or agent (`.claude/agents/` or `plugins/wiggum/agents/`) exists for a task, you MUST delegate to it. Never perform the task inline. Before performing any non-trivial action, check whether a matching skill or agent exists and use it.

Rationale: skills and agents carry project-specific conventions and workflows that must not be bypassed or approximated from memory.

## Quick Reference

- **Language**: Python 3.14+
- **Package manager**: uv (do NOT use pip, poetry, or conda)
- **Linter/formatter**: ruff (do NOT use black, isort, or flake8)
- **Type checker**: pyright (strict mode)
- **Test framework**: pytest + pytest-asyncio
- **Layout**: src layout (`src/wiggum/`)

## Commands

All commands use `uv run` directly. No task runner.

```
uv sync                                    # install dependencies
uv run ruff check src/ tests/              # lint
uv run ruff check --fix src/ tests/        # lint with auto-fix
uv run ruff format src/ tests/             # format
uv run pyright                             # type check
uv run pytest                              # test
uv run pytest --cov --cov-report=term-missing  # test with coverage
uv run pre-commit install                  # install git hooks
uv run pre-commit run --all-files          # run all hooks
```

## Layout

```
src/wiggum/                  # package source
tests/                       # test files mirror src/ structure
plugins/wiggum/              # wiggum Claude Code plugin (marketplace)
  skills/                    # plugin skills (invoke as /wiggum:<name>)
  agents/                    # plugin agents (researcher/, prd-writer)
  scripts/                   # shared shell scripts (symlinked into skills)
  hooks/                     # plugin hook configuration
bin/                         # convenience symlinks (claude-dev)
.claude-plugin/              # marketplace manifest
.wiggum/                     # runtime artifacts (specs, research)
```

## Plugin Development

```
./bin/claude-dev                           # launch claude with local plugin
./bin/claude-dev --resume                  # resume a previous session
```

Plugin skills are namespaced: `/wiggum:propose-feature`, `/wiggum:create-feature-prd`, `/wiggum:review-feature-prd`.
