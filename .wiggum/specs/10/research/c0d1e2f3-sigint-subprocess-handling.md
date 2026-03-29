# Research: SIGINT and Subprocess Handling in Python CLI Tools

## Question

Best practices for SIGINT handling in Python CLI tools managing long-running subprocesses.

## Findings

### SIGINT Propagation on POSIX

- Ctrl+C sends SIGINT to the entire foreground process group simultaneously
- Both parent and child receive SIGINT automatically -- no forwarding needed
- Parent's job: wait for child to handle its own SIGINT, then run cleanup

### KeyboardInterrupt Race Conditions

- `KeyboardInterrupt` can be raised between any two bytecode instructions
- Documented race windows in `try/finally` blocks (PEP 419 proposed protections but was deferred)
- Do not rely solely on `except KeyboardInterrupt` or `atexit` for critical cleanup

### Recommended Signal Handler Pattern

```python
import signal
import sys

def _sigint_handler(signum, frame):
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # prevent re-entry
    run_cleanup()
    sys.exit(130)  # 128 + SIGINT = conventional exit code

signal.signal(signal.SIGINT, _sigint_handler)
```

Key constraints:
- `signal.signal()` can only be called from main thread
- Re-register `SIG_IGN` immediately to prevent second Ctrl+C from re-entering mid-cleanup
- Exit with code 130 (Unix convention for SIGINT-terminated process)

### subprocess.Popen vs subprocess.run

- **`subprocess.Popen`**: required when the tool needs to react to signals during subprocess execution
- **`subprocess.run`**: only appropriate for short-lived, non-interruptible calls
- With `subprocess.run`, `KeyboardInterrupt` propagates but subprocess is NOT automatically terminated

### Graceful Termination Sequence

```python
def terminate_subprocess(proc, timeout=5):
    proc.terminate()              # SIGTERM -- ask nicely
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()               # SIGKILL -- force
        proc.wait()               # reap zombie
```

### Process Group Isolation

- Default (same group): Ctrl+C reaches both parent and child automatically
- `start_new_session=True`: child in separate session, parent must forward signals explicitly
- `process_group=0` (Python 3.11+): new process group without new session -- preferred over `preexec_fn=os.setpgrp`

### atexit Limitations

- Runs on `sys.exit()` but NOT on unhandled signals or `os._exit()`
- Fragile as primary interrupt cleanup mechanism
- Use as secondary safety net; primary cleanup via signal handler

## Recommendations

1. Register explicit `signal.signal(SIGINT, handler)` for cleanup-critical operations
2. Use `subprocess.Popen` for interruptible workflows
3. SIGTERM first with timeout, SIGKILL fallback, always `proc.wait()`
4. Re-register `SIG_IGN` at start of handler to prevent re-entry
5. Exit with code 130

## Sources

- Python signal, subprocess, atexit docs
- Control-C handling in Python and Trio (njs blog)
- PEP 419
