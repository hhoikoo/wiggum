# Research: ralph.sh Bootstrap Script

## Question

What does the current ralph.sh bootstrap script do? What's its loop structure, how does it invoke claude, what modes does it support, and what prompt templates does it use?

## Findings

### Script Structure

- Takes `<issue-id>` (required) and `[max_iterations]` (default 10)
- Derives paths: `prd.json`, `progress.md`, `archive/`, `.last-branch`, `agent-prompt.md`, `convert-prd-prompt.md`

### PRD Auto-Conversion (One-Shot Bootstrap)

- If `prd.json` does not exist, locates markdown PRD under `.wiggum/specs/<issue-id>/` (excludes `research/`)
- Invokes `claude -p "<prompt>" --dangerously-skip-permissions` with `convert-prd-prompt.md` content + raw PRD
- Claude writes `prd.json` as file side effect; script exits 2 if not produced
- Runs exactly once per new feature branch

### Branch Archiving

- Reads `branchName` from `prd.json` via `jq`, compares with `.last-branch`
- On mismatch: archives previous `prd.json` + `progress.md` to `archive/YYYY-MM-DD-<feature>/`, resets `progress.md`

### Main Iteration Loop

- `for` loop 1 to MAX_ITERATIONS
- Each iteration: pipes `agent-prompt.md` via stdin to `claude --dangerously-skip-permissions --print`
- Captures output with `tee /dev/stderr` for live visibility
- Checks for `<promise>COMPLETE</promise>` sentinel in output
- On completion: emits JSON `{"status":"complete",...}` on stdout, exits 0
- On exhaustion: emits `{"status":"max_iterations",...}`, exits 1
- 2-second sleep between iterations

### Agent Prompt Template (agent-prompt.md)

10-step per-iteration workflow:
1. Read `prd.json` and `progress.md`
2. Check out correct branch from `branchName`
3. Pick highest-priority story where `passes: false`
4. Implement it
5. Run `uv run pyright`, `uv run ruff check`, `uv run pytest`
6. Update CLAUDE.md with reusable patterns
7. Commit
8. Set `passes: true` in `prd.json`
9. Append structured progress entry to `progress.md`
10. Reply `<promise>COMPLETE</promise>` when all stories pass

One story per iteration enforced explicitly.

### Convert-PRD Prompt Template (convert-prd-prompt.md)

Converts markdown PRD to structured `prd.json` with fields:
- `project`, `branchName` (prefixed `ralph/`), `description`
- `userStories[]`: `id`, `title`, `description`, `acceptanceCriteria`, `priority`, `passes: false`, `notes`
- Story-sizing rules (must fit one context window)
- Dependency ordering (schema before backend before UI)
- Every story includes "Typecheck passes" and "Lint passes" criteria

### State Model

- Each iteration is stateless from claude's perspective -- no conversation history
- State communicated via files on disk (`prd.json` tracking story completion, `progress.md` accumulating learnings)
- Branch archiving isolates separate feature runs

## Gaps

- No retry on failed claude invocations (`|| true` suppresses errors)
- No explicit resume-from-iteration-N capability
- No model selection, MCP config, or additional flag passthrough
