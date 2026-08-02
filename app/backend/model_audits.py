"""Read and validate owner-approved model-audit candidate records.

The sibling catalog reports evidence only.  Studio Hub remains responsible for
deciding whether an audited candidate is exposed to GenStudio.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


_ROOT = Path(__file__).resolve().parents[2]
_AUDIT_RECORDS = {
    "AITRADER/FLUX2-klein-4B-mlx-4bit": (
        _ROOT
        / "model-audits"
        / "2026-08-02-group-a"
        / "aitrader--flux2-klein-4b-mlx-4bit.audit.json"
    ),
}
_AUDIT_STATUSES = {"passed", "conditional", "failed", "revoked"}
_HASHED_FIELDS = (
    "schema",
    "schema_version",
    "runtime_revision",
    "approved_operations",
    "adapter",
    "controls",
    "input_limits",
    "output_limits",
    "hardware",
)


class ModelAuditError(ValueError):
    """Raised when a checked-in model audit is malformed or has drifted."""


def contract_hash(internal_model_id: str, candidate: dict[str, Any]) -> str:
    """Return the deterministic hash of the executable candidate contract."""
    contract = {
        "internal_model_id": internal_model_id,
        **{field: candidate.get(field) for field in _HASHED_FIELDS},
    }
    encoded = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_candidate(internal_model_id: str, candidate: dict[str, Any]) -> None:
    if candidate.get("schema") != "studio.model-audit":
        raise ModelAuditError(f"{internal_model_id}: unsupported model-audit schema")
    if candidate.get("schema_version") != 1:
        raise ModelAuditError(f"{internal_model_id}: unsupported model-audit schema version")
    if candidate.get("audit_status") not in _AUDIT_STATUSES:
        raise ModelAuditError(f"{internal_model_id}: invalid audit status")
    if not isinstance(candidate.get("candidate_for_genstudio"), bool):
        raise ModelAuditError(f"{internal_model_id}: candidate flag must be boolean")
    if not re.fullmatch(r"[0-9a-f]{40,64}", str(candidate.get("runtime_revision", ""))):
        raise ModelAuditError(f"{internal_model_id}: runtime revision must be immutable")
    operations = candidate.get("approved_operations")
    if not isinstance(operations, list) or not operations or not all(isinstance(v, str) for v in operations):
        raise ModelAuditError(f"{internal_model_id}: approved operations are required")
    for field in ("adapter", "controls", "input_limits", "output_limits", "hardware"):
        if not isinstance(candidate.get(field), dict):
            raise ModelAuditError(f"{internal_model_id}: {field} must be an object")
    if candidate.get("contract_hash") != contract_hash(internal_model_id, candidate):
        raise ModelAuditError(f"{internal_model_id}: contract hash does not match the candidate")


@lru_cache(maxsize=None)
def candidate_for(internal_model_id: str) -> dict[str, Any] | None:
    """Load one checked-in candidate summary, failing closed on invalid evidence."""
    path = _AUDIT_RECORDS.get(internal_model_id)
    if path is None:
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelAuditError(f"{internal_model_id}: model-audit record is unreadable") from exc
    if record.get("model", {}).get("internal_model_id") != internal_model_id:
        raise ModelAuditError(f"{internal_model_id}: audit record identifies another model")
    candidate = record.get("genstudio_candidate")
    if not isinstance(candidate, dict):
        raise ModelAuditError(f"{internal_model_id}: candidate summary is missing")
    _validate_candidate(internal_model_id, candidate)
    return candidate
