from types import SimpleNamespace

from backend import main


def test_generation_blocks_automatic_update(monkeypatch):
    monkeypatch.setattr(main.gen_manager, "list_jobs", lambda: [SimpleNamespace(state="running")])
    monkeypatch.setattr(main.manager, "list_jobs", lambda: [])
    monkeypatch.setattr(main.generation_installer, "status", lambda: {"state": "idle"})
    assert main._automatic_update_blockers() == ["an image generation is queued or running"]


def test_download_and_installer_block_automatic_update(monkeypatch):
    monkeypatch.setattr(main.gen_manager, "list_jobs", lambda: [])
    monkeypatch.setattr(main.manager, "list_jobs", lambda: [SimpleNamespace(state="queued")])
    monkeypatch.setattr(main.generation_installer, "status", lambda: {"state": "installing"})
    assert main._automatic_update_blockers() == [
        "a model download is active",
        "the generation engine installer is active",
    ]
