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
BATCH_SIZE="${BATCH_SIZE:-10}"
CYCLE_LIMIT="${CYCLE_LIMIT:-0}"
MAX_TURNS="${MAX_TURNS:-50}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-600}"
PROJECT_DIR="$(git rev-parse --show-toplevel)"
WORK_DIR="$(mktemp -d /tmp/wiggum-ralph-XXXXXX)"
LOG_FILE="${WORK_DIR}/ralph.log"
PREAMBLE_FILE="${WORK_DIR}/preamble.md"

cleanup() { rm -rf "$WORK_DIR"; }

CHILD_PIDS=()

# Kill all child processes (including running claude -p sessions) on interrupt.
# Preserves work dir for debugging -- only normal exit cleans up.
abort() {
    printf '\n[ralph] INTERRUPTED -- killing child processes...\n' >&2
    for pid in "${CHILD_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    printf '[ralph] Work dir preserved: %s\n' "$WORK_DIR" >&2
    trap - EXIT
    exit 130
}
trap abort INT TERM
trap cleanup EXIT

RALPH_START="$(date +%s)"

log() {
    local now elapsed
    now="$(date '+%H:%M:%S')"
    elapsed=$(( $(date +%s) - RALPH_START ))
    printf '[ralph %s +%dm%02ds] %s\n' "$now" $((elapsed / 60)) $((elapsed % 60)) "$*" | tee -a "$LOG_FILE"
}

# Phase timer -- call phase_start before a phase, phase_end after.
_PHASE_START=0
phase_start() {
    _PHASE_START="$(date +%s)"
    log "$1"
}
phase_end() {
    local dur=$(( $(date +%s) - _PHASE_START ))
    log "$1 (${dur}s)"
}

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
    # Use fixed-string grep to find the line number, then sed by line number.
    # Avoids regex escaping issues with long items containing special chars.
    local line_num
    line_num="$(grep -nF -- "- [ ] $item" "$PLAN_FILE" | head -1 | cut -d: -f1)" || true
    if [ -n "$line_num" ]; then
        sed -i '' "${line_num}s/^- \[ \] /- [x] /" "$PLAN_FILE"
    else
        log "WARNING: mark_checked failed to find item: ${item:0:60}" >&2
    fi
}

append_todo() {
    local item="$1"
    # Ensure the Additional Findings section exists, then append to end of file.
    # Items always land at the bottom; the outer loop reorganizes them later.
    if ! grep -q '^### Additional Findings' "$PLAN_FILE"; then
        printf '\n### Additional Findings\n' >> "$PLAN_FILE"
    fi
    printf '%s\n' "- [ ] $item" >> "$PLAN_FILE"
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
5. Follow project conventions: Python 3.14+, src layout (src/wiggum/), pyright strict, pytest, uv.
6. Use `uv run` for all tool invocations (ruff, pytest, pyright).
7. All public classes, methods, and functions must have a one-line docstring.
8. Imports used only in type annotations must be inside `if TYPE_CHECKING:` blocks.
9. Use modern Python syntax: PEP 695 type parameters, not TypeVar.
10. ASCII only in code and comments.
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
    log "Invoking: $label" >&2
    local flags=("${CLAUDE_BASE_FLAGS[@]}")
    if [ -n "$tools" ]; then
        flags+=(--tools "$tools")
    fi
    local out_tmp="${WORK_DIR}/run_${RANDOM}.out"
    timeout "$AGENT_TIMEOUT" claude -p "$prompt" "${flags[@]}" > "$out_tmp" 2>>"$LOG_FILE" &
    local pid=$!
    CHILD_PIDS+=("$pid")
    wait "$pid" || {
        local rc=$?
        if [ "$rc" -eq 124 ]; then
            log "TIMEOUT after ${AGENT_TIMEOUT}s: $label" >&2
        fi
        rm -f "$out_tmp"
        return "$rc"
    }
    cat "$out_tmp"
    rm -f "$out_tmp"
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
    CHILD_PIDS+=($!)
}

# Scan output files for NEW_TODO lines and append them to the plan.
harvest_todos() {
    local glob_pattern="$1"
    local f
    for f in $glob_pattern; do
        [ -f "$f" ] || continue
        grep '^NEW_TODO: ' "$f" 2>/dev/null | sed 's/^NEW_TODO: //' | while IFS= read -r todo; do
            # Skip if this TODO (or something very similar) already exists in the plan.
            if grep -qF -- "${todo:0:60}" "$PLAN_FILE" 2>/dev/null; then
                log "Skipping duplicate TODO: ${todo:0:60}..."
                continue
            fi
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
    phase_start "Running checks ($tag)..."

    # Refresh editable install so newly created modules are importable.
    (cd "$PROJECT_DIR" && uv sync --quiet) 2>/dev/null || true

    local lint_out="${WORK_DIR}/lint_${tag}.out"
    local test_out="${WORK_DIR}/test_${tag}.out"
    local lint_rc=0 test_rc=0

    (cd "$PROJECT_DIR" && uv run ruff check src/ tests/) > "$lint_out" 2>&1 || lint_rc=$?
    (cd "$PROJECT_DIR" && uv run pytest) > "$test_out" 2>&1 || test_rc=$?

    phase_end "Lint rc=$lint_rc | Pytest rc=$test_rc ($tag)"

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
    log "=== OUTER LOOP ==="

    local plan_content
    plan_content="$(cat "$PLAN_FILE")"
    local has_checked=false
    local verify_out="${WORK_DIR}/verify_checked.out"
    local gaps_out="${WORK_DIR}/find_gaps.out"

    local checked
    checked="$(grep '^- \[x\] ' "$PLAN_FILE" | sed 's/^- \[x\] //' || true)"
    local unchecked_items
    unchecked_items="$(get_unchecked)"

    # Skip gap scan on cycle 1 -- plan is hand-written and there's no code
    # to compare against yet. Inner loop NEW_TODO discovery handles gaps.
    local run_gaps=false
    if [ "$cycle" -gt 1 ]; then
        run_gaps=true
    fi

    # Launch agents in parallel where applicable.
    if [ -n "$checked" ]; then
        has_checked=true
        if [ "$run_gaps" = true ]; then
            phase_start "OUTER: verifying checked items + scanning for gaps (parallel)..."
        else
            phase_start "OUTER: verifying checked items..."
        fi
        claude_bg "$(cat <<EOF
## Task: Verify Completed Items

Working directory: $PROJECT_DIR

### Checked items to verify

$checked

### Instructions

For each item above, check the codebase to confirm it is actually implemented. If an item is NOT implemented (missing code, stub only, or partially done), output it on its own line. Output NOTHING else -- no commentary, no preamble. If all items are truly done, output the single word NONE.
EOF
        )" "$verify_out" "verify-checked"
        local verify_pid=$!
    else
        log "OUTER: no checked items to verify."
        if [ "$run_gaps" = true ]; then
            phase_start "OUTER: scanning for gaps..."
        fi
    fi

    local gaps_pid=""
    if [ "$run_gaps" = true ]; then
        # List recently changed files so the agent can focus its search
        # instead of reading the entire codebase.
        local recent_files
        recent_files="$(cd "$PROJECT_DIR" && git diff --name-only HEAD~3 HEAD -- src/ 2>/dev/null || echo '(none)')"

        claude_bg "$(cat <<EOF
## Task: Find Missing Plan Items

Working directory: $PROJECT_DIR

### Current plan (unchecked items only)

$unchecked_items

### Recently changed source files

$recent_files

### Instructions

Check the recently changed files above. Identify ONLY items that are required to make the existing plan items work but are missing from the plan. For example: a missing __init__.py that blocks imports, a missing dependency in pyproject.toml, or a function that existing plan items depend on but nobody creates.

Do NOT add:
- Edge cases, error handling, or hardening
- Nice-to-haves or improvements to existing code
- Items that duplicate or overlap with existing plan items
- Items that the inner loop agents can discover on their own via NEW_TODO

Do NOT do a full codebase scan. Focus only on the recently changed files.

Output at most 3 items. Output each as: - [ ] <description>
Output NOTHING else -- no commentary, no preamble, no code fences. If nothing is blocking, output the single word NONE.
EOF
        )" "$gaps_out" "find-gaps"
        gaps_pid=$!
    else
        log "OUTER: skipping gap scan (cycle 1)."
    fi

    # Wait for agents.
    if [ "$has_checked" = true ]; then
        wait "$verify_pid" 2>/dev/null || true
        log "OUTER: verify-checked done."
    fi
    if [ -n "$gaps_pid" ]; then
        wait "$gaps_pid" 2>/dev/null || true
        log "OUTER: find-gaps done."
    fi

    # Process verify results.
    if [ "$has_checked" = true ] && [ -f "$verify_out" ]; then
        local unchecks
        unchecks="$(sed '/^```/d; /^[[:space:]]*$/d' "$verify_out")"
        if [ -n "$unchecks" ] && ! echo "$unchecks" | grep -qi '^NONE$'; then
            echo "$unchecks" | while IFS= read -r item; do
                [ -z "$item" ] && continue
                local escaped
                escaped="$(printf '%s\n' "$item" | sed 's/[[\/.^$*+?()|{}]/\\&/g')"
                sed -i '' "s/^- \[x\] ${escaped}$/- [ ] ${escaped}/" "$PLAN_FILE"
            done
            log "OUTER: unchecked items not yet implemented."
        else
            log "OUTER: all checked items verified."
        fi
    fi

    # Process gap results.
    if [ -f "$gaps_out" ]; then
        local gaps
        gaps="$(sed '/^```/d; /^[[:space:]]*$/d' "$gaps_out")"
        if [ -n "$gaps" ] && ! echo "$gaps" | grep -qi '^NONE$'; then
            echo "$gaps" | grep '^- \[ \] ' | sed 's/^- \[ \] //' | while IFS= read -r item; do
                [ -z "$item" ] && continue
                append_todo "$item"
            done
            log "OUTER: added new items to plan."
        else
            log "OUTER: no gaps found."
        fi
    fi

    # Step 3: Reorganize Additional Findings into proper headings.
    if grep -q '^### Additional Findings' "$PLAN_FILE"; then
        local findings
        findings="$(sed -n '/^### Additional Findings$/,$ { /^### Additional Findings$/d; /^[[:space:]]*$/d; p; }' "$PLAN_FILE")"
        if [ -n "$findings" ]; then
            phase_start "OUTER: reorganizing additional findings..."
            local reorg_out="${WORK_DIR}/reorganize.out"
            plan_content="$(cat "$PLAN_FILE")"
            claude_run "$(cat <<EOF
## Task: Reorganize Plan Items

### Current plan

$plan_content

### Instructions

The plan has a section called "### Additional Findings" at the bottom with items that were discovered during implementation. Move each item to the most appropriate existing section heading. If no existing heading fits, create a new ### heading for it. If still unclear, place it under ### Miscellaneous.

Remove the ### Additional Findings section entirely after relocating all items.

Output the COMPLETE updated plan. No commentary, no code fences, no preamble.
EOF
            )" "reorganize" > "$reorg_out"

            local reorg
            reorg="$(sed '/^```/d; /^[[:space:]]*$/{ 1d; }' "$reorg_out")"
            if echo "$reorg" | grep -q '^- \[[ x]\] '; then
                echo "$reorg" > "$PLAN_FILE"
                phase_end "Reorganized findings into plan sections."
            else
                phase_end "WARNING: reorganization output invalid, keeping current plan."
            fi
        fi
    fi

    log "$(count_unchecked) items remaining after outer loop."
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

    local raw
    raw="$(claude_run "$(cat <<EOF
Select the $BATCH_SIZE most important items to implement next from the list below.
Consider dependencies: foundational/infrastructure items before features that depend on them.

Items:
$items

Output ONLY the selected items, one per line, exactly as listed above.
No numbering, no bullets, no commentary.
EOF
    )" "select priorities")"

    # Match model output to actual plan items. The model may truncate or
    # rephrase, so match if the output line is a substring of a plan item
    # or vice versa. Emit the canonical plan item, not the model's version.
    echo "$raw" | while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        # Try exact match first.
        if echo "$items" | grep -qFx -- "$line"; then
            echo "$line"
            continue
        fi
        # Fuzzy: find a plan item that contains the model's line or that
        # the model's line contains. Use first 60 chars as search key.
        local key="${line:0:60}"
        local match
        match="$(echo "$items" | grep -F -- "$key" | head -1)" || true
        if [ -n "$match" ]; then
            echo "$match"
        else
            log "  WARNING: no plan item matched: ${line:0:80}" >&2
        fi
    done
}

# --------------------------------------------------------------------------- #
# RED phase: write failing tests (parallel)
# --------------------------------------------------------------------------- #

red_phase() {
    phase_start "--- RED PHASE: writing failing tests ---"

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
5. Only output NEW_TODO: for missing dependencies YOUR item needs. Do NOT report issues in unrelated modules.
EOF
        )" "${WORK_DIR}/red_${i}.out" "RED[${item:0:50}]" "$red_tools"
        pids+=($!)
        ((i++))
    done

    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
    harvest_todos "${WORK_DIR}/red_*.out"
    phase_end "RED phase complete."
}

# --------------------------------------------------------------------------- #
# GREEN phase: implement fixes (sequential to avoid file conflicts)
# --------------------------------------------------------------------------- #

green_phase() {
    phase_start "--- GREEN PHASE: implementing fixes ---"

    local green_tools="Read,Write,Edit,Glob,Grep,Bash"

    local i=0
    for item in "$@"; do
        claude_run "$(cat <<EOF
## Task: Implement Minimal Fix (GREEN)

Working directory: $PROJECT_DIR

### Item to implement

$item

### Instructions

1. Read the failing tests for this item.
2. Write the MINIMUM code to make those tests pass.
3. Run \`uv run ruff check --fix --unsafe-fixes\` on files you changed and fix any remaining lint errors.
4. Run \`uv run pytest\` to verify your changes pass. If tests fail, fix your code and re-run until all tests pass. Ignore pre-existing failures unrelated to your item.
5. Do NOT write new tests.
6. Do NOT refactor unrelated code.
7. Only output NEW_TODO: for gaps directly caused by YOUR item. Do NOT report pre-existing test failures or issues in unrelated modules.
EOF
        )" "GREEN[${item:0:50}]" "$green_tools" > "${WORK_DIR}/green_${i}.out"
        harvest_todos "${WORK_DIR}/green_${i}.out"
        ((i++))
    done

    phase_end "GREEN phase complete."
}

# --------------------------------------------------------------------------- #
# Commit -- delegate to /commit skill via claude -p
# --------------------------------------------------------------------------- #

do_commit() {
    log "Committing via /commit skill..."
    (cd "$PROJECT_DIR" && git add -A)
    claude_run "/commit" "commit" >> "$LOG_FILE" || {
        log "Commit skill failed (rc=$?). Continuing."
        return 0
    }
    log "Committed."
}

# --------------------------------------------------------------------------- #
# Inner loop: one batch of TDD cycles
# --------------------------------------------------------------------------- #

inner_loop() {
    phase_start "=== INNER LOOP: processing batch ==="

    # Priority selection.
    local selection
    selection="$(select_items)" || { log "No items to process."; return 1; }

    local items=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && items+=("$line")
    done <<< "$selection"

    if [ "${#items[@]}" -eq 0 ]; then
        log "No items matched. Raw select output was:"
        echo "$selection" | head -10 | while IFS= read -r l; do log "  | $l"; done
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

    # Fix loop: auto-fix lint, run checks, remediate if failing, repeat.
    local max_fix_attempts=3
    local attempt=0
    local checks_passed=false

    while [ "$attempt" -lt "$max_fix_attempts" ]; do
        ((attempt++))

        (cd "$PROJECT_DIR" && uv run ruff check --fix --unsafe-fixes src/ tests/ 2>/dev/null || true)
        (cd "$PROJECT_DIR" && uv run ruff format src/ tests/ 2>/dev/null || true)

        if run_checks "fix_${attempt}"; then
            checks_passed=true
            break
        fi

        log "Checks failing (attempt $attempt/$max_fix_attempts). Remediating..."

        local test_failures
        test_failures="$(tail -100 "${WORK_DIR}/test_fix_${attempt}.out" 2>/dev/null || echo '(no output)')"
        local lint_failures
        lint_failures="$(tail -50 "${WORK_DIR}/lint_fix_${attempt}.out" 2>/dev/null || echo '(no output)')"

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
3. Run \`uv run ruff check --fix --unsafe-fixes\` on changed files.
4. Do NOT run pytest -- the harness runs tests.
5. If a fix requires broader changes, output: NEW_TODO: <description>
EOF
        )" "REMEDIATE[$attempt]" > "${WORK_DIR}/remediate_${attempt}.out"
        harvest_todos "${WORK_DIR}/remediate_${attempt}.out"
    done

    if [ "$checks_passed" = true ]; then
        log "All checks pass."
        for item in "${items[@]}"; do mark_checked "$item"; done
    else
        log "Checks still failing after $max_fix_attempts attempts."
        append_todo "FIX: checks still failing -- see ${WORK_DIR}/test_fix_${attempt}.out"
    fi

    # Commit progress regardless (partial or complete).
    do_commit "${items[@]}"
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
    cycle_start="$(date +%s)"
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

    cycle_dur=$(( $(date +%s) - cycle_start ))
    log "======== CYCLE $cycle DONE (${cycle_dur}s) ========"

    if [ "$CYCLE_LIMIT" -gt 0 ] && [ "$cycle" -ge "$CYCLE_LIMIT" ]; then
        log "Cycle limit reached ($CYCLE_LIMIT). Stopping."
        break
    fi
done

log "Final plan state:"
cat "$PLAN_FILE" | tee -a "$LOG_FILE"
