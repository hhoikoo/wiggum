#!/usr/bin/env bash
set -euo pipefail

# Remove a git worktree and prune stale references idempotently.
# Dependencies: git
# Usage: worktree-remove.sh --worktree-path <PATH> --repo-path <PATH>
# Exit codes: 0 = success (or already removed), 1 = bad input, 2 = unexpected failure

worktree_path=""
repo_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worktree-path)
      worktree_path="${2:?--worktree-path requires a value}"
      shift 2
      ;;
    --repo-path)
      repo_path="${2:?--repo-path requires a value}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$worktree_path" ] || [ -z "$repo_path" ]; then
  echo "worktree-remove.sh: --worktree-path and --repo-path are required" >&2
  exit 1
fi

if [ ! -d "$repo_path" ]; then
  echo "worktree-remove.sh: repo path does not exist: ${repo_path}" >&2
  exit 1
fi

if [ -d "$worktree_path" ]; then
  echo "Removing worktree at ${worktree_path}" >&2
  git -C "$repo_path" worktree remove --force "$worktree_path" 2>&1 >&2 || {
    echo "worktree-remove.sh: git worktree remove failed, attempting manual cleanup" >&2
    rm -rf "$worktree_path"
  }
else
  echo "Worktree already removed: ${worktree_path}" >&2
fi

git -C "$repo_path" worktree prune 2>&1 >&2
echo "Worktree pruned" >&2
