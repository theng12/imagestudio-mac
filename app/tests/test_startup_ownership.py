import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[2]


def _environment_writer() -> str:
    script = (ROOT / "install_service.sh").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^set_pinokio_autolaunch\(\) \{\n.*?^\}\n",
        script,
    )
    assert match, "install_service.sh must expose its atomic environment writer"
    return match.group(0)


def _run_environment_writer(environment_file: Path) -> None:
    command = (
        f"{_environment_writer()}"
        f"set_pinokio_autolaunch {shlex.quote(str(environment_file))}"
    )
    subprocess.run(["/bin/bash", "-c", command], check=True)


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

    writer = script.index('set_pinokio_autolaunch "$ROOT/ENVIRONMENT"')
    first_bootstrap = script.index('_bootstrap "$LA/$SRV.plist"')
    second_bootstrap = script.index('_bootstrap "$LA/$WD.plist"')
    marker = script.index('touch "$ROOT/service/.installed"')

    assert first_bootstrap < writer < marker
    assert second_bootstrap < writer < marker


def test_start_launcher_keeps_url_capture_and_local_set_contract():
    start = (ROOT / "start.js").read_text(encoding="utf-8")

    assert 'event: "/Uvicorn running on (http:\\\\/\\\\/[0-9.:]+)/",' in start
    assert 'url: "{{input.event[1]}}"' in start
