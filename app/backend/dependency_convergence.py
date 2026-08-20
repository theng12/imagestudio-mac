"""Fixed Image Studio dependency convergence commands."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[1]
MODES = {"base", "generation", "all-installed"}


def uv_executable() -> str:
    """Return only Pinokio's configured uv executable, or fail closed."""
    config = Path.home() / ".pinokio" / "config.json"
    try:
        value = json.loads(config.read_text(encoding="utf-8"))["home"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Configured Pinokio home is unavailable.") from exc
    if not isinstance(value, str):
        raise RuntimeError("Configured Pinokio home is unavailable.")
    home = Path(value).expanduser()
    if not home.is_absolute():
        raise RuntimeError("Configured Pinokio home must be absolute.")
    uv = home.resolve() / "bin" / "miniforge" / "bin" / "uv"
    if not uv.is_file():
        raise RuntimeError("Configured Pinokio uv executable is unavailable.")
    return str(uv)


def generation_installed() -> bool:
    return importlib.util.find_spec("mflux") is not None


def _pip(requirements: Path) -> list[str]:
    return [uv_executable(), "pip", "install", "--python", sys.executable,
            "-r", str(requirements)]


def converge(mode: str, *, runner=subprocess.run) -> None:
    if mode not in MODES:
        raise ValueError("mode must be base, generation, or all-installed")
    commands = []
    if mode in {"base", "all-installed"}:
        commands.append(_pip(APP / "requirements.txt"))
    if mode == "generation" or (mode == "all-installed" and generation_installed()):
        commands.extend([
            _pip(APP / "requirements-generation.lock.txt"),
            [sys.executable, "-c", "import mflux; print('GEN_VERIFY_OK')"],
        ])
    for argv in commands:
        runner(argv, cwd=APP, check=True, timeout=1800)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=sorted(MODES))
    args = parser.parse_args()
    converge(args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
