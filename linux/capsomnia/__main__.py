"""Entry point: ``python -m capsomnia``.

Single-instance guard via a lock file in the runtime dir, then hand off to the
Qt tray application.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _acquire_single_instance_lock():
    import fcntl

    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/capsomnia-{os.getuid()}"
    Path(runtime).mkdir(parents=True, exist_ok=True)
    lock_path = Path(runtime) / "capsomnia.lock"
    lock_file = open(lock_path, "w")  # noqa: SIM115 — kept open for lock lifetime
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return lock_file


def main() -> int:
    lock = _acquire_single_instance_lock()
    if lock is None:
        print("Capsomnia is already running.", file=sys.stderr)
        return 0

    from .app import main as app_main

    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
