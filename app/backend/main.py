"""
ImageStudio (Mac) — backend.

Serves:
- `/`                                → single-page UI
- `/api/health`                      → liveness check
- `/api/catalog`                     → model catalog + families with live cache state
- `/api/cache/{repo}`                → cache state for one repo
- `/api/downloads`                   → list/start/cancel downloads
- `/api/downloads/stream`            → SSE stream of per-job progress
- `/api/imports/scan`                → list candidates from IMAGESTUDIO_EXTRA_MODEL_DIRS
- `/api/imports`                     → symlink/move an existing folder into HF_HOME
- `/api/loras`                       → list local LoRAs
- `/api/reveal`                      → open a path in the OS file manager (macOS Finder)
- `/api/generate/availability`       → is mflux installed? + aspect presets
- `/api/generate/install/status`     → fixed dependency-installer progress
- `/api/generate/install`            → install checked-in generation requirements
- `/api/generate/txt2img`            → start a text-to-image generation
- `/api/generate/jobs`               → list generation jobs
- `/api/generate/jobs/{id}`          → poll one job
- `/api/generate/jobs/{id}/image`    → fetch the rendered PNG
- `/api/generate/jobs/{id}/cancel`   → cancel a running job
- `/api/generate/stream`             → SSE stream of generation jobs
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import cache, catalog, generation_installer, loras, settings as app_settings, storage_policy
from .downloads import manager
from .generation import manager as gen_manager, diagnostics as gen_diagnostics
from .generation import OUTPUT_DIR
from .imports import import_path, scan_for_candidates
from .fleet_auth import load_token as load_fleet_token, make_middleware as fleet_middleware, manifest
from .auto_update import UpdateError
from .auto_update_config import create_updater


# ───────────── App release version ─────────────
# Read once at module load — `VERSION` lives at the project root (a sibling
# of `app/`). Surfaced via `/api/version` for the WebUI footer and the
# (future) update-available check. Independent of FastAPI's `app.version`,
# which is the internal API version.

def _read_app_version() -> str:
    try:
        version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
        return version_file.read_text().strip()
    except Exception:
        return "unknown"

APP_VERSION = _read_app_version()


# ───────────── FastAPI setup ─────────────

app = FastAPI(title="Image Studio KH", version="0.1.0")

# Permissive CORS so the main mac can call the mac mini over LAN.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Force the Pinokio webview (and any browser) to always re-fetch the
    static frontend. Pinokio's embedded webview caches index.html / app.js /
    style.css very aggressively, so we explicitly disable caching for the
    frontend files and any /assets/* path."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/assets") or path.endswith(
            (".html", ".js", ".css")
        ):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheStaticMiddleware)
FLEET_TOKEN = load_fleet_token()
app.middleware("http")(fleet_middleware(FLEET_TOKEN))
storage_policy.start_background(gen_manager, OUTPUT_DIR)


# ───────────── request models ─────────────

class StartDownloadBody(BaseModel):
    repo: str
    token: Optional[str] = None


class ImportBody(BaseModel):
    source_path: str
    repo: Optional[str] = None
    mode: str = "link"   # "link" | "move"


class RevealBody(BaseModel):
    path: str


class PruneBody(BaseModel):
    keep_last: int = 0            # keep the newest N outputs, delete the rest
    older_than_days: float = 0.0  # or: delete outputs older than this many days


class SettingsBody(BaseModel):
    hf_token: Optional[str] = None   # pass "" to clear; omit field to leave unchanged
    # Cloud-provider credentials (v1.6.0). Same convention: "" clears, omit = unchanged.
    cloudflare_account_id: Optional[str] = None
    cloudflare_api_token: Optional[str] = None
    together_api_key: Optional[str] = None
    # v1.13.0 cloud providers.
    gemini_api_key: Optional[str] = None
    nebius_api_key: Optional[str] = None


class AutoUpdateSettingsBody(BaseModel):
    mode: str
    frequency: str
    maintenance_hour: int
    idle_only: bool = True


class AutoUpdateRequestBody(BaseModel):
    after_current: bool = False


class TokenTestBody(BaseModel):
    hf_token: Optional[str] = None   # if omitted, tests the currently-saved token


class Txt2ImgBody(BaseModel):
    repo: str
    prompt: str
    negative_prompt: str = ""              # ignored by distilled klein (g=1.0); used by dev models
    width: int = 1024
    height: int = 1024
    steps: int = 4
    guidance: float = 3.5
    seed: Optional[int] = None
    quantize: Optional[int] = None         # 3 | 4 | 6 | 8 — runtime quantize for full checkpoints
    lora_names: list[str] = []             # filename stems under app/lora/
    lora_scales: list[float] = []


# Keep resource limits explicit at the API boundary. The frontend already uses
# smaller model-aware presets, but remote callers must not be able to submit
# unbounded dimensions, steps, prompts, or LoRA lists to a GPU-backed service.
MAX_PROMPT_CHARS = 10_000
MIN_IMAGE_SIDE = 512
MAX_IMAGE_SIDE = 2_048
MAX_OUTPUT_PIXELS = 4_000_000
MIN_STEPS = 2
MAX_STEPS = 100
MAX_GUIDANCE = 30.0
MAX_LORA_COUNT = 8
MAX_LORA_SCALE = 2.0
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_INPUT_PIXELS = 16_000_000


def _automatic_update_blockers() -> list[str]:
    reasons: list[str] = []
    generation_states = {str(job.state) for job in gen_manager.list_jobs()}
    if generation_states & {"queued", "running", "cancelling"}:
        reasons.append("an image generation is queued or running")
    download_states = {str(job.state) for job in manager.list_jobs()}
    if download_states & {"queued", "running", "cancelling"}:
        reasons.append("a model download is active")
    installer_state = str(generation_installer.status().get("state", "idle"))
    if installer_state in {"installing", "restarting"}:
        reasons.append("the generation engine installer is active")
    return reasons


auto_updater = create_updater(readiness=_automatic_update_blockers)


def _validate_generation_controls(
    *, prompt: str, width: int, height: int, steps: int, guidance: float,
    seed: Optional[int], quantize: Optional[int],
    lora_names: list[str], lora_scales: list[float],
) -> None:
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    if len(prompt) > MAX_PROMPT_CHARS:
        raise HTTPException(status_code=422, detail=f"prompt must be {MAX_PROMPT_CHARS:,} characters or fewer")
    if not (MIN_IMAGE_SIDE <= width <= MAX_IMAGE_SIDE and MIN_IMAGE_SIDE <= height <= MAX_IMAGE_SIDE):
        raise HTTPException(
            status_code=422,
            detail=f"width and height must each be between {MIN_IMAGE_SIDE} and {MAX_IMAGE_SIDE}px",
        )
    if width % 8 or height % 8:
        raise HTTPException(status_code=422, detail="width and height must be divisible by 8")
    if width * height > MAX_OUTPUT_PIXELS:
        raise HTTPException(status_code=422, detail=f"output is limited to {MAX_OUTPUT_PIXELS:,} pixels")
    if not (MIN_STEPS <= steps <= MAX_STEPS):
        raise HTTPException(status_code=422, detail=f"steps must be between {MIN_STEPS} and {MAX_STEPS}")
    if not math.isfinite(guidance) or not (0.0 <= guidance <= MAX_GUIDANCE):
        raise HTTPException(status_code=422, detail=f"guidance must be between 0 and {MAX_GUIDANCE:g}")
    if seed is not None and not (-1 <= seed <= 2**32 - 1):
        raise HTTPException(status_code=422, detail="seed must be -1 or an unsigned 32-bit integer")
    if quantize is not None and quantize not in (3, 4, 6, 8):
        raise HTTPException(status_code=422, detail="quantize must be one of 3, 4, 6, or 8")
    if len(lora_names) > MAX_LORA_COUNT:
        raise HTTPException(status_code=422, detail=f"at most {MAX_LORA_COUNT} LoRAs may be applied")
    if lora_scales and len(lora_scales) != len(lora_names):
        raise HTTPException(status_code=422, detail="lora_scales must contain one value per LoRA")
    if any(not math.isfinite(scale) or abs(scale) > MAX_LORA_SCALE for scale in lora_scales):
        raise HTTPException(status_code=422, detail=f"LoRA scales must be finite and between {-MAX_LORA_SCALE:g} and {MAX_LORA_SCALE:g}")


def _parse_lora_fields(names: str, scales: str) -> tuple[list[str], list[float]]:
    name_list = [n.strip() for n in names.split(",") if n.strip()] if names else []
    try:
        scale_list = [float(s) for s in scales.split(",") if s.strip()] if scales else []
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="lora_scales must be comma-separated numbers") from exc
    return name_list, scale_list


def _validate_image_strength(value: float) -> float:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise HTTPException(status_code=422, detail="image_strength must be between 0 and 1")
    return value


async def _save_uploaded_image(image: UploadFile) -> Path:
    """Validate and persist one bounded, decodable input image."""
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="image file is required")
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="image file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"image uploads are limited to {MAX_UPLOAD_BYTES // 1024 // 1024} MiB")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as checked:
            checked.verify()
        with Image.open(io.BytesIO(data)) as checked:
            width, height = checked.size
    except Exception as exc:
        raise HTTPException(status_code=400, detail="image must be a valid PNG, JPEG, or WebP file") from exc
    if width * height > MAX_INPUT_PIXELS:
        raise HTTPException(status_code=413, detail=f"input images are limited to {MAX_INPUT_PIXELS:,} pixels")

    uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    import uuid
    suffix = Path(image.filename).suffix.lower() or ".png"
    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
        suffix = ".png"
    saved_image = uploads_dir / (uuid.uuid4().hex[:12] + suffix)
    saved_image.write_bytes(data)
    return saved_image


# ───────────── API: meta ─────────────

@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "version": app.version,
        "app_version": APP_VERSION,
        "hf_home": str(cache.hf_home()),
        "hub_dir": str(cache.hub_dir()),
    }


@app.get("/api/capabilities")
def capabilities() -> dict:
    return manifest(modality="image", title=app.title, version=APP_VERSION,
                    operations=["txt2img", "img2img", "edit"],
                    diagnostics="/api/generate/diagnostics")


# ── Update / generation health (auto-check surfaced by the web-UI banner) ──
# Detect-in-app, apply-via-sidebar: the frontend banner reads this and points
# the user at the single "Update" (or "Install Generation") button in the
# Pinokio sidebar. We never git-pull from here — a sandboxed web page can't
# reliably drive Pinokio's script runner, and the backend restarting itself
# mid-request is fragile.
import importlib.util as _ilu
import threading as _threading
import time as _time
import urllib.request as _urlreq

_UPDATE_REPO = "theng12/imagestudio-mac"
_GEN_MODULE = "mflux"
_update_state = {"checked_at": 0.0, "latest": None}


def _parse_ver(v):
    try:
        return tuple(int(x) for x in str(v).strip().lstrip("v").split(".")[:3])
    except Exception:
        return (0,)


def _refresh_latest_version():
    try:
        url = f"https://raw.githubusercontent.com/{_UPDATE_REPO}/main/VERSION"
        with _urlreq.urlopen(url, timeout=5) as r:
            _update_state["latest"] = r.read().decode("utf-8").strip()
    except Exception:
        pass
    finally:
        _update_state["checked_at"] = _time.time()


@app.get("/api/update-status")
def update_status() -> dict:
    """What the web-UI banner needs: are we behind the published version, and is
    the generation stack actually installed? The remote version is fetched from
    the repo's raw VERSION file at most every ~6h, in a background thread, so a
    slow or unreachable GitHub never blocks the request."""
    if _time.time() - _update_state["checked_at"] > 6 * 3600:
        _threading.Thread(target=_refresh_latest_version, daemon=True).start()
    latest = _update_state["latest"]
    behind = bool(latest and _parse_ver(latest) > _parse_ver(APP_VERSION))
    gen_required = _GEN_MODULE is not None
    gen_ok = (_ilu.find_spec(_GEN_MODULE) is not None) if gen_required else None
    return {
        "app_version": APP_VERSION,
        "latest_version": latest,
        "update_available": behind,
        "generation_required": gen_required,
        "generation_ok": gen_ok,
    }


@app.get("/api/version")
def app_release_version() -> dict:
    """Application release version + title. Read from the VERSION file at the
    project root. Frontend renders this in the footer and (eventually) compares
    against a remote `latest.json` for update-available signaling."""
    return {
        "app_version": APP_VERSION,
        "title": app.title,
    }


@app.get("/api/release-notes")
def release_notes() -> dict:
    """Return recent installed release notes from the checked-out changelog."""
    try:
        changelog = Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md"
        text = changelog.read_text(encoding="utf-8")
    except OSError:
        return {"current_version": APP_VERSION, "releases": []}

    releases = []
    for section in re.split(r"(?m)^##\s+", text)[1:]:
        lines = section.splitlines()
        if not lines:
            continue
        heading = lines[0].strip()
        match = re.search(r"\d+\.\d+\.\d+", heading)
        if not match:
            continue
        details = []
        for line in lines[1:]:
            value = line.strip()
            if value.startswith("- "):
                details.append(re.sub(r"[`*]", "", value[2:].strip()))
            elif value.startswith("### "):
                details.append(re.sub(r"[`*]", "", value[4:].strip()))
            if len(details) >= 12:
                break
        releases.append({
            "version": match.group(0),
            "heading": heading,
            "details": details,
        })
        if len(releases) >= 8:
            break
    return {"current_version": APP_VERSION, "releases": releases}


@app.get("/api/auto-update/status")
def automatic_update_status() -> dict:
    return auto_updater.public_status()


@app.get("/api/auto-update/readiness")
def automatic_update_readiness() -> dict:
    return auto_updater.readiness_status()


@app.post("/api/auto-update/settings")
def automatic_update_settings(body: AutoUpdateSettingsBody) -> dict:
    try:
        return auto_updater.save_settings(body.model_dump())
    except UpdateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auto-update/check")
def automatic_update_check() -> dict:
    try:
        return auto_updater.trigger_check()
    except UpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/auto-update/update")
def automatic_update_run(body: AutoUpdateRequestBody) -> dict:
    try:
        return auto_updater.trigger_update(after_current=body.after_current)
    except UpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/auto-update/retry")
def automatic_update_retry() -> dict:
    try:
        return auto_updater.retry()
    except UpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/system")
def system_hardware() -> dict:
    """Apple Silicon chip + unified memory snapshot of the host. Frontend uses
    this for the Models tab per-model fit chip and the 'Your Mac' settings
    panel. Mac-only — the underlying sysctl probes return None elsewhere."""
    from . import system_info
    return system_info.system_info()


# ───────────── API: catalog ─────────────

@app.get("/api/catalog")
def get_catalog() -> dict:
    families = {fid: catalog.serialize_family(f) for fid, f in catalog.FAMILIES.items()}
    models = []
    for m in catalog.CATALOG:
        d = catalog.serialize_model(m)
        if m.is_cloud:
            # Cloud models have no HF download. Report a synthetic "cached"
            # state — the frontend gates readiness + the Generate dropdown on
            # state == "cached", so this makes them ready with no download UI.
            d["cache"] = {
                "repo": m.repo,
                "state": "cached",
                "path": None,
                "bytes_complete": 0,
                "bytes_incomplete": 0,
            }
            d["active_download"] = None
        else:
            d["cache"] = cache.status_snapshot(m.repo)
            active = manager.active_for_repo(m.repo)
            d["active_download"] = active.serialize() if active else None
        models.append(d)
    return {"families": families, "models": models}


@app.get("/api/cache/{repo:path}")
def get_cache(repo: str) -> dict:
    return cache.status_snapshot(repo)


# ───────────── API: downloads ─────────────

@app.get("/api/downloads")
def list_downloads() -> dict:
    return {"jobs": [j.serialize() for j in manager.list_jobs()]}


@app.delete("/api/downloads")
def clear_downloads() -> dict:
    """Remove all terminal-state download jobs from memory."""
    return {"cleared": manager.clear_finished()}


@app.post("/api/downloads")
def start_download(body: StartDownloadBody) -> dict:
    if not body.repo or "/" not in body.repo:
        raise HTTPException(status_code=400, detail="repo must be 'owner/name'")
    job = manager.start(body.repo, token=body.token)
    return {"job": job.serialize()}


@app.delete("/api/downloads/{job_id}")
def cancel_download(job_id: str) -> dict:
    ok = manager.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found or already finished")
    job = manager.get(job_id)
    return {"job": job.serialize() if job else None}


@app.get("/api/downloads/stream")
async def stream_downloads():
    """
    Server-Sent Events stream.

    The browser keeps this connection open; we push the full job table every
    second (small JSON). Polling-style — the disk is the source of truth for
    progress, and downloads.py doesn't have native callbacks.
    """
    async def gen():
        try:
            while True:
                payload = {"jobs": [j.serialize() for j in manager.list_jobs()]}
                yield {"event": "snapshot", "data": json.dumps(payload)}
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            return
    return EventSourceResponse(gen())


# ───────────── API: imports ─────────────

@app.get("/api/imports/scan")
def imports_scan() -> dict:
    return {"candidates": [c.serialize() for c in scan_for_candidates()]}


@app.post("/api/imports")
def imports_link(body: ImportBody) -> dict:
    result = import_path(body.source_path, repo=body.repo, mode=body.mode)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "import failed"))
    return result


# ───────────── API: connectivity (where can this server be reached?) ─────────────

def _classify_ip(ip: str) -> str:
    """Heuristic label so the UI can recommend the right address for the use case."""
    if ip.startswith("127."):
        return "loopback"
    # Tailscale assigns CGNAT range 100.64.0.0 – 100.127.255.255
    try:
        octets = [int(x) for x in ip.split(".")]
        if len(octets) == 4 and octets[0] == 100 and 64 <= octets[1] <= 127:
            return "tailscale"
    except (ValueError, IndexError):
        pass
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return "lan"
    return "other"


def _list_local_ips() -> list[dict]:
    """All IPv4 addresses for this machine, classified by likely role."""
    ips: set[str] = set()
    # Hostname resolution — fast and works for most machines.
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except (socket.error, OSError):
        pass
    # Primary outbound IP via the connect-to-public-IP trick. No packets actually
    # leave the machine — UDP connect() just picks the route.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ips.add(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()
    out: list[dict] = []
    for ip in ips:
        if ":" in ip:           # skip ipv6 fragments
            continue
        out.append({"ip": ip, "kind": _classify_ip(ip)})
    # Sort: tailscale → lan → other → loopback, then by IP.
    rank = {"tailscale": 0, "lan": 1, "other": 2, "loopback": 3}
    out.sort(key=lambda d: (rank.get(d["kind"], 9), d["ip"]))
    return out


def _detect_bind_port(default: int = 47868) -> int:
    """
    Find the port uvicorn was actually started with by scanning sys.argv for
    `--port N`. This is the source of truth — request.url.port can lie when
    we're being proxied (e.g. through Pinokio's UI at 42000), but our own
    command-line args don't change.
    """
    args = sys.argv
    try:
        i = args.index("--port")
        return int(args[i + 1])
    except (ValueError, IndexError):
        pass
    env_port = os.environ.get("UVICORN_PORT", "").strip()
    if env_port.isdigit():
        return int(env_port)
    return default


def _detect_bind_host(default: str = "127.0.0.1") -> str:
    args = sys.argv
    try:
        i = args.index("--host")
        return args[i + 1]
    except (ValueError, IndexError):
        pass
    return default


_BIND_PORT = _detect_bind_port()
_BIND_HOST = _detect_bind_host()


@app.get("/api/connectivity")
def connectivity(request: Request) -> dict:
    """
    Return the addresses this server can be reached at, plus Pinokio share-proxy
    config from env. The UI uses this to render a "where can I reach the API?"
    panel in Settings so users don't have to dig through terminal output.

    `bind_port` is what uvicorn was actually launched with (the source of truth).
    `request_port` is whatever URL the *browser* used to reach us — they can
    differ if the request came through a proxy like Pinokio's UI on port 42000.
    The frontend uses `bind_port` when constructing remote-access URLs so it
    doesn't confuse users with the wrong number.
    """
    request_port = request.url.port
    if request_port is None:
        request_port = 443 if request.url.scheme == "https" else 80
    return {
        # Backwards-compat alias — older UI rendered `listen_port`. Now equals
        # the true bind port too.
        "listen_port": _BIND_PORT,
        "bind_port": _BIND_PORT,
        "bind_host": _BIND_HOST,
        "request_port": request_port,
        "scheme": request.url.scheme,
        "client_url": str(request.base_url).rstrip("/"),
        "addresses": _list_local_ips(),
        "share_local_enabled": (os.environ.get("PINOKIO_SHARE_LOCAL", "").strip().lower() == "true"),
        "share_local_port_fixed": os.environ.get("PINOKIO_SHARE_LOCAL_PORT", "").strip() or None,
        "share_passcode_set": bool(os.environ.get("PINOKIO_SHARE_PASSCODE", "").strip()),
        "pinokio_ui_port": 42000,   # Pinokio's own UI default; not detected, just informational
    }


# ───────────── API: settings ─────────────

@app.get("/api/settings")
def get_settings_endpoint() -> dict:
    """Returns a caller-safe (masked) view of the current settings."""
    return app_settings.serialize_public()


@app.post("/api/settings")
def update_settings_endpoint(body: SettingsBody) -> dict:
    """Update settings. For any field, passing "" clears it; omitting leaves it
    unchanged."""
    if body.hf_token is not None:
        app_settings.set_hf_token(body.hf_token)
    for key in ("cloudflare_account_id", "cloudflare_api_token", "together_api_key",
                "gemini_api_key", "nebius_api_key"):
        val = getattr(body, key)
        if val is not None:
            app_settings.set_value(key, val.strip())
    return app_settings.serialize_public()


@app.post("/api/settings/test-hf-token")
def test_hf_token_endpoint(body: TokenTestBody) -> dict:
    """
    Validate a Hugging Face token by calling whoami(). If body.hf_token is
    omitted/empty, tests the saved token instead. Returns the user's display
    info on success, or 400 with the upstream error message on failure.
    """
    token = (body.hf_token or "").strip() or app_settings.get_hf_token()
    if not token:
        raise HTTPException(status_code=400, detail="No token provided and none saved in settings.")
    try:
        from huggingface_hub import HfApi  # imported here so it's lazy
        info = HfApi().whoami(token=token)
        return {
            "ok": True,
            "name": info.get("name") or info.get("fullname") or info.get("email"),
            "type": info.get("type"),
            "orgs": [o.get("name") for o in (info.get("orgs") or []) if o.get("name")],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token validation failed: {e}")


# ───────────── API: reveal in OS file manager ─────────────

_APP_ROOT = Path(__file__).resolve().parent.parent      # .../app
_LAUNCHER_ROOT = _APP_ROOT.parent                       # .../imagestudio-mac

# Whitelist of root paths we'll open. Anything under these is fair game;
# anything outside is rejected so this endpoint can't be turned into an
# arbitrary-path opener from a malicious page on the LAN.
def _reveal_allowed_roots() -> list[Path]:
    return [
        cache.hf_home().resolve(),
        (_APP_ROOT / "output").resolve(),
        (_APP_ROOT / "lora").resolve(),
        _LAUNCHER_ROOT.resolve(),
    ]


def _is_path_allowed(target: Path) -> bool:
    target = target.resolve()
    for root in _reveal_allowed_roots():
        try:
            target.relative_to(root)
            return True
        except ValueError:
            continue
    return False


@app.post("/api/reveal")
def reveal_path(body: RevealBody) -> dict:
    """
    Open the given path in the OS file manager. macOS only for now
    (Finder via `open -R` for files, `open` for directories).
    """
    if sys.platform != "darwin":
        raise HTTPException(status_code=501, detail="Reveal is only implemented on macOS.")
    if not body.path:
        raise HTTPException(status_code=400, detail="path is required")
    target = Path(body.path).expanduser()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"path does not exist: {target}")
    if not _is_path_allowed(target):
        raise HTTPException(
            status_code=403,
            detail="path is outside the allowed roots (HF cache, app/output, app/lora, launcher folder)"
        )
    # -R reveals (selects) the item in Finder; if `target` is a directory it
    # opens that directory directly.
    args = ["open", "-R", str(target.resolve())] if target.is_file() else ["open", str(target.resolve())]
    try:
        subprocess.Popen(args)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="`open` command not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reveal failed: {e}")
    return {"ok": True, "opened": str(target.resolve())}


# ───────────── API: loras ─────────────

@app.get("/api/loras")
def list_loras_endpoint() -> dict:
    return {"loras": loras.list_loras()}


# ───────────── API: generation ─────────────

@app.get("/api/generate/availability")
def generation_availability() -> dict:
    return gen_manager.availability()


@app.get("/api/generate/diagnostics")
def generation_diagnostics() -> dict:
    """Per-package + per-engine health check. Surfaced in the Generate tab as a
    checklist so users see what's installed and which engines are ready.
    Includes `app_version` for convenience so the frontend doesn't need an
    extra round-trip."""
    data = gen_diagnostics()
    data["app_version"] = APP_VERSION
    return data


@app.get("/api/generate/install/status")
def generation_install_status() -> dict:
    """Return progress for the fixed generation-dependency installer."""
    return generation_installer.status()


@app.post("/api/generate/install")
def install_generation_dependencies(request: Request) -> dict:
    """Install the checked-in generation requirements from the Web UI.

    The endpoint deliberately accepts no package names or commands. A basic
    same-origin check prevents unrelated websites from triggering maintenance
    against a LAN-accessible Image Studio instance.
    """
    origin = request.headers.get("origin")
    host = request.headers.get("host")
    if origin and host and urlparse(origin).netloc != host:
        raise HTTPException(status_code=403, detail="Maintenance actions require the Image Studio origin.")
    return generation_installer.start()


@app.post("/api/generate/txt2img")
def start_txt2img(body: Txt2ImgBody) -> dict:
    _validate_generation_controls(
        prompt=body.prompt, width=body.width, height=body.height,
        steps=body.steps, guidance=body.guidance, seed=body.seed,
        quantize=body.quantize, lora_names=body.lora_names,
        lora_scales=body.lora_scales,
    )
    model = catalog.get_model(body.repo)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown repo: {body.repo}")
    if not model.runtime_compatible:
        raise HTTPException(status_code=409, detail=model.runtime_note or "This model conversion is not supported by the current worker.")
    # Cloud models are an HTTP call — they need neither the local mflux engine
    # nor a Hugging Face download, so skip both gates for them.
    if not model.is_cloud:
        if not gen_manager.is_available():
            raise HTTPException(
                status_code=503,
                detail="Generation engine not installed. Run the 'Install Generation' menu item.",
            )
        if cache.cache_state(body.repo) != "cached":
            raise HTTPException(
                status_code=409,
                detail=f"Model {body.repo} is not fully cached. Download it from the Models tab first.",
            )

    # Resolve LoRA names to absolute paths so the worker doesn't need to redo it.
    lora_paths: list[str] = []
    for name in body.lora_names:
        path = loras.resolve_lora_path(name)
        if path is None:
            raise HTTPException(status_code=400, detail=f"LoRA not found: {name}")
        lora_paths.append(str(path))

    params = body.model_dump()
    params["lora_paths"] = lora_paths
    job = gen_manager.start_txt2img(params)
    return {"job": job.serialize()}


@app.post("/api/generate/img2img")
async def start_img2img(
    image: UploadFile = File(...),
    repo: str = Form(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int = Form(1024),
    height: int = Form(1024),
    steps: int = Form(4),
    guidance: float = Form(3.5),
    seed: Optional[int] = Form(None),
    image_strength: float = Form(0.6),
    quantize: Optional[int] = Form(None),
    lora_names: str = Form(""),          # comma-separated names
    lora_scales: str = Form(""),         # comma-separated floats
) -> dict:
    """
    Image-to-image generation. Accepts multipart/form-data: an `image` file
    plus the same JSON-ish param set as txt2img, with one extra:
    `image_strength` (0.0–1.0, how aggressively to denoise the input).
    """
    if not gen_manager.is_available():
        raise HTTPException(
            status_code=503,
            detail="Generation engine not installed. Run the 'Install Generation' menu item.",
        )
    name_list, scale_list = _parse_lora_fields(lora_names, lora_scales)
    _validate_generation_controls(
        prompt=prompt, width=width, height=height, steps=steps,
        guidance=guidance, seed=seed, quantize=quantize,
        lora_names=name_list, lora_scales=scale_list,
    )
    _validate_image_strength(image_strength)
    model = catalog.get_model(repo)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown repo: {repo}")
    if not model.runtime_compatible:
        raise HTTPException(status_code=409, detail=model.runtime_note or "This model conversion is not supported by the current worker.")
    if cache.cache_state(repo) != "cached":
        raise HTTPException(status_code=409,
            detail=f"Model {repo} is not fully cached. Download it from the Models tab first.")

    # Resolve LoRAs before writing the upload, so rejected requests leave no
    # orphaned temporary file behind.
    lora_paths: list[str] = []
    for n in name_list:
        path = loras.resolve_lora_path(n)
        if path is None:
            raise HTTPException(status_code=400, detail=f"LoRA not found: {n}")
        lora_paths.append(str(path))
    saved_image = await _save_uploaded_image(image)

    params = {
        "repo": repo,
        "prompt": prompt.strip(),
        "negative_prompt": negative_prompt.strip(),
        "width": int(width),
        "height": int(height),
        "steps": int(steps),
        "guidance": float(guidance),
        "seed": seed,
        "image_strength": max(0.0, min(1.0, float(image_strength))),
        "image_path": str(saved_image.resolve()),
        "quantize": quantize,
        "lora_names": name_list,
        "lora_scales": scale_list,
        "lora_paths": lora_paths,
    }
    job = gen_manager.start_img2img(params)
    return {"job": job.serialize()}


@app.post("/api/generate/edit")
async def start_edit(
    image: UploadFile = File(...),
    repo: str = Form(...),
    prompt: str = Form(...),
    width: int = Form(1024),
    height: int = Form(1024),
    steps: int = Form(4),
    guidance: float = Form(1.0),     # klein-edit defaults to 1.0 (distilled)
    seed: Optional[int] = Form(None),
    image_strength: float = Form(0.85),   # higher than img2img — edit preserves more
    quantize: Optional[int] = Form(None),
    lora_names: str = Form(""),
    lora_scales: str = Form(""),
) -> dict:
    """
    Instruction-based image edit. Same multipart shape as img2img but the
    backend dispatches to a model-specific edit pipeline (Flux2KleinEdit /
    Kontext / Qwen) based on the chosen model's family.
    """
    if not gen_manager.is_available():
        raise HTTPException(status_code=503,
            detail="Generation engine not installed. Run 'Install Generation' first.")
    name_list, scale_list = _parse_lora_fields(lora_names, lora_scales)
    _validate_generation_controls(
        prompt=prompt, width=width, height=height, steps=steps,
        guidance=guidance, seed=seed, quantize=quantize,
        lora_names=name_list, lora_scales=scale_list,
    )
    _validate_image_strength(image_strength)
    model = catalog.get_model(repo)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown repo: {repo}")
    if not model.runtime_compatible:
        raise HTTPException(status_code=409, detail=model.runtime_note or "This model conversion is not supported by the current worker.")
    if "edit" not in (model.capabilities or ()):
        raise HTTPException(status_code=400,
            detail=f"Model {repo} does not support edit mode. Pick an edit-capable model.")
    if cache.cache_state(repo) != "cached":
        raise HTTPException(status_code=409,
            detail=f"Model {repo} is not fully cached. Download it from the Models tab first.")

    # Resolve LoRAs before writing the upload, so rejected requests leave no
    # orphaned temporary file behind.
    lora_paths: list[str] = []
    for n in name_list:
        path = loras.resolve_lora_path(n)
        if path is None:
            raise HTTPException(status_code=400, detail=f"LoRA not found: {n}")
        lora_paths.append(str(path))
    saved_image = await _save_uploaded_image(image)

    params = {
        "repo": repo,
        "prompt": prompt.strip(),
        "width": int(width),
        "height": int(height),
        "steps": int(steps),
        "guidance": float(guidance),
        "seed": seed,
        "image_strength": max(0.0, min(1.0, float(image_strength))),
        "image_paths": [str(saved_image.resolve())],
        "image_path": str(saved_image.resolve()),   # convenience alias for variants that use singular
        "quantize": quantize,
        "lora_names": name_list,
        "lora_scales": scale_list,
        "lora_paths": lora_paths,
    }
    job = gen_manager.start_edit(params)
    return {"job": job.serialize()}


@app.get("/api/generate/jobs")
def list_generation_jobs() -> dict:
    return {"jobs": [j.serialize() for j in gen_manager.list_jobs()]}


@app.delete("/api/generate/jobs")
def clear_generation_history() -> dict:
    return {"cleared": gen_manager.clear_history()}


@app.get("/api/generate/jobs/{job_id}")
def get_generation_job(job_id: str) -> dict:
    job = gen_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job": job.serialize()}


@app.get("/api/generate/jobs/{job_id}/image")
def get_generation_image(job_id: str) -> FileResponse:
    job = gen_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if not job.output_path:
        raise HTTPException(status_code=425, detail="image not ready yet")
    return FileResponse(job.output_path, media_type="image/png")


@app.delete("/api/generate/jobs/{job_id}")
def cancel_generation_job(job_id: str) -> dict:
    ok = gen_manager.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found or already finished")
    job = gen_manager.get(job_id)
    return {"job": job.serialize() if job else None}


@app.delete("/api/generate/history/{job_id}")
def delete_one_generation(job_id: str) -> dict:
    """Delete a single FINISHED generation: remove it from history and delete its
    PNG from disk. (DELETE .../jobs/{id} only cancels active jobs.)"""
    if not gen_manager.delete_job(job_id):
        raise HTTPException(status_code=404, detail="job not found")
    return {"deleted": job_id}


@app.get("/api/output/stats")
def output_stats() -> dict:
    """Size + count of generated PNGs on disk, for the disk-usage display."""
    return gen_manager.output_stats()


@app.post("/api/output/prune")
def prune_outputs(body: PruneBody) -> dict:
    """Reclaim disk: keep the newest N (keep_last) OR delete files older than
    older_than_days. History entries for deleted files are trimmed too."""
    return gen_manager.prune_outputs(keep_last=body.keep_last, older_than_days=body.older_than_days)


@app.get("/api/storage-policy")
def get_storage_policy() -> dict:
    return storage_policy.status(gen_manager, OUTPUT_DIR)


@app.put("/api/storage-policy")
def put_storage_policy(body: dict) -> dict:
    storage_policy.save(
        body.get("enabled"), body.get("retention_days"), body.get("max_gb"))
    return storage_policy.status(gen_manager, OUTPUT_DIR)


@app.post("/api/storage-policy/cleanup")
def cleanup_storage_policy(body: dict | None = None) -> dict:
    body = body or {}
    target = body.get("target_bytes")
    if target is not None and (not isinstance(target, int) or target < 0):
        raise HTTPException(400, "target_bytes must be a non-negative integer")
    return storage_policy.enforce(gen_manager, OUTPUT_DIR, target)


@app.get("/api/generate/stream")
async def stream_generation():
    async def gen():
        try:
            while True:
                payload = {"jobs": [j.serialize() for j in gen_manager.list_jobs()]}
                yield {"event": "snapshot", "data": json.dumps(payload)}
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            return
    return EventSourceResponse(gen())


# ───────────── static frontend ─────────────

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIR), html=False),
        name="assets",
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
