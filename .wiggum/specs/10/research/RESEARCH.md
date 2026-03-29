# RESEARCH.md -- Executive Research Summary for Ticket #10

## Executive Summary

Ticket #10 implements the first working version of `wiggum run`, a Python CLI that replaces the bash `ralph.sh` bootstrap script. The implementation is deliberately minimal: direct subprocess calls to `claude`, no hexagonal architecture, no tmux, no PRD generation, and no PR lifecycle. The existing codebase provides a clean slate -- a bare cyclopts `App` with no commands, an empty package structure, and no config file -- so the entire feature is greenfield. All major design questions (CLI structure, config loading, subprocess management, interrupt handling) have been answered by the nine research files and converge on a consistent, straightforward pattern.

## Current State

**What exists today:**

- `src/wiggum/cli.py` -- two lines: `import cyclopts` and `app = cyclopts.App(name="wiggum")`. No commands registered.
- `pyproject.toml` -- entry point `wiggum = "wiggum.cli:app"`. Dependencies include `cyclopts>=4,<5` and `pydantic>=2,<3`. Runtime is Python 3.14+. No `tomllib` dependency needed (stdlib since 3.11).
- `samples/ralph-bootstrap/ralph.sh` -- bash loop that drives claude invocations. Supports PRD auto-conversion (one-shot), branch archiving, main iteration loop with `<promise>COMPLETE</promise>` sentinel, and a 10-step agent prompt template. State lives entirely in files on disk (`prd.json`, `progress.md`).
- `.wiggum/` -- no `config.toml` exists. Directory holds `worktrees/` (gitignored) and `specs/<ticket-id>/` (research, PRD output).
- `tests/` -- only an empty `conftest.py`. No CLI tests.

**What ralph.sh currently does that the new CLI must replicate:**
- Takes `<issue-id>` and optional `[max_iterations]` (default 10)
- Per-iteration: pipes prompt to `claude --dangerously-skip-permissions --print`
- Detects `<promise>COMPLETE</promise>` sentinel in claude output
- Appends structured entries to `progress.md`
- Exits with structured JSON on completion or iteration exhaustion

**What ralph.sh does that the new CLI must NOT replicate:**
- PRD auto-conversion (bash one-shot bootstrap)
- Branch archiving logic
- tmux session management

## Target Design

**CLI command structure:**

```
wiggum run <issue-id>          # combined: plan then build
wiggum run plan <issue-id>     # plan only
wiggum run build <issue-id>    # build only
```

Implemented via a two-level cyclopts sub-app.

**Config from `.wiggum/config.toml` validated by pydantic:**

- Loaded via `tomllib` (stdlib, no new dependency)
- Validated via `pydantic.BaseModel.model_validate()`
- Discovered via upward walk from cwd, stopping at `.git`
- Config file does not yet exist -- must be created as part of this ticket
- Layering: field defaults < config file < CLI arguments

**PROGRESS.md:** Append-only log written after each completed build iteration. Structured entries (timestamp, iteration number, summary). Persists across interrupted runs.

**SIGINT handling:** Register `signal.signal(SIGINT, handler)` before starting loop. Handler must re-register `SIG_IGN` immediately, reset uncommitted `[x]` marks, terminate subprocess gracefully, then `sys.exit(130)`. Use `subprocess.Popen` for claude invocations.

## Key Patterns to Adopt

**From ralph loop guide:**
- Plan mode and build mode are separate concerns with separate prompt templates
- One task per iteration, fresh context per iteration
- All acceptance criteria must be verifiable shell commands before loop starts
- Numbered step structure in prompts (0a-0d orientation, 1-4 main, 99+ guardrails, 999+ constraints, 9999+ invariants)

**From ralph.sh:**
- State communicated entirely via files; each claude invocation is stateless
- `<promise>COMPLETE</promise>` sentinel for loop exit detection
- `tee /dev/stderr` pattern for live visibility
- Structured JSON output on exit

**From design doc:**
- Spec file as the only interface between skill and CLI
- All state persists through git-committed files

## Architecture Decisions

**Config loading:** `tomllib.load()` + `pydantic.BaseModel.model_validate()`. Walk from cwd up to `.git` sentinel. Missing config file falls back to defaults.

**Subprocess management:** `subprocess.Popen` for all claude invocations. Prompt via stdin, capture stdout for sentinel detection, stream stderr for visibility. Graceful termination: SIGTERM -> wait(timeout=5) -> SIGKILL -> wait().

**CLI structure:** cyclopts child `App(name="run")` registered on root app. Sub-subcommands `plan`, `build`, and a default handler for combined mode.

**SIGINT and cleanup:** Handler registered before loop. Responsible for stopping subprocess, resetting uncommitted marks, writing partial-run marker to PROGRESS.md, then exit 130.

## Constraints and Non-Goals

Explicitly excluded from ticket #10:
- No hexagonal ports/adapters -- direct subprocess calls
- No tmux session management
- No PRD generation pipeline
- No PR lifecycle
- No daemon mode
- No `wiggum resume` command
- No parallel agent batching
- No PRD auto-conversion
- No branch archiving

## Open Questions

1. **Task tracker format.** ralph.sh uses `prd.json` with `passes: true/false` per story. The ticket's "uncommitted `[x]` marks" language implies markdown checkboxes, not JSON. Which format?

2. **Prompt template ownership.** Where do plan and build prompt templates live? Embedded in Python package, in `.wiggum/`, or in the spec directory?

3. **Specs directory resolution.** ralph.sh looks under `.wiggum/specs/<issue-id>/*.md`. How does the new CLI resolve this path -- relative to cwd, git root, or from config?

4. **Combined mode sequencing.** Does `wiggum run <issue-id>` run plan once then build until complete, interleave, or prompt for confirmation between phases?

5. **Config schema.** Full set of configurable values beyond `max_iterations` and `claude_flags` is undefined.

6. **Exit code contract.** Success (0), exhaustion (1), and interrupt (130) are clear, but other failure modes are not specified.

7. **PROGRESS.md entry format.** Markdown, JSON lines, or free text? Exact fields not defined.

8. **Async vs sync.** cyclopts supports async natively, but the single-subprocess loop may not need it. Not specified.
