# Progress

## 2026-03-29 - Wire SIGINT handler into runner loops
- Imported `register_handler` and `set_active_plan` from `wiggum.interrupt` in `runner.py`
- Called `register_handler()` at the start of `run_plan()`, `run_build()`, and `run_combined()`
- Wrapped `invoke_claude()` in `run_build()` with `set_active_plan(state)` before and `set_active_plan(None)` in a `finally` block after
- Added `autouse` fixture `_restore_interrupt_state` to save/restore signal handler and clear module state between tests
- Added `test_calls_register_handler` to `TestRunPlan`, `TestRunBuild`, and `TestRunCombined`
- Added `test_sets_active_plan_before_invoke` and `test_clears_active_plan_after_invoke` to `TestRunBuild`
- Files changed: `src/wiggum/runner.py`, `tests/test_runner.py`
- **Learnings for future iterations:**
  - `run_combined` delegates to `run_plan` and `run_build`, so `register_handler` is called 3 times total; test for `run_combined` uses `assert_called()` rather than `assert_called_once()`
  - Patching `wiggum.runner.register_handler` requires the function to be imported by name into `runner.py` (not via `import wiggum.interrupt`)
  - The `side_effect` capture pattern from `test_subprocess_util.py` works for `invoke_claude` in runner tests too: define a function that reads `interrupt_mod._active_plan` and returns `InvokeResult`
---

## Codebase Patterns
- Tests mirror src/ structure: `src/wiggum/foo.py` -> `tests/test_foo.py`
- Use `autouse` fixture in test files to restore module-level globals after each test (see `test_interrupt.py` and `test_subprocess_util.py` patterns)
- Access private module state (`mod._active_proc`) directly in tests to verify runtime behavior; do not only check mock call counts
- `wiggum.interrupt` module-level globals (`_active_proc`, `_active_plan`) are the source of truth for SIGINT handler state

---

## 2026-03-29 - Wire SIGINT handler into invoke_claude
- Imported `set_active_process` from `wiggum.interrupt` in `subprocess_util.py`
- Called `set_active_process(proc)` after `Popen` and before `proc.communicate()`
- Added `try/finally` block so `set_active_process(None)` always runs after communicate, even on exception
- Added three new tests in `test_subprocess_util.py`:
  - `test_sets_active_process_before_communicate`: uses `side_effect` on `proc.communicate` to capture `interrupt_mod._active_proc` at call time and assert it equals `proc`
  - `test_clears_active_process_after_success`: verifies `_active_proc` is `None` after a successful invocation
  - `test_clears_active_process_after_exception`: makes `communicate` raise `RuntimeError`, verifies `_active_proc` is still cleared
- Added `autouse` fixture `_clear_active_process` to reset interrupt module state between tests
- Files changed: `src/wiggum/subprocess_util.py`, `tests/test_subprocess_util.py`
- **Learnings for future iterations:**
  - No circular import: `subprocess_util` -> `interrupt` is safe because `interrupt` does not import from `subprocess_util`
  - To test "state during a call", use `side_effect` on the mock to capture module globals at call time rather than checking before/after only
  - `proc.communicate` is called with `input=prompt` as a keyword arg; use `*args, **kwargs` in `side_effect` functions for forward compatibility
---
## Iteration 1 (2026-03-29T13:59:10)
- **Task:** Wire SIGINT handler into `invoke_claude()`: import `set_active_process` from `wiggum.interrupt` in `subprocess_util.py`, call `set_active_process(proc)` before `proc.communicate()` and `set_active_process(None)` in a `finally` block after. Add tests in `test_subprocess_util.py` that verify the active process is set during invocation and cleared after (both on success and on exception). Pyright, ruff, and pytest pass.
- **Outcome:** pass

## Iteration 2 (2026-03-29)
- **Task:** Wire SIGINT handler into runner loops: import `register_handler` and `set_active_plan` from `wiggum.interrupt` in `runner.py`. Call `register_handler()` at the start of `run_plan()`, `run_build()`, and `run_combined()`. In `run_build()`, call `set_active_plan(state)` before each `invoke_claude()` call and `set_active_plan(None)` after. Update tests in `test_runner.py`.
- **Outcome:** pass

## Iteration 3 (2026-03-29T14:02:39)
- **Task:** Wire SIGINT handler into runner loops: import `register_handler` and `set_active_plan` from `wiggum.interrupt` in `runner.py`. Call `register_handler()` at the start of `run_plan()`, `run_build()`, and `run_combined()`. In `run_build()`, call `set_active_plan(state)` before each `invoke_claude()` call and `set_active_plan(None)` after. Update tests in `test_runner.py` to verify `register_handler` is called and `set_active_plan` is set/cleared around subprocess invocations. Pyright, ruff, and pytest pass.
- **Outcome:** pass

## Iteration 4 (2026-03-29) - Create scripts/ symlinks for feature-work-on skill
- Verified that `plugins/wiggum/skills/feature-work-on/scripts/` already exists with all required symlinks: `fetch-issue.sh`, `session-launch.sh`, and `tmux-send.sh`, all pointing to `../../../scripts/<name>.sh` and resolving to the correct shared scripts in `plugins/wiggum/scripts/`.
- No changes required -- task was already complete from a previous iteration.
- Files changed: none
- **Learnings for future iterations:**
  - The `scripts/` directory pattern for skill-level symlinks mirrors the structure in other skills like `prd-close/scripts/`. Check existing state before creating symlinks.
  - Symlink targets use path `../../../scripts/<name>.sh` from inside `plugins/wiggum/skills/<skill>/scripts/`, which resolves to `plugins/wiggum/scripts/<name>.sh`.
---

## Iteration 5 (2026-03-29T14:03:30)
- **Task:** Create `scripts/` directory with symlinks for `feature-work-on` skill: create `plugins/wiggum/skills/feature-work-on/scripts/` and add relative symlinks for `fetch-issue.sh`, `session-launch.sh`, and `tmux-send.sh` pointing to `../../../scripts/<name>.sh`. Verify each symlink resolves to the correct shared script.
- **Outcome:** pass

## 2026-03-29 - Create scripts/ symlinks for feature-stop-work-on skill
- Verified `plugins/wiggum/skills/feature-stop-work-on/scripts/` exists with `worktree-remove.sh` and `tmux-kill-window.sh` symlinks pointing to `../../../scripts/<name>.sh`, resolving to `plugins/wiggum/scripts/worktree-remove.sh` and `plugins/wiggum/scripts/tmux-kill-window.sh`.
- Both shared scripts exist in `plugins/wiggum/scripts/`.
- The symlinks were already committed in commit `52cb834` -- no changes required.
- Files changed: none
- **Learnings for future iterations:**
  - Always check git log for the skill directory before creating symlinks -- prior skill scaffolding commits may have already included them.
---

## Iteration 6 (2026-03-29T14:04:28)
- **Task:** Create `scripts/` directory with symlinks for `feature-stop-work-on` skill: create `plugins/wiggum/skills/feature-stop-work-on/scripts/` and add relative symlinks for `worktree-remove.sh` and `tmux-kill-window.sh` pointing to `../../../scripts/<name>.sh`. Verify each symlink resolves to the correct shared script.
- **Outcome:** pass
