import json
from pathlib import Path
from unittest.mock import patch

import pytest

from backend import catalog, model_audits
from backend.main import get_catalog


RUNTIME_REPO = "AITRADER/FLUX2-klein-4B-mlx-4bit"
RUNTIME_REVISION = "7fd24828501390b67a92c8b66d2fc5a707d0ba1a"
CONTRACT_HASH = "sha256:879290c9eb1f5395d2fdfe38421f0a571189113076d67f95c91adba48ce94355"


def test_checked_in_candidate_is_valid_and_exactly_hash_bound():
    candidate = model_audits.candidate_for(RUNTIME_REPO)

    assert candidate is not None
    assert candidate["schema"] == "studio.model-audit"
    assert candidate["schema_version"] == 1
    assert candidate["audit_status"] == "passed"
    assert candidate["candidate_for_genstudio"] is True
    assert candidate["runtime_revision"] == RUNTIME_REVISION
    assert candidate["approved_operations"] == ["image.text_to_image"]
    assert candidate["hardware"]["minimum_unified_memory_gb"] == 8
    assert candidate["hardware"]["recommended_unified_memory_gb"] == 16
    assert candidate["hardware"]["benchmarked_unified_memory_gb"] == 16
    assert candidate["contract_hash"] == CONTRACT_HASH
    assert model_audits.contract_hash(RUNTIME_REPO, candidate) == CONTRACT_HASH
    assert "approved_for_genstudio" not in candidate


def test_candidate_contract_exposes_only_qualified_1k_text_to_image_controls():
    candidate = model_audits.candidate_for(RUNTIME_REPO)
    assert candidate is not None

    assert candidate["controls"]["reference_images"] == {"supported": False, "maximum": 0}
    assert candidate["controls"]["negative_prompt"] == {"supported": False}
    assert candidate["controls"]["guidance"] == {"type": "number", "fixed": 1.0}
    assert candidate["controls"]["steps"] == {"type": "integer", "fixed": 4}
    assert candidate["input_limits"]["max_prompt_characters"] == 10_000
    assert candidate["input_limits"]["max_prompt_tokens"] == 512
    assert candidate["output_limits"]["resolution_tiers"] == ["1K"]
    assert all(item["resolution"] == "1K" for item in candidate["output_limits"]["dimensions"])
    assert next(
        item for item in candidate["output_limits"]["dimensions"] if item["aspect_ratio"] == "16:9"
    ) == {
        "aspect_ratio": "16:9",
        "resolution": "1K",
        "width": 1280,
        "height": 720,
        "default": True,
    }


def test_catalog_keeps_technical_capabilities_separate_from_sellable_candidate():
    model = catalog.get_model(RUNTIME_REPO)
    assert model is not None
    serialized = catalog.serialize_model(model)

    assert serialized["capabilities"] == ["txt2img", "img2img", "edit"]
    assert serialized["genstudio_candidate"]["approved_operations"] == ["image.text_to_image"]
    assert "approved_for_genstudio" not in json.dumps(serialized)


def test_live_inventory_adds_candidate_without_weakening_revision_readiness():
    def cache_status(repo):
        return {
            "repo": repo,
            "state": "cached",
            "path": None,
            "bytes_complete": 1,
            "bytes_incomplete": 0,
        }

    with (
        patch("backend.main.cache.status_snapshot", side_effect=cache_status),
        patch("backend.main.cache.snapshot_revision", return_value=RUNTIME_REVISION),
        patch("backend.main.gen_manager.is_available", return_value=True),
        patch(
            "backend.main.gen_manager.availability",
            return_value={"available": True, "busy": False, "queued": 0, "running": 0},
        ),
    ):
        target = next(model for model in get_catalog()["models"] if model["repo"] == RUNTIME_REPO)

    assert target["execution_ready"] is True
    assert target["genstudio_candidate"]["contract_hash"] == CONTRACT_HASH
    assert target["genstudio_candidate"]["capacity"] == {
        "max_concurrency": 1,
        "available_slots": 1,
    }


def test_busy_worker_reports_no_candidate_slot_without_changing_the_contract_hash():
    def cache_status(repo):
        return {
            "repo": repo,
            "state": "cached",
            "path": None,
            "bytes_complete": 1,
            "bytes_incomplete": 0,
        }

    with (
        patch("backend.main.cache.status_snapshot", side_effect=cache_status),
        patch("backend.main.cache.snapshot_revision", return_value=RUNTIME_REVISION),
        patch("backend.main.gen_manager.is_available", return_value=True),
        patch(
            "backend.main.gen_manager.availability",
            return_value={"available": True, "busy": True, "queued": 0, "running": 1},
        ),
    ):
        target = next(model for model in get_catalog()["models"] if model["repo"] == RUNTIME_REPO)

    assert target["genstudio_candidate"]["contract_hash"] == CONTRACT_HASH
    assert target["genstudio_candidate"]["capacity"] == {
        "max_concurrency": 1,
        "available_slots": 0,
    }


def test_invalid_contract_hash_fails_closed(tmp_path, monkeypatch):
    source = Path("model-audits/2026-08-02-group-a/aitrader--flux2-klein-4b-mlx-4bit.audit.json")
    record = json.loads(source.read_text())
    record["genstudio_candidate"]["controls"]["guidance"]["fixed"] = 2.0
    changed = tmp_path / "changed.audit.json"
    changed.write_text(json.dumps(record))

    monkeypatch.setitem(model_audits._AUDIT_RECORDS, RUNTIME_REPO, changed)
    model_audits.candidate_for.cache_clear()
    with pytest.raises(model_audits.ModelAuditError, match="contract hash"):
        model_audits.candidate_for(RUNTIME_REPO)
    model_audits.candidate_for.cache_clear()


def test_audit_record_preserves_the_real_generation_and_2k_safety_decision():
    path = Path("model-audits/2026-08-02-group-a/aitrader--flux2-klein-4b-mlx-4bit.audit.json")
    record = json.loads(path.read_text())
    tests = {item["test_id"]: item for item in record["evidence"]["generation_tests"]}

    one_k = tests["text-to-image-16-9-1k-default"]
    assert one_k["result"] == "passed"
    assert one_k["artifact"]["width"] == 1280
    assert one_k["artifact"]["height"] == 720
    assert len(one_k["artifact"]["sha256"]) == 64

    two_k = tests["text-to-image-16-9-2k-default"]
    assert two_k["result"] == "not_run_memory_safety"
    assert "excluded from the candidate output contract" in two_k["reason"]
