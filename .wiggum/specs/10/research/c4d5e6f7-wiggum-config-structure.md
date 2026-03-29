# Research: .wiggum/ Configuration and Directory Structure

## Question

What configuration and directory structure does `.wiggum/` use? What specs, config files, and conventions exist?

## Findings

### .wiggum/ Purpose

- CLAUDE.md documents it as "runtime artifacts (specs, research)" -- not a configuration directory
- Only committed file: `.wiggum/.gitignore` with content `worktrees/`

### Directory Layout

```
.wiggum/
  .gitignore              # excludes worktrees/
  worktrees/<ticket-id>/  # per-ticket isolated git worktrees (gitignored)
  specs/<ticket-id>/      # per-ticket research and PRD output
    research/             # per-source research files
      <hash>-<name>.md   # individual research (hash = first 8 of SHA-256)
      RESEARCH.md         # synthesized executive summary
    <feature-name>.md     # the final PRD document
```

### Worktrees

- Created by `session-launch.sh` at `.wiggum/worktrees/<ticket-id>/`
- Uses branch `doc/prd-<ticket-id>`
- Symlinks `.claude/settings.local.json` from repo root
- Pre-accepts Claude Code trust dialog by patching `~/.claude.json`

### Specs as Pipeline Junction

- `.wiggum/specs/` is the handoff point between PRD-generation (propose-feature / create-feature-prd) and implementation loop (ralph.sh)
- ralph.sh reads PRD markdown from `.wiggum/specs/<issue-id>/*.md` (excluding `research/`)
- If specs dir does not exist, ralph exits with error

### No Config Files

- No `config.toml`, `config.json`, or any config file in `.wiggum/`
- Follows single-source-of-truth rule -- config lives in `plugins/wiggum/` and `.claude/`
- The ticket mentions `.wiggum/config.toml` as a design goal -- does not exist yet

## Gaps

- No formal schema or README documenting the specs structure
- Hash prefix naming convention enforced only by skill definition, not tooling
- `.wiggum/config.toml` referenced in ticket but not yet created
