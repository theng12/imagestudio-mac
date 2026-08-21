import json
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[2]


def _shell_function(name: str) -> str:
    script = (ROOT / "install_service.sh").read_text(encoding="utf-8")
    match = re.search(
        rf"(?ms)^{re.escape(name)}\(\) \{{\n.*?^\}}\n",
        script,
    )
    assert match, f"install_service.sh must expose {name}"
    return match.group(0)


def _run_environment_writer(environment_file: Path) -> None:
    command = (
        f"{_shell_function('set_pinokio_autolaunch')}"
        f"set_pinokio_autolaunch {shlex.quote(str(environment_file))}"
    )
    subprocess.run(["/bin/bash", "-c", command], check=True)


def _run_environment_seed(template: Path, environment_file: Path) -> None:
    command = (
        f"{_shell_function('seed_environment')}"
        f"seed_environment {shlex.quote(str(template))} {shlex.quote(str(environment_file))}"
    )
    subprocess.run(["/bin/bash", "-c", command], check=True)


def _install_launcher() -> dict:
    script = "console.log(JSON.stringify(require('./install.js')))"
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def _start_launcher() -> dict:
    script = "console.log(JSON.stringify(require('./start.js')))"
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def test_repository_ships_a_template_and_ignores_machine_environment():
    template = ROOT / "ENVIRONMENT.example"

    assert template.is_file()
    assert subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", "ENVIRONMENT"], cwd=ROOT,
    ).returncode == 0
    assert subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", "ENVIRONMENT.example"], cwd=ROOT,
    ).returncode == 1


def test_install_seeds_environment_only_when_machine_file_is_absent():
    launcher = _install_launcher()

    assert launcher["run"][0] == {
        "when": "{{!exists('ENVIRONMENT')}}",
        "method": "fs.copy",
        "params": {"src": "ENVIRONMENT.example", "dest": "ENVIRONMENT"},
    }
    assert launcher["run"][1]["method"] == "shell.run"


def test_start_seeds_environment_and_has_first_run_hf_cache_fallback():
    launcher = _start_launcher()

    assert launcher["run"][0] == {
        "when": "{{!exists('ENVIRONMENT')}}",
        "method": "fs.copy",
        "params": {"src": "ENVIRONMENT.example", "dest": "ENVIRONMENT"},
    }
    server = launcher["run"][1]
    assert server["method"] == "shell.run"
    assert server["params"]["env"]["HF_HOME"] == (
        "{{envs.HF_HOME || path.resolve(cwd, 'cache/HF_HOME')}}"
    )


def test_service_writer_preserves_template_and_machine_settings(tmp_path):
    environment_file = tmp_path / "ENVIRONMENT"
    environment_file.write_text(
        (ROOT / "ENVIRONMENT.example").read_text(encoding="utf-8")
        + "KEEP_MACHINE_SETTING=unchanged\n",
        encoding="utf-8",
    )

    _run_environment_writer(environment_file)

    result = environment_file.read_text(encoding="utf-8")
    assert "HF_HOME=./cache/HF_HOME\n" in result
    assert "IMAGESTUDIO_EXTRA_MODEL_DIRS=\n" in result
    assert "KEEP_MACHINE_SETTING=unchanged\n" in result
    assert result.count("PINOKIO_SCRIPT_AUTOLAUNCH=start.js\n") == 1


def test_service_seed_creates_missing_environment_without_overwriting(tmp_path):
    template = tmp_path / "ENVIRONMENT.example"
    environment_file = tmp_path / "ENVIRONMENT"
    template.write_text("DEFAULT_SETTING=one\n", encoding="utf-8")

    _run_environment_seed(template, environment_file)
    assert environment_file.read_text(encoding="utf-8") == "DEFAULT_SETTING=one\n"

    environment_file.write_text("OWNER_SETTING=keep\n", encoding="utf-8")
    template.write_text("DEFAULT_SETTING=two\n", encoding="utf-8")
    _run_environment_seed(template, environment_file)

    assert environment_file.read_text(encoding="utf-8") == "OWNER_SETTING=keep\n"


def test_install_service_disables_pinokio_autolaunch_idempotently(tmp_path):
    environment_file = tmp_path / "ENVIRONMENT"
    environment_file.write_text(
        "KEEP_ME=1\n"
        "PINOKIO_SCRIPT_AUTOLAUNCH=old.js\n"
        "PINOKIO_SCRIPT_AUTOLAUNCH_ENABLED=true\n"
        "PINOKIO_SCRIPT_REQUIRES=stale-dependency\n",
        encoding="utf-8",
    )

    _run_environment_writer(environment_file)
    _run_environment_writer(environment_file)

    lines = environment_file.read_text(encoding="utf-8").splitlines()
    assert lines.count("KEEP_ME=1") == 1
    assert lines.count("PINOKIO_SCRIPT_AUTOLAUNCH=start.js") == 1
    assert lines.count("PINOKIO_SCRIPT_AUTOLAUNCH_ENABLED=false") == 1
    assert lines.count("PINOKIO_SCRIPT_REQUIRES=") == 1
    assert not list(tmp_path.glob(".ENVIRONMENT.tmp.*"))


def test_install_service_writes_ownership_after_bootstrap_before_marker():
    script = (ROOT / "install_service.sh").read_text(encoding="utf-8")

    seed = script.index('seed_environment "$ROOT/ENVIRONMENT.example" "$ROOT/ENVIRONMENT"')
    writer = script.index('set_pinokio_autolaunch "$ROOT/ENVIRONMENT"')
    first_bootstrap = script.index('_bootstrap "$LA/$SRV.plist"')
    second_bootstrap = script.index('_bootstrap "$LA/$WD.plist"')
    marker = script.index('touch "$ROOT/service/.installed"')

    assert first_bootstrap < seed < writer < marker
    assert second_bootstrap < seed < writer < marker


def test_start_launcher_keeps_url_capture_and_local_set_contract():
    start = (ROOT / "start.js").read_text(encoding="utf-8")

    assert 'event: "/Uvicorn running on (http:\\\\/\\\\/[0-9.:]+)/",' in start
    assert 'url: "{{input.event[1]}}"' in start
