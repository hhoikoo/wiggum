---
name: feature-work-on
description: Start implementation work on a proposal. Creates an implementation ticket, sets up a git worktree and tmux session, and launches wiggum run.
argument-hint: "<proposal-issue-number>"
---

# Feature Work On

Takes a proposal issue (created by `/wiggum:feature-propose`), creates an implementation ticket, sets up an isolated worktree with a tmux session, and launches `wiggum run` to begin autonomous implementation.

## Phase 1: Resolve Proposal Spec

Read `$ARGUMENTS` as the proposal issue number.

1. Fetch the proposal issue details:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/fetch-issue.sh <proposal-issue-number>
   ```
   Parse the JSON output. Extract `summary` (issue title) and `key` (issue number).

2. Locate the spec directory at `.wiggum/specs/<proposal-issue-number>/` relative to the git root. Read the PRD markdown file inside it (the largest `.md` file, excluding `RESEARCH.md`).

3. If the spec directory does not exist, stop with an error: "No spec found at .wiggum/specs/<proposal-issue-number>/. Run /wiggum:feature-propose first."

## Phase 2: Determine Implementation Ticket Type

Scan the PRD content for an `## Implementation Sketch` section. Count the number of `**Phase N:**` entries:

- **2 or more phases**: type is **Epic** (multi-phase implementation)
- **Exactly 1 phase**: type is **Story** (single-phase implementation)
- **No Implementation Sketch section**: type is **Task**

## Phase 3: Create Implementation Ticket

Delegate to `/wiggum:create-issue` with structured flags:

```
/wiggum:create-issue -t <type> -s "<feature-name>" -P <proposal-issue-number>
```

Where `<feature-name>` is derived from the proposal title by stripping the `Proposal: ` prefix. The `-P` flag links the implementation ticket as a sub-issue of the proposal.

Capture the created issue number from the skill output. This is `<impl-ticket>`.

## Phase 4: Derive Naming

Compute these values for later steps:

- **repo-name**: `basename "$(git remote get-url origin)" .git`
- **feature-slug**: 2-4 kebab-case words from the feature name, lowercase, stripped of filler words (the, a, an, is, for, to, in, on, with)
- **session-name**: `wiggum-<repo-name>-<feature-slug>`
- **window-name**: `<impl-ticket>`
- **branch-name**: `feat/<impl-ticket>/<feature-slug>`

## Phase 5: Create Worktree and Session

Launch session-launch.sh without `--command`. The `--no-claude` flag skips the Claude TUI launch, leaving a bare shell in the tmux window.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/session-launch.sh \
  --ticket-id <impl-ticket> \
  --repo-path "$(git rev-parse --show-toplevel)" \
  --base-branch main \
  --branch-name <branch-name> \
  --session-name <session-name> \
  --window-name <window-name> \
  --no-claude
```

Capture the tmux target from stdout (format: `<session>:<window>`).

If the script exits 0 with "already exists" on stderr, the worktree and window are reused. This is expected for idempotent re-invocation -- skip Phases 6-7 and go directly to Phase 8.

If the script fails, report the error and stop.

## Phase 6: Set Up Implementation Directory

After session-launch.sh creates the worktree, set up the required directories inside it:

```bash
worktree_path="$(git rev-parse --show-toplevel)/.wiggum/worktrees/<impl-ticket>"
mkdir -p "${worktree_path}/.wiggum/specs/<impl-ticket>"
mkdir -p "${worktree_path}/.wiggum/implementation/<impl-ticket>"
```

Copy all spec files from the proposal into the implementation spec directory:

```bash
cp -r "$(git rev-parse --show-toplevel)/.wiggum/specs/<proposal-issue-number>/." "${worktree_path}/.wiggum/specs/<impl-ticket>/"
```

## Phase 7: Launch wiggum run

Send the implementation command to the tmux window. Directory setup from Phase 6 must complete before this step.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/tmux-send.sh "<tmux-target>" "uv run wiggum run <impl-ticket>"
```

## Phase 8: Report

Print a summary for the user:

```
Implementation ticket created: #<impl-ticket> - <feature-name>
Parent proposal: #<proposal-issue-number>

Implementation started in background:
  tmux session:   <session-name>
  tmux window:    <window-name>
  worktree:       .wiggum/worktrees/<impl-ticket>/
  branch:         <branch-name>

To watch progress:
  tmux attach -t <session-name>
```

## Rules

- Always delegate issue creation to `/wiggum:create-issue`. Never create issues directly.
- The spawned session runs `wiggum run` independently. Do not wait for it to complete.
- Phase 6 must complete before Phase 7. The implementation directory and specs must exist before `wiggum run` starts.
- If the tmux window already exists (idempotent re-run), skip Phases 5-7 and report the existing session details.

$ARGUMENTS
