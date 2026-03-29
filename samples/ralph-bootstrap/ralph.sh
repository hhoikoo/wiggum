#!/usr/bin/env bash
set -euo pipefail

# Ralph Wiggum - Long-running AI agent loop
# Dependencies: claude, jq
# Usage: ./ralph.sh <issue-id> [max_iterations]
# Stdout: JSON summary on completion
# Stderr: progress diagnostics

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ISSUE_ID="${1:?Usage: ralph.sh <issue-id> [max_iterations]}"
MAX_ITERATIONS="${2:-50}"

PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.md"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"
AGENT_PROMPT="$SCRIPT_DIR/agent-prompt.md"
CONVERT_PROMPT="$SCRIPT_DIR/convert-prd-prompt.md"

# --- PRD conversion ---

if [ ! -f "$PRD_FILE" ]; then
  # Find the PRD file in .wiggum/specs/<issue-id>/
  specs_dir="${REPO_ROOT}/.wiggum/specs/${ISSUE_ID}"
  if [ ! -d "$specs_dir" ]; then
    echo "No specs directory found at ${specs_dir}" >&2
    echo "Run /wiggum:feature-propose first to generate a PRD." >&2
    exit 1
  fi

  # Find the PRD markdown (skip RESEARCH.md which is an artifact, not the PRD)
  prd_file=""
  for f in "$specs_dir"/*.md; do
    if [ -f "$f" ] && [ "$(basename "$f")" != "RESEARCH.md" ]; then
      prd_file="$f"
      break
    fi
  done

  if [ -z "$prd_file" ]; then
    echo "No PRD markdown found in ${specs_dir}" >&2
    exit 1
  fi

  echo "Converting PRD to prd.json: ${prd_file}" >&2
  prd_content="$(cat "$prd_file")"
  convert_instructions="$(cat "$CONVERT_PROMPT")"

  claude -p "${convert_instructions}

---

Here is the PRD to convert:

${prd_content}

---

Write the resulting prd.json to: ${PRD_FILE}
The project name is: wiggum
" --dangerously-skip-permissions >&2

  if [ ! -f "$PRD_FILE" ]; then
    echo "PRD conversion failed -- prd.json was not created" >&2
    exit 2
  fi

  echo "PRD converted successfully" >&2
fi

# --- Archive previous run if branch changed ---

if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  current_branch="$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")"
  last_branch="$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")"

  if [ -n "$current_branch" ] && [ -n "$last_branch" ] && [ "$current_branch" != "$last_branch" ]; then
    archive_date="$(date +%Y-%m-%d)"
    folder_name="${last_branch#ralph/}"
    archive_folder="${ARCHIVE_DIR}/${archive_date}-${folder_name}"

    echo "Archiving previous run: ${last_branch}" >&2
    mkdir -p "$archive_folder"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$archive_folder/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$archive_folder/"
    echo "Archived to: ${archive_folder}" >&2

    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

# --- Track current branch ---

if [ -f "$PRD_FILE" ]; then
  current_branch="$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")"
  if [ -n "$current_branch" ]; then
    echo "$current_branch" > "$LAST_BRANCH_FILE"
  fi
fi

# --- Initialize progress file ---

if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

# --- Main loop ---

echo "Starting Ralph - Issue: ${ISSUE_ID} - Max iterations: ${MAX_ITERATIONS}" >&2

for i in $(seq 1 "$MAX_ITERATIONS"); do
  echo "" >&2
  echo "===============================================================" >&2
  echo "  Ralph Iteration ${i} of ${MAX_ITERATIONS}" >&2
  echo "===============================================================" >&2

  output="$(claude --dangerously-skip-permissions --print < "$AGENT_PROMPT" 2>&1 | tee /dev/stderr)" || true

  if echo "$output" | grep -q "<promise>COMPLETE</promise>"; then
    echo "" >&2
    echo "Ralph completed all tasks!" >&2
    echo "Completed at iteration ${i} of ${MAX_ITERATIONS}" >&2
    printf '{"status":"complete","iteration":%d,"max_iterations":%d,"issue_id":"%s"}\n' "$i" "$MAX_ITERATIONS" "$ISSUE_ID"
    exit 0
  fi

  echo "Iteration ${i} complete. Continuing..." >&2
  sleep 2
done

echo "" >&2
echo "Ralph reached max iterations (${MAX_ITERATIONS}) without completing all tasks." >&2
echo "Check ${PROGRESS_FILE} for status." >&2
printf '{"status":"max_iterations","iteration":%d,"max_iterations":%d,"issue_id":"%s"}\n' "$MAX_ITERATIONS" "$MAX_ITERATIONS" "$ISSUE_ID"
exit 1
