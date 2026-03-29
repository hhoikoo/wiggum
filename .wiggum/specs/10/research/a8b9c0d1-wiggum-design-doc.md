# Research: Wiggum Design Document (Outdated)

## Question

What does the wiggum design doc describe about the architecture, CLI commands, and overall vision?

**Note**: The ticket marks this document as outdated. Focus on general architecture and vision, not specific details.

## Findings

### Two-Component Architecture

- **Claude Code Skill** (interactive): handles human-facing planning, produces `specs/<feature>.md`
- **Wiggum CLI** (autonomous): consumes spec files, runs plan/build loops
- Spec file format is the only interface -- no shared code, no IPC, no runtime state

### Hexagonal Architecture (CLI)

- All external interactions (git, tmux, Claude agent CLI) through Python `Protocol`-based ports
- Shell adapters using `subprocess.run()`
- Core loop logic fully decoupled from tool invocation
- Adapters swappable (e.g., libtmux alternative)

### Five-Phase Pipeline

Setup -> Proposal -> PRD Creation -> Implementation -> PR Lifecycle

All long-running work in tmux sessions with git worktrees for isolation. No intermediate state beyond committed files -- everything persists through git.

### CLI Commands

- `wiggum run <spec-file>` -- core ralph loop
- `wiggum resume` -- rediscover dead sessions and relaunch
- `wiggum daemon` -- persistent process for automatic issue pickup
- Built on cyclopts, entry point `wiggum.cli:app`
- Distributed via `uv tool install`

### Ralph Loop (Outer + Inner)

- **Outer loop**: launches up to 500 parallel research agents, produces/updates PLAN.md
- **Inner loop**: TDD cycle -- testability gate -> Red agent (failing tests) -> Green agent (all tests pass) -> mark done -> commit
- Continuous batching: 5 concurrent agents, 10-15 items per outer cycle
- Each agent iteration is fresh process with clean context

### Configuration Model

- Project config: `.wiggum/config.toml` (tomllib + pydantic)
- System override: `~/.wiggum/config.toml` for locked-down repos
- Startup validates git repo presence and config discoverability

### Phased Roadmap

| Phase | Scope |
|-------|-------|
| 1 | Core ralph loop (manual specs, manual issue/branch/PR) |
| 1.5 | Hardening: SIGINT, rebase-before-loop, worktree symlinks |
| 2 | PR lifecycle automation |
| 3 | PRD creation loop + daemon |
| 4 | Interactive Claude Code skills |
| 5 | Extensions: subissue parallelism, courtroom review, ticket provider abstraction |

Phase 1 ralph loop is used to build subsequent phases -- self-bootstrapping.

## Relevance to Ticket #10

Ticket #10 implements Phase 1 of this roadmap. Key deviations from the design doc:
- **No hexagonal architecture** -- ticket explicitly says "No hexagonal ports/adapters -- direct subprocess calls, refactor later"
- **No tmux session management** -- explicitly a non-goal
- **No PRD generation pipeline** -- explicitly a non-goal
- **No PR lifecycle** -- explicitly a non-goal
- Config model (.wiggum/config.toml with pydantic) aligns with design doc
