---
paths:
  - "plugins/*/skills/*/**"
---
# Plugin Skill Conventions

Rules for SKILL.md files inside plugin skill directories.

## Script Path Resolution

Use `${CLAUDE_SKILL_DIR}` to reference scripts in the skill's `scripts/` subdirectory. Do not use `${CLAUDE_PLUGIN_ROOT}` -- it has multiple open bugs (anthropics/claude-code#38699, #9354) where it resolves inconsistently between marketplace and local installs.

`${CLAUDE_SKILL_DIR}` was added in v2.1.69 and works reliably in skill body content. It resolves to the absolute path of the directory containing the SKILL.md file.

```
bash ${CLAUDE_SKILL_DIR}/scripts/session-launch.sh --ticket-id 42
```

## Skill Directory Structure

Each skill follows the Agent Skills standard layout with a `scripts/` subdirectory:

```
skills/feature-propose/
├── SKILL.md
├── reference.md                                                  # optional supporting files
└── scripts/
    ├── session-launch.sh -> ../../../scripts/session-launch.sh   # shared (symlink)
    ├── fetch-issue.sh -> ../../../scripts/fetch-issue.sh         # shared (symlink)
    └── validate-input.sh                                          # skill-specific
```

Shared scripts live in `plugins/<plugin>/scripts/`. Each skill symlinks the individual shared scripts it needs into its own `scripts/` subdirectory. Skill-specific scripts live directly in the same `scripts/` subdirectory alongside the symlinks.

Git preserves symlinks, so this works in both local dev (`--plugin-dir`) and marketplace installs on macOS/Linux. When installed via marketplace, Claude Code dereferences symlinks during the cache copy -- the cached skill directory contains real files, not symlinks.

## Known Bugs

- `${CLAUDE_SKILL_DIR}` is **not** substituted in SKILL.md frontmatter fields like `hooks:` or `allowed-tools:` (anthropics/claude-code#36135, #31494). Only use it in the skill body.
- Symlinked skill *directories* (the directory itself being a symlink) break skill discovery (anthropics/claude-code#14836). Symlinked *files inside* a skill directory work fine -- the OS resolves them transparently when bash runs.
- `${CLAUDE_PLUGIN_ROOT}` is unreliable: wrong path in skill body (anthropics/claude-code#9354), inconsistent between hooks and agent environment (anthropics/claude-code#38699), stale after cache hash changes (anthropics/claude-code#39328).

## Frontmatter

Omit `allowed-tools` from plugin skill frontmatter. Spawned tmux sessions run with `--dangerously-skip-permissions` since each session gets its own isolated git worktree. The parent session (where the user invokes the skill) already has permission rules configured in `.claude/settings.json` and `.claude/settings.local.json`.
