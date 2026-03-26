#!/usr/bin/env bash
# ralph-minimal.sh -- Minimal ralph loop bootstrap for wiggum Phase 1.
# Processes a plan.md checklist via TDD: outer loop recalibrates the plan,
# inner loop picks priority items and runs RED/GREEN/test cycles.
#
# Usage: scripts/ralph-minimal.sh <plan.md>
#
# Environment:
#   BATCH_SIZE  -- items per inner loop cycle (default: 3)
#   CYCLE_LIMIT -- max outer loop cycles, 0 = unlimited (default: 0)

set -o pipefail

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

PLAN_FILE="${1:?Usage: $0 <plan.md>}"
PLAN_FILE="$(cd "$(dirname "$PLAN_FILE")" && pwd)/$(basename "$PLAN_FILE")"
BATCH_SIZE="${BATCH_SIZE:-3}"
CYCLE_LIMIT="${CYCLE_LIMIT:-0}"
MAX_TURNS="${MAX_TURNS:-50}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-600}"
PROJECT_DIR="$(git rev-parse --show-toplevel)"
WORK_DIR="$(mktemp -d /tmp/wiggum-ralph-XXXXXX)"
LOG_FILE="${WORK_DIR}/ralph.log"
PREAMBLE_FILE="${WORK_DIR}/preamble.md"

cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

log() { printf '[ralph] %s\n' "$*" | tee -a "$LOG_FILE"; }

# --------------------------------------------------------------------------- #
# Checklist utilities
# All plan.md mutations happen through these functions, never by the model.
# --------------------------------------------------------------------------- #

get_unchecked() {
    grep '^- \[ \] ' "$PLAN_FILE" | sed 's/^- \[ \] //' || true
}

count_unchecked() {
    local n
    n="$(grep -c '^- \[ \] ' "$PLAN_FILE" 2>/dev/null)" || true
    echo "${n:-0}"
}

mark_checked() {
    local item="$1"
    # Escape sed special characters in item text.
    local escaped
    escaped="$(printf '%s\n' "$item" | sed 's/[[\/.^$*+?()|{}]/\\&/g')"
    # Replace first occurrence only.
    sed -i '' "0,/^- \[ \] ${escaped}$/s//- [x] ${escaped}/" "$PLAN_FILE"
}

append_todo() {
    local item="$1"
    printf '\n- [ ] %s\n' "$item" >> "$PLAN_FILE"
}

remove_checked() {
    sed -i '' '/^- \[x\] /d' "$PLAN_FILE"
}

# --------------------------------------------------------------------------- #
# Prompt preamble -- written to file, injected via --append-system-prompt-file
# --------------------------------------------------------------------------- #

cat > "$PREAMBLE_FILE" << 'PREAMBLE_EOF'
## Ralph Loop Principles

1. This invocation does exactly ONE thing. Not one feature -- one thing.
2. Never expand scope. If you find a gap or issue, output a line starting with NEW_TODO: and move on. Do not attempt to address it.
3. Fresh context. You have no memory of prior invocations.
4. Minimal changes. Write the minimum code for the task at hand.
5. Follow project conventions: Python 3.14+, src layout (src/wiggum/), ruff linting (line-length 88), pyright strict, pytest, uv.
6. Use `uv run` for all tool invocations (ruff, pytest, pyright).
7. Do not add docstrings, comments, or type annotations beyond what is needed for the change.
8. ASCII only in code and comments.
PREAMBLE_EOF

# --------------------------------------------------------------------------- #
# Agent invocation helpers
# --------------------------------------------------------------------------- #

# Common flags for all claude -p calls.
CLAUDE_BASE_FLAGS=(
    --output-format text
    --max-turns "$MAX_TURNS"
    --append-system-prompt-file "$PREAMBLE_FILE"
    --dangerously-skip-permissions
)

# Run claude -p synchronously, capture stdout. Stderr goes to log.
# Optional third arg: comma-separated tool list (restricts available tools).
claude_run() {
    local prompt="$1"
    local label="${2:-agent}"
    local tools="${3:-}"
    log "Invoking: $label"
    local flags=("${CLAUDE_BASE_FLAGS[@]}")
    if [ -n "$tools" ]; then
        flags+=(--tools "$tools")
    fi
    timeout "$AGENT_TIMEOUT" claude -p "$prompt" "${flags[@]}" 2>>"$LOG_FILE" || {
        local rc=$?
        if [ "$rc" -eq 124 ]; then
            log "TIMEOUT after ${AGENT_TIMEOUT}s: $label"
        fi
        return "$rc"
    }
}

# Run claude -p in background, stdout to file. Returns immediately.
# Optional fourth arg: comma-separated tool list.
claude_bg() {
    local prompt="$1"
    local out_file="$2"
    local label="${3:-agent}"
    local tools="${4:-}"
    log "Background: $label"
    local flags=("${CLAUDE_BASE_FLAGS[@]}")
    if [ -n "$tools" ]; then
        flags+=(--tools "$tools")
    fi
    timeout "$AGENT_TIMEOUT" claude -p "$prompt" "${flags[@]}" > "$out_file" 2>>"$LOG_FILE" &
}

# Scan output files for NEW_TODO lines and append them to the plan.
harvest_todos() {
    local glob_pattern="$1"
    local f
    for f in $glob_pattern; do
        [ -f "$f" ] || continue
        grep '^NEW_TODO: ' "$f" 2>/dev/null | sed 's/^NEW_TODO: //' | while IFS= read -r todo; do
            log "Discovered TODO: $todo"
            append_todo "$todo"
        done
    done
}

# --------------------------------------------------------------------------- #
# Direct test/lint execution -- no AI overhead, real backpressure
# --------------------------------------------------------------------------- #

run_checks() {
    local tag="$1"
    log "Running checks ($tag)..."

    local lint_out="${WORK_DIR}/lint_${tag}.out"
    local test_out="${WORK_DIR}/test_${tag}.out"
    local lint_rc=0 test_rc=0

    (cd "$PROJECT_DIR" && uv run ruff check src/ tests/) > "$lint_out" 2>&1 || lint_rc=$?
    (cd "$PROJECT_DIR" && uv run pytest) > "$test_out" 2>&1 || test_rc=$?

    log "Lint rc=$lint_rc | Pytest rc=$test_rc ($tag)"

    # pytest exit 5 = no tests collected -- treat as passing for early bootstrap
    if [ "$lint_rc" -eq 0 ] && { [ "$test_rc" -eq 0 ] || [ "$test_rc" -eq 5 ]; }; then
        return 0
    fi
    return 1
}

# --------------------------------------------------------------------------- #
# Outer loop: plan recalibration
# --------------------------------------------------------------------------- #

outer_loop() {
    log "=== OUTER LOOP: recalibrating plan ==="

    local plan_content
    plan_content="$(cat "$PLAN_FILE")"

    local recalibrated
    recalibrated="$(claude_run "$(cat <<EOF
## Task: Recalibrate Implementation Plan

Working directory: $PROJECT_DIR
Plan file: $PLAN_FILE

### Current plan contents

$plan_content

### Instructions

1. Read the codebase to see what is already implemented.
2. Items marked [x]: verify truly done in the code. If NOT done, uncheck them.
3. Unchecked items: verify still relevant and correctly scoped.
4. Identify MISSING items that the plan should include.
5. Re-sort all unchecked items by priority (most important / foundational first).
6. Output the COMPLETE updated plan.md content. Nothing else.

No commentary, no code fences, no preamble. Raw markdown only.
EOF
    )" "recalibrate")"

    if echo "$recalibrated" | grep -q '^- \[[ x]\] '; then
        echo "$recalibrated" > "$PLAN_FILE"
        remove_checked
        log "Plan recalibrated. $(count_unchecked) items remain."
    else
        log "WARNING: recalibration output invalid, keeping current plan."
    fi
}

# --------------------------------------------------------------------------- #
# Priority selection -- model picks top N items from prompt
# --------------------------------------------------------------------------- #

select_items() {
    local items
    items="$(get_unchecked)"
    local n
    n="$(echo "$items" | grep -c . 2>/dev/null)" || true
    n="${n:-0}"

    if [ "$n" -eq 0 ]; then return 1; fi

    # If fewer items than batch size, use all.
    if [ "$n" -le "$BATCH_SIZE" ]; then
        echo "$items"
        return 0
    fi

    claude_run "$(cat <<EOF
Select the $BATCH_SIZE most important items to implement next from the list below.
Consider dependencies: foundational/infrastructure items before features that depend on them.

Items:
$items

Output ONLY the selected items, one per line, exactly as listed above.
No numbering, no bullets, no commentary.
EOF
    )" "select priorities"
}

# --------------------------------------------------------------------------- #
# RED phase: write failing tests (parallel)
# --------------------------------------------------------------------------- #

red_phase() {
    log "--- RED PHASE: writing failing tests ---"

    # Tools restricted: no Bash = cannot run tests.
    local red_tools="Read,Write,Edit,Glob,Grep"

    local pids=()
    local i=0
    for item in "$@"; do
        claude_bg "$(cat <<EOF
## Task: Write Failing Tests (RED)

Working directory: $PROJECT_DIR

### Item to test

$item

### Instructions

1. Read relevant source code to understand current state.
2. Write pytest test(s) that FAIL because the described behavior does not exist yet.
3. Place tests under tests/ mirroring the src/wiggum/ structure.
4. Do NOT implement the feature. Only write tests.
5. If you find gaps, output: NEW_TODO: <description>
EOF
        )" "${WORK_DIR}/red_${i}.out" "RED[${item:0:50}]" "$red_tools"
        pids+=($!)
        ((i++))
    done

    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
    harvest_todos "${WORK_DIR}/red_*.out"
    log "RED phase complete."
}

# --------------------------------------------------------------------------- #
# GREEN phase: implement fixes (sequential to avoid file conflicts)
# --------------------------------------------------------------------------- #

green_phase() {
    log "--- GREEN PHASE: implementing fixes ---"

    # Tools restricted: no Bash = cannot run tests.
    local green_tools="Read,Write,Edit,Glob,Grep"

    local test_output
    test_output="$(tail -200 "${WORK_DIR}/test_red.out" 2>/dev/null || echo '(no test output)')"

    local i=0
    for item in "$@"; do
        claude_run "$(cat <<EOF
## Task: Implement Minimal Fix (GREEN)

Working directory: $PROJECT_DIR

### Item to implement

$item

### Recent test output (for context)

$test_output

### Instructions

1. Read the failing tests for this item.
2. Write the MINIMUM code to make those tests pass.
3. Do NOT write new tests.
4. Do NOT refactor unrelated code.
5. If you find gaps, output: NEW_TODO: <description>
EOF
        )" "GREEN[${item:0:50}]" "$green_tools" > "${WORK_DIR}/green_${i}.out"
        harvest_todos "${WORK_DIR}/green_${i}.out"
        ((i++))
    done

    log "GREEN phase complete."
}

# --------------------------------------------------------------------------- #
# Commit -- direct git, no AI overhead
# --------------------------------------------------------------------------- #

do_commit() {
    log "Committing changes..."
    cd "$PROJECT_DIR" || return 1

    git add -A

    # Build a commit message from the completed items.
    local body=""
    for item in "$@"; do
        body="${body}- ${item}"$'\n'
    done

    local subject
    subject="feat: implement $(echo "$1" | tr '[:upper:]' '[:lower:]' | cut -c1-60)"

    if ! git commit -m "$(cat <<EOF
$subject

$body
EOF
    )"; then
        log "Pre-commit hook failed, running auto-fix..."
        uv run ruff check --fix src/ tests/ 2>/dev/null || true
        uv run ruff format src/ tests/ 2>/dev/null || true
        git add -A
        git commit -m "$(cat <<EOF
$subject

$body
EOF
        )" || {
            log "Commit failed after auto-fix. Continuing anyway."
            return 0
        }
    fi

    log "Committed."
}

# --------------------------------------------------------------------------- #
# Inner loop: one batch of TDD cycles
# --------------------------------------------------------------------------- #

inner_loop() {
    log "=== INNER LOOP: processing batch ==="

    # Priority selection.
    local selection
    selection="$(select_items)" || { log "No items to process."; return 1; }

    local items=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && items+=("$line")
    done <<< "$selection"

    if [ "${#items[@]}" -eq 0 ]; then
        log "No items selected."
        return 1
    fi

    log "Selected ${#items[@]} items:"
    for item in "${items[@]}"; do log "  -> $item"; done

    # RED: write failing tests (parallel).
    red_phase "${items[@]}"

    # Test gate after RED: expect failures (new tests should fail).
    if run_checks "red"; then
        log "WARNING: all checks pass after RED -- tests may not assert new behavior."
    else
        log "Checks failing as expected after RED."
    fi

    # GREEN: implement fixes (sequential to avoid codebase conflicts).
    green_phase "${items[@]}"

    # Auto-fix lint before testing.
    (cd "$PROJECT_DIR" && uv run ruff check --fix src/ tests/ 2>/dev/null || true)
    (cd "$PROJECT_DIR" && uv run ruff format src/ tests/ 2>/dev/null || true)

    # Test gate after GREEN: expect all pass.
    if run_checks "green"; then
        log "All checks pass after GREEN."
        for item in "${items[@]}"; do mark_checked "$item"; done
        do_commit "${items[@]}"
    else
        log "Checks still failing after GREEN."
        # Attempt a single remediation pass.
        local test_failures
        test_failures="$(tail -100 "${WORK_DIR}/test_green.out" 2>/dev/null || echo '(no output)')"
        local lint_failures
        lint_failures="$(tail -50 "${WORK_DIR}/lint_green.out" 2>/dev/null || echo '(no output)')"

        claude_run "$(cat <<EOF
## Task: Fix Remaining Failures

Working directory: $PROJECT_DIR

### Test failures

$test_failures

### Lint failures

$lint_failures

### Instructions

1. Read the failing test output and lint errors.
2. Fix ALL failures. Make all tests pass and lint clean.
3. If a fix requires broader changes, output: NEW_TODO: <description>
EOF
        )" "REMEDIATE" "Read,Write,Edit,Glob,Grep" > "${WORK_DIR}/remediate.out"
        harvest_todos "${WORK_DIR}/remediate.out"

        # Auto-fix lint again.
        (cd "$PROJECT_DIR" && uv run ruff check --fix src/ tests/ 2>/dev/null || true)
        (cd "$PROJECT_DIR" && uv run ruff format src/ tests/ 2>/dev/null || true)

        if run_checks "remediate"; then
            log "Remediation succeeded."
            for item in "${items[@]}"; do mark_checked "$item"; done
            do_commit "${items[@]}"
        else
            log "Remediation failed. Appending fix TODO."
            append_todo "FIX: checks still failing -- see ${WORK_DIR}/test_remediate.out"
            # Commit partial progress.
            do_commit "${items[@]}"
        fi
    fi
}

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

log "Ralph Loop Bootstrap"
log "Plan:  $PLAN_FILE"
log "Project: $PROJECT_DIR"
log "Batch: $BATCH_SIZE"
log "Work:  $WORK_DIR"
log ""

if [ ! -f "$PLAN_FILE" ]; then
    log "FATAL: plan file not found: $PLAN_FILE"
    exit 1
fi

cycle=0
while true; do
    ((cycle++))
    log "======== CYCLE $cycle ========"

    outer_loop

    remaining="$(count_unchecked)"
    if [ "$remaining" -eq 0 ]; then
        log ""
        log "ALL ITEMS COMPLETE."
        break
    fi
    log "$remaining items remaining."

    inner_loop || true

    if [ "$CYCLE_LIMIT" -gt 0 ] && [ "$cycle" -ge "$CYCLE_LIMIT" ]; then
        log "Cycle limit reached ($CYCLE_LIMIT). Stopping."
        break
    fi
done

log "Final plan state:"
cat "$PLAN_FILE" | tee -a "$LOG_FILE"
