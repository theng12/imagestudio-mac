"""Fixed, in-app installer for Image Studio's generation dependencies.

The Web UI can run in launchd service mode without Pinokio's launcher sidebar.
This module exposes one deliberately narrow maintenance action: install the
checked-in generation requirements into the interpreter running the server.
It never accepts package names or shell commands from the request.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = APP_DIR.parent
REQUIREMENTS = APP_DIR / "requirements-generation.txt"
STATUS_FILE = APP_DIR / ".generation-install.json"
LOG_FILE = PROJECT_DIR / "logs" / "generation-install.log"
SERVICE_MARKER = PROJECT_DIR / "service" / ".installed"
SERVICE_LABEL = "com.kh.imagestudio.server"

_lock = threading.Lock()
_thread: threading.Thread | None = None


def _write_status(**values: object) -> dict:
    current = _read_status()
    current.update(values)
    current["updated_at"] = time.time()
    STATUS_FILE.write_text(json.dumps(current, indent=2))
    return current


def _read_status() -> dict:
    try:
        return json.loads(STATUS_FILE.read_text())
    except Exception:
        return {
            "state": "idle",
            "message": "Generation dependencies have not been installed from this screen.",
            "restart_required": False,
        }


def status() -> dict:
    data = _read_status()
    # A service restart replaces the process that wrote the restarting state.
    # Reaching this module in a new process is proof the restart succeeded.
    if data.get("state") == "restarting" and data.get("server_pid") != os.getpid():
        data = _write_status(
            state="done",
            message="Generation dependencies installed and the service restarted.",
            restart_required=False,
            server_pid=os.getpid(),
        )
    data["log_path"] = str(LOG_FILE)
    try:
        lines = LOG_FILE.read_text(errors="replace").splitlines()
        data["log_tail"] = lines[-30:]
    except Exception:
        data["log_tail"] = []
    return data


def start() -> dict:
    global _thread
    with _lock:
        if _thread and _thread.is_alive():
            return status()
        _write_status(
            state="installing",
            message="Installing the local MLX and Diffusers engines...",
            started_at=time.time(),
            finished_at=None,
            restart_required=False,
            server_pid=os.getpid(),
        )
        _thread = threading.Thread(target=_run, name="generation-installer", daemon=True)
        _thread.start()
    return status()


def _run() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    try:
        with LOG_FILE.open("w") as log:
            log.write("Image Studio generation dependency install\n")
            log.write("Interpreter: " + sys.executable + "\n\n")
            log.flush()
            result = subprocess.run(
                command,
                cwd=str(APP_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        if result.returncode != 0:
            _write_status(
                state="error",
                message=f"Dependency installation failed (exit {result.returncode}).",
                finished_at=time.time(),
                restart_required=False,
            )
            return

        if SERVICE_MARKER.exists() and sys.platform == "darwin":
            _write_status(
                state="restarting",
                message="Installed. Restarting the Image Studio service...",
                finished_at=time.time(),
                restart_required=False,
            )
            # Give the POST response time to reach the browser before launchd
            # replaces this process. The browser reconnects and re-checks status.
            time.sleep(1.0)
            subprocess.Popen(
                [
                    "/bin/launchctl",
                    "kickstart",
                    "-k",
                    f"gui/{os.getuid()}/{SERVICE_LABEL}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        _write_status(
            state="done",
            message="Installed. Restart Image Studio once to load the new engines.",
            finished_at=time.time(),
            restart_required=True,
        )
    except Exception as exc:
        _write_status(
            state="error",
            message=f"Dependency installation failed: {type(exc).__name__}: {exc}",
            finished_at=time.time(),
            restart_required=False,
        )
