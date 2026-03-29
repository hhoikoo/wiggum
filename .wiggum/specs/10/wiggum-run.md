# PRD: Implement Core Ralph Loop CLI (`wiggum run`)

**Ticket:** #10
**Date:** 2026-03-29

---

## Summary

The project needs a Python CLI (`wiggum run`) to replace the bash `ralph.sh` bootstrap script, providing a two-mode plan/build loop that drives autonomous Claude Code invocations. The solution adds three commands -- `wiggum run <issue-id>` (combined), `wiggum run plan <issue-id>` (plan-only), and `wiggum run build <issue-id>` (build-only) -- using direct `subprocess.Popen` calls against the `claude` binary, with config from `.wiggum/config.toml` validated by pydantic. The primary tradeoff is deliberately skipping hexagonal architecture (no ports/adapters) in favor of shipping a working loop fast, accepting that subprocess calls will be inlined and refactored later. `wiggum run` is one component in a larger orchestration pipeline: companion skills (`feature-work-on`, `feature-stop-work-on`) handle environment setup (implementation ticket, worktree, tmux session) and teardown, while `wiggum run` operates within that prepared environment.

Each mode runs an iteration loop. Plan mode reads specs from a configurable specs directory (defaulting to `.wiggum/specs/<issue-id>/` relative to the git root), feeds a plan prompt template to `claude -p --dangerously-skip-permissions`, and produces/updates `IMPLEMENTATION_PLAN.md` within `.wiggum/implementation/<ticket-num>/`. Plan mode runs up to `max_plan_iterations` (default 5) iterations but exits early when the claude agent signals completion via a fenced JSON code block containing `{"status": "complete"}`. Build mode reads that plan, picks the top unchecked task, implements it via a build prompt template, runs quality checks defined in config, marks the task done, and the build prompt instructs claude to run the `/commit` skill. Each iteration spawns a fresh `claude -p` process -- no conversation history carries over. A SIGINT handler resets any uncommitted `[x]` marks and terminates the subprocess gracefully. `PROGRESS.md` (also in `.wiggum/implementation/<ticket-num>/`) accumulates an append-only log across iterations using heading-per-iteration format, and the build prompt instructs claude to update both `PROGRESS.md` (patterns section) and the project's `CLAUDE.md` files with reusable conventions learned during implementation.

This approach directly ports the proven `ralph.sh` loop to Python with three improvements: structured config (TOML + pydantic with defaults and CLI overrides), clean interrupt handling (SIGINT resets state instead of corrupting it), and explicit plan/build mode separation (the bash script conflates both into a single prompt). The alternative of building hexagonal architecture first was rejected by the ticket scope -- the loop is the critical path and needs to work before abstractions are layered on.

## Goals

- Replace `ralph.sh` with a Python CLI that runs fully autonomous plan and build loops against the `claude` binary.
- Support three invocation modes: combined (`run <id>`), plan-only (`run plan <id>`), and build-only (`run build <id>`).
- Ship prompt templates as package data files (`src/wiggum/templates/*.md`) loaded via `importlib.resources`, with `string.Template` `$variable` interpolation for value injection.
- Load configuration from `.wiggum/config.toml` with pydantic validation and sensible defaults when no config file exists.
- Handle SIGINT gracefully: terminate subprocess, reset uncommitted task marks in `IMPLEMENTATION_PLAN.md`, exit 130.
- Maintain an append-only `PROGRESS.md` log with heading-per-iteration entries recording task completed, outcome, and codebase patterns learned.
- Produce structured JSON on stdout at loop completion (matching `ralph.sh` contract) for downstream tooling.

## Non-Goals

- No hexagonal ports/adapters architecture (ticket explicitly defers this -- direct subprocess calls, refactor later).
- No tmux session management or worktree creation (handled by companion `feature-work-on` skill, not this CLI).
- No PRD generation pipeline (specs are consumed as input, not produced -- `propose-feature` and `create-feature-prd` skills handle creation).
- No PR lifecycle automation (creating, updating, or merging PRs is out of scope for Phase 1).
- No parallel agent instances or concurrent iteration batching (single-threaded loop per invocation; parallelism deferred to Phase 5 roadmap).

## Orchestration Context

`wiggum run` is the loop engine, not the entry point for feature work. Companion skills set up and tear down the environment:

**`feature-work-on` skill (future, not part of this ticket):**
- Accepts a proposal spec (issue number or file path).
- Creates an implementation ticket (epic, story, or task depending on size) with a brief summary. This ticket registers an issue number used for branch names, PRs, and the implementation directory.
- Creates a tmux session named `wiggum-<repo-name>-<feature-name>` with window 0 named `<ticket-num>`.
- Creates a git worktree for the implementation branch.
- The tmux/worktree structure supports future subdivision into subissues for epic-level work.

**`feature-stop-work-on` skill (future, not part of this ticket):**
- Cleans up worktree, tmux session, and creates/updates PR as needed.

`wiggum run` assumes it is invoked inside a prepared worktree where `.wiggum/implementation/<ticket-num>/` already exists (created by `feature-work-on` or manually). The CLI validates this directory exists at startup and exits with code 2 if missing.

## Architecture

```
                      +---------------------+
                      | feature-work-on     |
                      | (companion skill)   |
                      +----------+----------+
                                 |
                    creates ticket, worktree,
                    tmux, implementation dir
                                 |
                                 v
                      +------------------+
                      |  wiggum run CLI  |
                      |  (cli.py / run)  |
                      +--------+---------+
                               |
                  +------------+------------+
                  |                         |
           +------+------+          +-------+------+
           |  plan mode  |          |  build mode  |
           |  (runner)   |          |  (runner)    |
           +------+------+          +-------+------+
                  |                         |
     +------------+------------+   +--------+---------+
     |            |            |   |        |         |
+---------+ +---------+ +-----+   |  +-----+---+ +---+----+
| config  | |templates| |specs|   |  |IMPL_PLAN| |PROGRESS|
| .toml   | | .md pkg | | .md |   |  |  .md    | |  .md   |
| loader  | | data    | |files|   |  +---------+ +--------+
+---------+ +---------+ +-----+   |
                                  |  .wiggum/implementation/<ticket>/
                                  |
                          +-------+--------+
                          | subprocess     |
                          | .Popen         |
                          | (claude -p     |
                          |  --danger...)  |
                          +-------+--------+
                                  |
                          +-------+--------+
                          | SIGINT handler  |
                          | - SIG_IGN       |
                          | - reset [x]     |
                          | - terminate     |
                          | - exit 130      |
                          +----------------+

                      +---------------------+
                      | feature-stop-work-on|
                      | (companion skill)   |
                      +---------------------+
                      cleanup: worktree, tmux, PR
```

Data flow: Config is loaded once at startup. Specs directory is resolved from config (`specs_dir`) or defaults to `.wiggum/specs/` relative to the git root. Implementation artifacts (`IMPLEMENTATION_PLAN.md`, `PROGRESS.md`) live in `.wiggum/implementation/<ticket-num>/` and are version-controlled. The CLI validates the implementation directory exists at startup, then on each iteration constructs a prompt from template files + current file state, pipes it to `claude -p --dangerously-skip-permissions` via `Popen`, captures stdout, and updates `IMPLEMENTATION_PLAN.md` and `PROGRESS.md` as side effects. The build prompt also instructs claude to update `CLAUDE.md` files with reusable patterns.

## Design Decisions

1. **Markdown checkboxes for task tracking, not JSON.** The ticket specifies "uncommitted `[x]` marks" which maps to markdown checkboxes in `IMPLEMENTATION_PLAN.md`. This aligns with the ralph loop guide (which uses `IMPLEMENTATION_PLAN.md` as a markdown file) and diverges from `ralph.sh` (which uses `prd.json` with `passes: true/false`). Markdown is human-readable, diff-friendly, and editable by both Claude and humans without tooling.

2. **Prompt templates as package data files loaded via `importlib.resources`.** Templates are `.md` files in `src/wiggum/templates/` (e.g., `plan.md`, `build.md`), not Python string constants or external files in `.wiggum/`. This keeps templates versioned with the CLI code, avoids requiring users to manage template files, and makes the content easy to read and edit in isolation. `importlib.resources` handles path resolution across installed and editable installs. The implementation agent drafts the prompt content from the ralph loop guide, following the numbered-step convention (0a-0d orientation, 1-4 main, 99+ guardrails, 999+ constraints) and preserving load-bearing phrases.

3. **`subprocess.Popen` for all claude invocations.** Required for SIGINT handling -- `subprocess.run` does not allow reacting to signals during execution. Prompt is piped via stdin, stdout is captured, stderr streams to the terminal for live visibility.

4. **Hybrid plan completion: max iterations with early exit on fenced JSON signal.** Plan mode runs up to `max_plan_iterations` (default 5) but exits early when the claude agent outputs a fenced JSON code block indicating the plan is complete. The plan prompt instructs claude to end its output with a fenced JSON block (` ```json\n{"status": "complete"}\n``` ` or ` ```json\n{"status": "in_progress"}\n``` `). The CLI extracts the last fenced JSON block from stdout and parses its `status` field. If the CLI detects `"status": "complete"`, the plan loop exits immediately. Otherwise, iteration continues up to the max. This avoids wasting iterations when the plan converges early (typical in 1-3 iterations) while capping runtime for plans that never stabilize.

5. **Quality commands are config-only, not hardcoded.** All quality checks are defined in `.wiggum/config.toml` under `[loop]` as `quality_commands` (a list of shell command strings). The build prompt reads this list and instructs claude to run them. If `quality_commands` is empty or unset, the build prompt omits quality check instructions entirely. This avoids coupling the CLI to any specific toolchain and lets each project define its own checks.

6. **`--dangerously-skip-permissions` always passed.** `wiggum run` is inherently autonomous; users opt in to unattended execution by running the command itself. Adding a separate flag or config toggle would be redundant -- there is no meaningful use of `wiggum run` that involves interactive permission prompts.

7. **Specs directory resolution via config with git root fallback.** The `specs_dir` field in `.wiggum/config.toml` can override the default. When unset, the CLI resolves `.wiggum/specs/` relative to the git root (found by walking up to `.git`). This handles monorepos and non-standard layouts while keeping the common case zero-config.

8. **Build prompt instructs claude to update CLAUDE.md and PROGRESS.md with patterns.** No separate `AGENTS.md` file. The build prompt tells claude to append a patterns section to `PROGRESS.md` per iteration and update the project's `CLAUDE.md` files with reusable conventions and learnings. This matches the existing wiggum convention where `CLAUDE.md` is the living conventions file, avoiding a parallel file that would drift.

9. **Combined mode runs plan then build without confirmation.** `wiggum run <issue-id>` executes plan mode (up to `max_plan_iterations` iterations, with early exit) to produce/update `IMPLEMENTATION_PLAN.md`, then immediately transitions to build mode (up to `max_build_iterations` iterations). No user confirmation between phases -- the combined mode is meant for fully autonomous operation.

10. **Synchronous execution, no async.** The loop is inherently sequential (one subprocess at a time, wait for completion, check result, repeat). Async adds complexity with no benefit. cyclopts supports async natively if this changes later.

11. **Exit codes follow Unix convention.** 0 = all tasks complete, 1 = max iterations reached without completion, 2 = startup failure (missing specs, invalid config, missing implementation directory), 130 = interrupted by SIGINT.

12. **Config discovery via upward directory walk to `.git` sentinel.** Matches the pattern used by ruff, uv, and other Python tooling. Start from cwd, walk parents, check for `.wiggum/config.toml` at each level, stop at `.git`. Missing config falls back to pydantic model defaults -- the CLI works without any config file.

13. **`string.Template` with `$variable` syntax for prompt template interpolation.** Safe (no code execution), stdlib-only, and familiar. Sufficient for simple value injection into `.md` templates -- the templates need variable substitution for specs content, plan state, config values, and quality commands, but do not need conditionals or loops. `str.format()` conflicts with curly braces in markdown/code content. Jinja2 supports conditionals but adds an external dependency for a feature that can be handled by conditional string concatenation in the render functions. Optional sections (e.g., quality commands) are assembled in Python before substitution rather than expressed as template logic.

14. **PROGRESS.md uses heading-per-iteration format.** Each entry starts with `## Iteration N (YYYY-MM-DDTHH:MM:SS)` followed by bullet points for task completed, outcome (pass/fail/interrupted), and codebase patterns learned. Headings are easy to scan, easy to append, and produce clean diffs. Tables or fenced blocks would require parsing surrounding structure to append correctly; headings are self-contained.

15. **Build prompt instructs claude to run the `/commit` skill, not raw `git commit`.** The `/commit` skill delegates to the project's conventional commit conventions via the wiggum commit skill, producing consistent commit messages that follow project standards. The CLI itself does not run any git commands after iteration completion -- commit responsibility is fully delegated to the claude subprocess via the prompt. This avoids duplicating commit message formatting logic and keeps the CLI decoupled from git workflow details.

16. **Implementation artifacts live in `.wiggum/implementation/<ticket-num>/`.** `IMPLEMENTATION_PLAN.md`, `PROGRESS.md`, and any other loop-generated files are stored under `.wiggum/implementation/<ticket-num>/` where `<ticket-num>` is the implementation ticket number (not the proposal ticket). These files are version-controlled (committed to git). The CLI validates this directory exists at startup and creates skeleton `IMPLEMENTATION_PLAN.md` and `PROGRESS.md` files if they are missing (but the directory itself must exist -- created by `feature-work-on` or manually). This separates implementation state from spec/proposal state in `.wiggum/specs/`, keeps each implementation self-contained in its own directory, and ties artifacts to the implementation ticket that branch names and PRs reference.

17. **Implementation ticket number passed as a CLI argument.** `wiggum run <issue-id>` takes the implementation ticket number as a positional argument. The `feature-work-on` companion skill passes it when launching. This resolves `.wiggum/implementation/<issue-id>/` directly from the argument with no ambiguity. Deriving the ticket from the branch name would couple the CLI to a naming convention and break when branches are renamed or follow non-standard patterns. Reading from a file in `.wiggum/implementation/` would require a discovery step and introduce questions about which file, what format, and what happens when multiple implementation directories exist.

18. **Plan completion signal uses a fenced JSON code block.** The plan prompt instructs claude to wrap its status output in a fenced JSON block (` ```json\n{"status": "complete"}\n``` `). The CLI extracts the last fenced JSON block from stdout by scanning for ` ```json ` / ` ``` ` delimiters and parses the JSON within. This is robust against JSON appearing in claude's reasoning text -- bare JSON lines could match incidental JSON in explanations or code examples, but fenced blocks with the ` ```json ` opening are unambiguous in practice. If no fenced JSON block is found, the iteration is treated as `in_progress` (graceful degradation).

## Config Schema

`.wiggum/config.toml` fields, all optional with defaults:

| Field | Type | Default | Description |
|---|---|---|---|
| `[loop]` | | | |
| `loop.max_plan_iterations` | `int` | `5` | Maximum plan mode iterations (exits early on completion signal). |
| `loop.max_build_iterations` | `int` | `25` | Maximum build mode iterations before exiting with code 1. |
| `loop.quality_commands` | `list[str]` | `[]` | Shell commands the build prompt instructs claude to run (e.g., `["uv run pyright", "uv run ruff check src/ tests/", "uv run pytest"]`). Empty means no quality instructions in the build prompt. |
| `[claude]` | | | |
| `claude.model` | `str \| null` | `null` | Claude model to use (passed as `--model` flag). Null means use claude's default. |
| `claude.flags` | `list[str]` | `[]` | Additional flags passed to every `claude -p` invocation. |
| *(top-level)* | | | |
| `specs_dir` | `str \| null` | `null` | Override for specs directory. Absolute path or relative to git root. Null means `.wiggum/specs/` relative to git root. |

Example `.wiggum/config.toml`:

```toml
specs_dir = ".wiggum/specs"

[loop]
max_plan_iterations = 5
max_build_iterations = 25
quality_commands = [
    "uv run pyright",
    "uv run ruff check src/ tests/",
    "uv run pytest",
]

[claude]
model = "sonnet"
flags = ["--verbose"]
```

The pydantic model validates types and ranges (e.g., `max_plan_iterations >= 1`). CLI flags `--max-iterations` and `--model` override the corresponding config values. The pydantic model uses nested models for `loop` and `claude` sections.

## Required Changes

| Component | Change |
|---|---|
| `src/wiggum/cli.py` | Register `run_app` child App with `plan`, `build`, and default (combined) commands. Wire up parameter parsing for `issue_id`, `--max-iterations`, `--model`. Accept `--impl-dir` or derive implementation directory from ticket number. |
| `src/wiggum/config.py` (new) | Pydantic `Config` model with nested `LoopConfig` and `ClaudeConfig` models. Fields: `specs_dir` (top-level), `loop.max_plan_iterations`, `loop.max_build_iterations`, `loop.quality_commands`, `claude.model`, `claude.flags`. `find_config()` upward walk. `load_config()` with tomllib + model_validate. |
| `src/wiggum/runner.py` (new) | Core loop logic: `run_plan()`, `run_build()`, `run_combined()`. Iteration loop, subprocess invocation, file updates. Plan mode extracts the last fenced JSON block from claude output to detect early completion. Validates `.wiggum/implementation/<ticket-num>/` exists at startup, creates skeleton plan/progress files if missing. |
| `src/wiggum/templates/plan.md` (new) | Plan mode prompt template using `string.Template` `$variable` placeholders. Numbered-step structure from ralph loop guide. Includes instruction for claude to output a fenced JSON code block (` ```json\n{"status": "complete"}\n``` ` or ` ```json\n{"status": "in_progress"}\n``` `) at end of response. Loaded via `importlib.resources`. |
| `src/wiggum/templates/build.md` (new) | Build mode prompt template using `string.Template` `$variable` placeholders. Includes quality command injection point, `/commit` skill instruction, CLAUDE.md/PROGRESS.md update instructions. |
| `src/wiggum/templates/__init__.py` (new) | Helper to load template files via `importlib.resources` and render them with `string.Template.safe_substitute()`. `load_template(name: str) -> string.Template` and `render_template(name: str, **kwargs) -> str`. |
| `src/wiggum/prompts.py` (new) | `render_plan_prompt()` and `render_build_prompt()` functions that load templates and substitute specs content, plan state, config values, and quality commands. Optional sections (quality commands) are assembled as strings before substitution. |
| `src/wiggum/subprocess_util.py` (new) | `invoke_claude()` wrapping `Popen` with stdin prompt, stdout capture, stderr passthrough. Always passes `--dangerously-skip-permissions`. Returns structured result including stdout for fenced JSON block extraction. `terminate_subprocess()` with SIGTERM/SIGKILL sequence. |
| `src/wiggum/interrupt.py` (new) | SIGINT handler registration, `SIG_IGN` re-register, uncommitted `[x]` mark reset in `IMPLEMENTATION_PLAN.md`, subprocess termination, exit 130. |
| `src/wiggum/plan.py` (new) | `IMPLEMENTATION_PLAN.md` parser: read checkbox items, find unchecked tasks, mark tasks complete, reset uncommitted marks. File path resolved from `.wiggum/implementation/<ticket-num>/`. |
| `src/wiggum/progress.py` (new) | `PROGRESS.md` writer: append heading-per-iteration entry with `## Iteration N (YYYY-MM-DDTHH:MM:SS)` format, bullet points for task, outcome, and patterns. File path resolved from `.wiggum/implementation/<ticket-num>/`. |
| `src/wiggum/impl_dir.py` (new) | Utilities for `.wiggum/implementation/<ticket-num>/` directory: validate existence, create skeleton `IMPLEMENTATION_PLAN.md` and `PROGRESS.md` files if missing, resolve file paths within the directory. |
| `src/wiggum/json_extract.py` (new) | `extract_last_fenced_json(stdout: str) -> dict | None` function that scans for the last ` ```json ` ... ` ``` ` block in stdout and parses the content as JSON. Returns `None` if no fenced JSON block is found. |
| `tests/test_config.py` (new) | Config loading, discovery, defaults, validation errors, `specs_dir` resolution, nested TOML section parsing. |
| `tests/test_runner.py` (new) | Loop iteration logic, mode transitions, early exit on plan completion signal. |
| `tests/test_plan.py` (new) | Plan file parsing, task selection, mark/reset operations. |
| `tests/test_interrupt.py` (new) | SIGINT handler behavior, mark reset on interrupt. |
| `tests/test_prompts.py` (new) | Template loading via `importlib.resources`, `string.Template` substitution, prompt rendering with and without quality commands, plan prompt includes fenced JSON status instruction. |
| `tests/test_cli.py` (new) | CLI argument parsing, subcommand routing via cyclopts test harness. |
| `tests/test_impl_dir.py` (new) | Implementation directory validation, skeleton file creation, path resolution. |
| `tests/test_json_extract.py` (new) | Fenced JSON block extraction: single block, multiple blocks (returns last), no block returns `None`, malformed JSON returns `None`, JSON embedded in reasoning text is ignored when not in a fenced block. |

## Acceptance Tests

- [ ] Given no `.wiggum/config.toml` exists, when `wiggum run plan 10` is invoked, then the CLI starts with default config values (max_plan_iterations=5, empty quality_commands, specs resolved from git root) and does not error on missing config.
- [ ] Given `.wiggum/specs/10/` contains markdown spec files, when `wiggum run plan 10` is invoked, then a fresh `claude -p --dangerously-skip-permissions` process is spawned with a plan prompt that includes the spec file contents.
- [ ] Given plan mode is running and claude outputs a fenced JSON block ` ```json\n{"status": "in_progress"}\n``` ` on each iteration, when the loop executes, then exactly `max_plan_iterations` iterations run (default 5), each spawning a separate claude process.
- [ ] Given plan mode is running and claude outputs a fenced JSON block ` ```json\n{"status": "complete"}\n``` ` on iteration 2, when the CLI extracts the last fenced JSON block from stdout, then the plan loop exits after iteration 2 without running remaining iterations.
- [ ] Given plan mode is running and claude output contains no fenced JSON block, when the CLI scans stdout for ` ```json ` delimiters, then no block is found, the iteration is treated as `in_progress`, and the loop continues to the next iteration (graceful degradation).
- [ ] Given plan mode is running and claude output contains JSON in reasoning text (not in a fenced block) followed by a fenced JSON block with `{"status": "complete"}`, when the CLI extracts the last fenced JSON block, then only the fenced block is parsed and the incidental JSON in reasoning text is ignored.
- [ ] Given plan mode completes, when `.wiggum/implementation/<ticket-num>/IMPLEMENTATION_PLAN.md` is inspected, then it contains markdown checkbox task items produced by the claude invocations.
- [ ] Given `IMPLEMENTATION_PLAN.md` exists with unchecked tasks, when `wiggum run build 10` is invoked, then a build prompt is constructed referencing the top unchecked task, and a fresh `claude -p --dangerously-skip-permissions` process is spawned.
- [ ] Given `.wiggum/config.toml` contains `[loop]` with `quality_commands = ["uv run pyright", "uv run pytest"]`, when a build prompt is rendered, then the prompt text includes instructions for claude to run those specific commands.
- [ ] Given `.wiggum/config.toml` has no `quality_commands` field (or it is empty), when a build prompt is rendered, then the prompt text omits quality check instructions entirely.
- [ ] Given build mode completes an iteration successfully, when the claude subprocess exits 0, then `PROGRESS.md` in `.wiggum/implementation/<ticket-num>/` has a new entry appended under `## Iteration N (YYYY-MM-DDTHH:MM:SS)` with bullet points for task completed, outcome, and patterns learned.
- [ ] Given build mode completes a task, when the iteration finishes, then the corresponding `[ ]` in `IMPLEMENTATION_PLAN.md` is marked `[x]` and the build prompt has instructed claude to run the `/commit` skill.
- [ ] Given all tasks in `IMPLEMENTATION_PLAN.md` are marked `[x]`, when the build loop checks for remaining work, then the loop exits with code 0 and prints a JSON summary to stdout.
- [ ] Given `max_build_iterations` is set to 3 in config, when the build loop reaches iteration 3 without all tasks complete, then it exits with code 1 and prints a JSON summary indicating max iterations reached.
- [ ] Given a build iteration is in progress, when SIGINT (Ctrl+C) is received, then the claude subprocess is terminated (SIGTERM then SIGKILL), any `[x]` marks added during the current iteration are reverted to `[ ]`, and the process exits with code 130.
- [ ] Given `.wiggum/specs/99/` does not exist, when `wiggum run plan 99` is invoked, then the CLI exits with code 2 and prints an error message to stderr indicating missing specs.
- [ ] Given `wiggum run 10` is invoked (combined mode), when plan mode completes (either via early exit or max iterations), then build mode starts automatically without user interaction using the produced `IMPLEMENTATION_PLAN.md`.
- [ ] Given a `.wiggum/config.toml` exists with `[claude]` containing `model = "opus"` and `[loop]` containing `max_build_iterations = 20`, when `wiggum run build 10` is invoked, then the claude subprocess is called with the `--model opus` flag and the loop allows up to 20 iterations.
- [ ] Given `wiggum run build 10 --max-iterations 5` is invoked and config has `max_build_iterations = 20`, when the loop starts, then the CLI override (5) takes precedence over the config file value (20).
- [ ] Given `IMPLEMENTATION_PLAN.md` does not exist in `.wiggum/implementation/<ticket-num>/`, when `wiggum run build 10` is invoked, then the CLI exits with code 2 and prints an error message indicating no implementation plan found.
- [ ] Given `.wiggum/config.toml` contains `specs_dir = "custom/specs"`, when `wiggum run plan 10` is invoked, then specs are read from `custom/specs/10/` relative to the git root instead of `.wiggum/specs/10/`.
- [ ] Given prompt templates exist at `src/wiggum/templates/plan.md` and `src/wiggum/templates/build.md`, when the CLI loads them via `importlib.resources`, then the full template content is returned without filesystem path assumptions.
- [ ] Given a plan template contains `$specs_content` and `$issue_id` placeholders, when `render_plan_prompt()` is called with those values, then `string.Template.safe_substitute()` replaces the placeholders and leaves any unrecognized `$` references intact.
- [ ] Given a build template contains `$quality_section` and quality commands are empty, when `render_build_prompt()` is called, then the quality section variable is substituted with an empty string and no quality instructions appear in the rendered prompt.
- [ ] Given `.wiggum/implementation/<ticket-num>/` does not exist, when `wiggum run plan 10` is invoked, then the CLI exits with code 2 and prints an error message indicating the implementation directory is missing.
- [ ] Given `.wiggum/implementation/<ticket-num>/` exists but contains no files, when `wiggum run plan 10` is invoked, then the CLI creates skeleton `IMPLEMENTATION_PLAN.md` and `PROGRESS.md` files in the directory before starting the plan loop.

## Implementation Sketch

**Phase 1: Config and CLI skeleton.** Add the pydantic `Config` model with nested `LoopConfig` (`max_plan_iterations`, `max_build_iterations`, `quality_commands`) and `ClaudeConfig` (`model`, `flags`) models, plus top-level `specs_dir`. Implement `find_config()` discovery via upward walk and `load_config()` with tomllib + model_validate. Register the `run` sub-app on the existing cyclopts root app with `plan`, `build`, and default commands. Tests for config loading, discovery, defaults, nested section parsing, and `specs_dir` resolution.

**Phase 2: Implementation directory and file infrastructure.** Create `impl_dir.py` with utilities for `.wiggum/implementation/<ticket-num>/` directory validation, skeleton file creation, and path resolution. The skeleton `IMPLEMENTATION_PLAN.md` contains a title and empty checkbox section; the skeleton `PROGRESS.md` contains a title. Tests for directory validation and skeleton creation.

**Phase 3: Templates, subprocess, and prompt infrastructure.** Create `src/wiggum/templates/` with `plan.md` and `build.md` template files drafted from the ralph loop guide's numbered-step structure, using `$variable` placeholders for `string.Template` substitution. The plan template includes instructions for claude to output a fenced JSON code block at the end of each response. Implement `importlib.resources`-based template loader returning `string.Template` instances. Implement `invoke_claude()` using `Popen` with stdin prompt piping, stdout capture, stderr passthrough, and `--dangerously-skip-permissions` always set. Implement `extract_last_fenced_json()` for parsing the last fenced JSON block from stdout. Write `render_plan_prompt()` and `render_build_prompt()` that load templates, assemble optional sections (quality commands, `/commit` skill instruction) as Python strings, and pass them to `safe_substitute()`. Tests for template loading, prompt rendering, fenced JSON extraction, and subprocess invocation (mocked).

**Phase 4: Plan mode loop with early exit.** Implement `run_plan()`: resolve specs directory from config, validate implementation directory, read specs from `<specs_dir>/<issue-id>/`, render plan prompt, invoke claude, extract last fenced JSON block from stdout, exit early on completion signal or continue to next iteration. Repeat for up to `max_plan_iterations`. Tests for plan loop logic with mocked subprocess, including early exit and graceful degradation on missing fenced JSON block.

**Phase 5: Build mode loop.** Implement `IMPLEMENTATION_PLAN.md` parser (read checkboxes, find top unchecked task, mark complete). Implement `run_build()`: read plan, select task, render build prompt (with quality commands from config, `/commit` skill instruction, and instructions to update CLAUDE.md/PROGRESS.md patterns), invoke claude, update plan, append heading-per-iteration entry to `PROGRESS.md`, repeat. Tests for plan parsing, task selection, and build loop logic.

**Phase 6: SIGINT handling and combined mode.** Register SIGINT handler before loop entry. Implement mark-reset logic (track which `[x]` marks were added in the current iteration, revert on interrupt). Implement `run_combined()` that chains plan then build. Wire exit codes (0, 1, 2, 130). Integration tests for interrupt behavior and combined mode sequencing.

## Alternatives Considered

| Approach | Why not |
|---|---|
| Hexagonal architecture with Protocol-based ports | Ticket #10 explicitly excludes this. The loop needs to ship first; abstractions layered in a later ticket when the interface is proven through use. |
| `subprocess.run` instead of `Popen` | Cannot handle SIGINT during execution. `run` blocks until completion with no way to terminate the child or run cleanup mid-invocation. |
| JSON task tracker (`prd.json` style) | The ticket specifies "uncommitted `[x]` marks" which implies markdown checkboxes. Markdown is also what the ralph loop guide uses for `IMPLEMENTATION_PLAN.md`. JSON adds a conversion step with no benefit. |
| Async iteration loop | Single sequential subprocess per iteration -- async adds complexity (event loop, signal handling differences) with no concurrency benefit. |
| Prompt templates as Python string constants | Harder to read, edit, and review in isolation. Package data files via `importlib.resources` keep templates versioned with the CLI while allowing direct editing of `.md` files. |
| Prompt templates as external files in `.wiggum/` | Couples CLI version to template version outside the package. Users would need to update templates separately from the CLI. Embedding in the package keeps them synchronized. |
| `pydantic-settings` with `BaseSettings` | Adds a dependency for env var and multi-source layering that is not needed. Manual TOML + `model_validate()` + CLI override merge is ~20 lines and sufficient. |
| `click` or `typer` instead of cyclopts | The project already uses cyclopts with a registered entry point. Switching CLI frameworks is out of scope and would require changing `pyproject.toml` and conventions. |
| Fixed iteration count only for plan completion (no early exit) | Wastes iterations when the plan converges early (typical in 1-3 iterations). Fenced JSON output from the agent is a reliable completion signal that avoids fragile heuristics like file diffing while keeping the max as a safety cap. |
| Hardcoded quality commands in build prompt | Couples the CLI to a specific toolchain (pyright, ruff, pytest). Config-only quality commands let each project define its own checks without modifying the CLI. |
| Separate `AGENTS.md` for codebase patterns | Creates a parallel conventions file that drifts from `CLAUDE.md`. The project already uses `CLAUDE.md` as the living conventions file; the build prompt instructs claude to update it directly. |
| `--dangerously-skip-permissions` as opt-in flag | `wiggum run` is inherently autonomous. Requiring users to pass an additional flag to enable what the command already promises adds ceremony without safety -- the opt-in is running `wiggum run` itself. |
| `str.format()` for template interpolation | Curly braces in markdown content and code blocks conflict with `str.format()` replacement fields, requiring double-brace escaping throughout templates. Makes templates unreadable and error-prone. |
| Jinja2 for template interpolation | Adds an external dependency for conditional logic that can be handled by assembling optional sections in Python before substitution. The templates need value injection, not a full template language. |
| Table rows or fenced blocks for PROGRESS.md entries | Tables require parsing surrounding structure to append correctly and are hard to read for multi-line content. Fenced blocks add visual noise. Heading-per-iteration is self-contained, scannable, and produces clean diffs. |
| CLI runs `git commit` directly after iteration | Duplicates commit message formatting logic that the `/commit` skill already encodes. The skill carries project-specific conventional commit conventions. Delegating via the build prompt keeps the CLI decoupled from git workflow details. |
| Implementation files in `.wiggum/specs/<ticket>/` | Conflates proposal/spec artifacts with implementation state. Specs are input to the loop; implementation plan and progress are output. Separating them into `.wiggum/implementation/` keeps concerns distinct and ties artifacts to the implementation ticket number rather than the proposal ticket. |
| Implementation files in the repo root or a `tmp/` directory | Root-level files pollute the project. `tmp/` suggests disposable state, but these files are version-controlled and persist across sessions. `.wiggum/implementation/` is consistent with the existing `.wiggum/` convention for runtime artifacts. |
| Flat config without TOML table sections | All fields at the top level works for a small config, but as the config grows (loop tuning, claude flags, future sections), flat keys become ambiguous. Grouping into `[loop]` and `[claude]` adds structure without over-engineering. |
| Ticket number derived from branch name | Couples the CLI to a branch naming convention that may vary across projects or change over time. Branches can be renamed, and non-standard branch names would require special-case parsing. An explicit CLI argument is unambiguous and works regardless of branch naming patterns. |
| Ticket number read from a file in `.wiggum/implementation/` | Requires a discovery step (which file? what format?) and introduces ambiguity when multiple implementation directories exist. An explicit CLI argument avoids the indirection. |
| Bare JSON line for plan completion signal | A bare JSON line at the end of stdout is fragile -- claude may include JSON snippets in reasoning text, code examples, or error messages that could be mistaken for the completion signal. Fenced JSON blocks (` ```json `) are structurally distinct from incidental JSON in prose. |

## Open Questions

(None -- all previously open questions have been resolved as design decisions.)
