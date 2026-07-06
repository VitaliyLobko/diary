"""Development server with reliable auto-reload.

uvicorn's built-in ``--reload`` does not cleanly restart its worker on Windows
here: WatchFiles detects the change and logs "Reloading...", but the old worker
process is never terminated, so it keeps holding the port and serving stale
code. This wraps uvicorn in watchfiles' external process runner, which kills and
restarts the *whole* process on any change under the watched paths — a clean,
reliable reload.

Usage:
    python dev.py
"""

import sys

from watchfiles import run_process

# Forward slashes so the path survives shlex splitting on Windows; the venv's
# own interpreter guarantees uvicorn and the app deps are importable.
_PYTHON = sys.executable.replace("\\", "/")
_COMMAND = f"{_PYTHON} -m uvicorn main:app --host 127.0.0.1 --port 8000"

# Watch only application code — not .venv (thousands of files) — so reloads are
# fast and never miss a change.
_WATCH_PATHS = ("src", "templates", "main.py")


if __name__ == "__main__":
    run_process(*_WATCH_PATHS, target=_COMMAND, target_type="command")
