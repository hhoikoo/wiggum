## Task: Triage Failures

### Instructions

Group the failures by root cause. Multiple tests may fail for the same reason (e.g. a missing import, a wrong return type, a missing method). Each group becomes one task.

Output one task per line. Each line should describe the root cause and list the affected tests/files. Example:
Missing GitPort.status method -- FAILED tests/test_git.py::test_status, tests/test_git.py::test_status_clean
Import error in wiggum.config -- FAILED tests/test_config.py::test_load, tests/test_cli.py::test_startup

Output ONLY the task lines. No numbering, no bullets, no commentary.
