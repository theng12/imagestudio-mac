import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("release_metadata_check", ROOT / "release_metadata_check.py")
release_metadata = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(release_metadata)


def test_non_metadata_change_requires_version_and_release_notes():
    errors = release_metadata.validate(
        changed_paths={"app/backend/main.py"},
        base_version="1.22.2",
        current_version="1.22.2",
        changelog="## [1.22.2]\n\n- Existing detail\n",
    )
    assert "Non-metadata changes require both VERSION and CHANGELOG.md updates." in errors
    assert "VERSION must increase for non-metadata changes." in errors


def test_current_release_must_be_first_and_have_whats_new_detail():
    errors = release_metadata.validate(
        changed_paths={"VERSION", "CHANGELOG.md", "app/frontend/app.js"},
        base_version="1.22.2",
        current_version="1.22.3",
        changelog="## [1.22.2]\n\n- Existing detail\n\n## [1.22.3]\n\n- Later detail\n",
    )
    assert errors == ["The first CHANGELOG release heading must match the current VERSION."]


def test_release_metadata_passes_for_a_bumped_visible_release():
    errors = release_metadata.validate(
        changed_paths={"VERSION", "CHANGELOG.md", "app/backend/main.py"},
        base_version="1.22.2",
        current_version="1.22.3",
        changelog="## [1.22.3] — 2026-07-20\n\n### Added\n\n- Versioned release details appear in What's New.\n",
    )
    assert errors == []
