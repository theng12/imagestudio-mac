import json
import sys
from pathlib import Path
import subprocess

import pytest

from backend import dependency_convergence as convergence


class FakeRunner:
    def __init__(self):
        self.argv = []
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.argv.append(argv)
        self.calls.append(kwargs)


@pytest.fixture
def fake_runner(monkeypatch):
    monkeypatch.setattr(convergence, "uv_executable", lambda: "/fixed/pinokio/bin/miniforge/bin/uv")
    return FakeRunner()


def test_base_uses_only_base_requirements(fake_runner):
    convergence.converge("base", runner=fake_runner)

    assert fake_runner.argv == [[
        "/fixed/pinokio/bin/miniforge/bin/uv", "pip", "install", "--python", sys.executable,
        "-r", str(convergence.APP / "requirements.txt"),
    ]]
    assert fake_runner.calls == [{"cwd": convergence.APP, "check": True, "timeout": 1800}]


def test_all_installed_skips_missing_generation(monkeypatch, fake_runner):
    monkeypatch.setattr(convergence, "generation_installed", lambda: False)

    convergence.converge("all-installed", runner=fake_runner)

    assert fake_runner.argv == [[
        "/fixed/pinokio/bin/miniforge/bin/uv", "pip", "install", "--python", sys.executable,
        "-r", str(convergence.APP / "requirements.txt"),
    ]]


def test_all_installed_refreshes_existing_generation_in_fixed_order(monkeypatch, fake_runner):
    monkeypatch.setattr(convergence, "generation_installed", lambda: True)

    convergence.converge("all-installed", runner=fake_runner)

    assert fake_runner.argv == [
        ["/fixed/pinokio/bin/miniforge/bin/uv", "pip", "install", "--python", sys.executable,
         "-r", str(convergence.APP / "requirements.txt")],
        ["/fixed/pinokio/bin/miniforge/bin/uv", "pip", "install", "--python", sys.executable,
         "-r", str(convergence.APP / "requirements-generation.lock.txt")],
        [sys.executable, "-c", "import mflux; print('GEN_VERIFY_OK')"],
    ]


def test_generation_installs_lock_and_verifies_mflux(fake_runner):
    convergence.converge("generation", runner=fake_runner)

    assert fake_runner.argv == [
        ["/fixed/pinokio/bin/miniforge/bin/uv", "pip", "install", "--python", sys.executable,
         "-r", str(convergence.APP / "requirements-generation.lock.txt")],
        [sys.executable, "-c", "import mflux; print('GEN_VERIFY_OK')"],
    ]


def test_runner_failure_propagates_without_running_later_commands(fake_runner):
    def fail(argv, **kwargs):
        fake_runner(argv, **kwargs)
        raise subprocess.CalledProcessError(1, argv)

    with pytest.raises(subprocess.CalledProcessError):
        convergence.converge("generation", runner=fail)

    assert len(fake_runner.argv) == 1


def test_invalid_mode_is_rejected_without_running_commands(fake_runner):
    with pytest.raises(ValueError, match="base, generation, or all-installed"):
        convergence.converge("arbitrary-package", runner=fake_runner)

    assert fake_runner.argv == []


def test_uv_executable_uses_only_the_fixed_configured_pinokio_path(tmp_path, monkeypatch):
    home = tmp_path / "pinokio"
    uv = home / "bin" / "miniforge" / "bin" / "uv"
    uv.parent.mkdir(parents=True)
    uv.touch()
    config = tmp_path / ".pinokio" / "config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"home": str(home)}), encoding="utf-8")
    monkeypatch.setattr(convergence.Path, "home", classmethod(lambda _cls: tmp_path))

    assert convergence.uv_executable() == str(uv)


@pytest.mark.parametrize(
    "payload",
    [None, "{not json", {}, {"home": 1}, {"home": "relative/pinokio"}, {"home": "/missing/pinokio"}],
)
def test_uv_executable_fails_closed_for_invalid_or_missing_config(tmp_path, monkeypatch, payload):
    config = tmp_path / ".pinokio" / "config.json"
    if payload is not None:
        config.parent.mkdir()
        config.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(convergence.Path, "home", classmethod(lambda _cls: tmp_path))

    with pytest.raises(RuntimeError, match="Configured Pinokio"):
        convergence.uv_executable()


@pytest.mark.parametrize(
    ("launcher", "mode"),
    [("install.js", "base"), ("update.js", "all-installed"), ("install_generation.js", "generation")],
)
def test_launchers_use_only_the_convergence_module(launcher, mode):
    source = (Path(__file__).resolve().parents[2] / launcher).read_text(encoding="utf-8")
    invocation = f"python -m backend.dependency_convergence {mode}"

    assert source.count("python -m backend.dependency_convergence") == 1
    assert source.count(invocation) == 1
    assert "uv pip install" not in source
    assert "pip install" not in source
    assert "conda install" not in source


def test_update_and_generation_launchers_keep_service_aware_restart_branches():
    root = Path(__file__).resolve().parents[2]
    for launcher in ("update.js", "install_generation.js"):
        source = (root / launcher).read_text(encoding="utf-8")
        assert "{{exists('service/.installed')}}" in source
        assert "bash install_service.sh" in source
        assert "{{!exists('service/.installed')}}" in source
        assert 'uri: "start.js"' in source
