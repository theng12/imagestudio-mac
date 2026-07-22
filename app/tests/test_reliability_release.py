from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
WATCHDOG = ROOT / "imagestudio-watchdog.sh"


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def _watchdog_env(tmp_path: Path, *, healthy: bool) -> tuple[dict[str, str], Path, Path]:
    curl = tmp_path / "curl"
    launchctl = tmp_path / "launchctl"
    state = tmp_path / "watchdog-state"
    launches = tmp_path / "launches.log"
    _write_executable(curl, f"#!/bin/sh\nexit {0 if healthy else 1}\n")
    _write_executable(
        launchctl,
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$WATCHDOG_LAUNCH_LOG\"\n",
    )
    env = {
        **os.environ,
        "IMAGESTUDIO_WATCHDOG_CURL_BIN": str(curl),
        "IMAGESTUDIO_WATCHDOG_LAUNCHCTL_BIN": str(launchctl),
        "IMAGESTUDIO_WATCHDOG_STATE_FILE": str(state),
        "IMAGESTUDIO_WATCHDOG_FAILURES_REQUIRED": "3",
        "WATCHDOG_LAUNCH_LOG": str(launches),
    }
    return env, state, launches


def _run_watchdog(env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/bin/bash", str(WATCHDOG)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def test_watchdog_requires_three_consecutive_failures(tmp_path: Path):
    env, state, launches = _watchdog_env(tmp_path, healthy=False)

    first = _run_watchdog(env)
    second = _run_watchdog(env)
    assert "(1/3)" in first.stdout
    assert "(2/3)" in second.stdout
    assert state.read_text(encoding="utf-8").strip() == "2"
    assert not launches.exists()

    third = _run_watchdog(env)
    assert "failed 3 consecutive times" in third.stdout
    assert "kickstart -k" in launches.read_text(encoding="utf-8")


def test_watchdog_success_resets_failure_streak(tmp_path: Path):
    failing_env, state, launches = _watchdog_env(tmp_path, healthy=False)
    _run_watchdog(failing_env)
    assert state.read_text(encoding="utf-8").strip() == "1"

    healthy_env, _, _ = _watchdog_env(tmp_path, healthy=True)
    _run_watchdog(healthy_env)
    assert not state.exists()

    failing_env, _, _ = _watchdog_env(tmp_path, healthy=False)
    after_reset = _run_watchdog(failing_env)
    assert "(1/3)" in after_reset.stdout
    assert not launches.exists()


def test_all_generation_installers_use_the_qualified_lock():
    expected = "requirements-generation.lock.txt"
    assert expected in (ROOT / "install_generation.js").read_text(encoding="utf-8")
    assert expected in (ROOT / "update.js").read_text(encoding="utf-8")
    assert expected in (ROOT / "app/backend/auto_update_config.py").read_text(encoding="utf-8")
    assert expected in (ROOT / "app/backend/generation_installer.py").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for launcher contract checks")
def test_whats_new_is_visible_in_every_launcher_state_and_service_order_is_shared():
    script = r"""
const launcher = require(process.argv[1]);
const scenarios = JSON.parse(process.argv[2]);
(async () => {
  const output = [];
  for (const state of scenarios) {
    const info = {
      exists: (name) => name === 'conda_env' ? state.installed :
        name === 'conda_env/lib/python3.12/site-packages/mflux' ? state.generation :
        name === 'service/.installed' ? state.service : false,
      running: (name) => Boolean(state.running && state.running[name]),
      local: () => state.url ? {url: state.url} : {},
    };
    output.push((await launcher.menu({}, info)).map((item) => item.text));
  }
  process.stdout.write(JSON.stringify(output));
})().catch((error) => { console.error(error); process.exit(1); });
"""
    scenarios = [
        {"installed": False},
        {"installed": True, "running": {"install.js": True}},
        {"installed": True, "running": {"install_generation.js": True}},
        {"installed": True, "running": {"update.js": True}},
        {"installed": True, "running": {"update_and_restart.js": True}},
        {"installed": True, "running": {"reset.js": True}},
        {"installed": True, "generation": True, "service": True},
        {"installed": True, "generation": True, "running": {"start.js": True}},
        {
            "installed": True,
            "generation": True,
            "running": {"start.js": True},
            "url": "http://0.0.0.0:47868",
        },
        {"installed": True, "generation": True},
    ]
    result = subprocess.run(
        ["node", "-e", script, str(ROOT / "pinokio.js"), json.dumps(scenarios)],
        text=True,
        capture_output=True,
        check=True,
    )
    menus = json.loads(result.stdout)
    assert all("What's New" in menu for menu in menus)

    service = menus[6]
    assert service.index("Service Logs") < service.index("Outputs")
    assert service.index("Outputs") < service.index("HF Cache")
    assert service.index("HF Cache") < service.index("Uninstall Startup Service")
    assert service.index("Uninstall Startup Service") < service.index("Reinstall Generation")
    assert service.index("Reinstall Generation") < service.index("Update")
    assert service[-1] == "What's New"


def test_interactive_controls_have_a_minimum_size_without_restyling_metadata():
    css = (ROOT / "app/frontend/style.css").read_text(encoding="utf-8")
    assert "--control-font-min: 15px" in css
    assert "--control-height-min: 40px" in css
    assert "select option," in css
    assert "font-size: var(--control-font-min)" in css
    assert ".family-facts" in css and "font-size: 10px" in css


def test_lightweight_update_banner_points_to_current_controls():
    html = (ROOT / "app/frontend/index.html").read_text(encoding="utf-8")
    assert "Open Settings \\u2192 Automatic updates" in html
    assert "Open Generate and choose Install engines" in html
    assert "In the Pinokio sidebar, click Update." not in html
