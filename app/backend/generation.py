"""
Generation manager.

Wraps mflux's FLUX pipelines in a thread-per-job pattern that mirrors the
download manager. The mflux import is wrapped in try/except so the server
still runs (catalog / download features only) when mflux isn't installed
yet — the generation endpoints just return 503 in that case.

Wired families (workers exist): flux2-klein, flux1-schnell, flux1-dev,
flux1-kontext, qwen-image, qwen-edit, fibo, z-image. flux2-dev is still
unwired (waiting on a mflux release that adds the Flux2Dev class).

Output images land in `app/output/<job_id>.png`.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import catalog, cache, loras


# ───────────── module-level locks / paths ─────────────
# mflux loads the FLUX model into a process-wide MLX state that isn't
# thread-safe. Concurrent generations OOM the GPU and produce corrupted
# images. Serialize ALL generations behind this lock so a batch submission
# from the UI just queues up in order.
_GEN_LOCK = threading.Lock()

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HISTORY_FILE = OUTPUT_DIR / ".history.json"
HISTORY_MAX = 200   # keep last N completed jobs; oldest are trimmed off disk


# ───────────── soft import of mflux ─────────────

MFLUX_AVAILABLE = False
MFLUX_IMPORT_ERROR: Optional[str] = None
try:
    # We resolve specific symbols lazily inside the worker thread to keep
    # server start-up fast and so the import error message is meaningful.
    import mflux  # noqa: F401
    MFLUX_AVAILABLE = True
except Exception as e:
    MFLUX_IMPORT_ERROR = f"{type(e).__name__}: {e}"


# ───────────── diagnostics ─────────────

# Per-package metadata for the "what's installed" checklist surfaced in the UI.
# Each entry is (display_name, role, import_name?) — when the package's display
# name differs from its Python import name (e.g. Pillow → PIL), the third
# element specifies the importable module.
_PACKAGE_CHECKLIST = [
    ("mflux",           "FLUX-on-MLX inference wrapper (engine core)"),
    ("mlx",             "Apple Silicon ML framework (pulled by mflux)"),
    ("Pillow",          "Image I/O (PIL fork)", "PIL"),
    ("numpy",           "Tensor numerics"),
    ("transformers",    "Text encoder for FLUX prompts"),
    ("safetensors",     "Weight file loading"),
    ("sentencepiece",   "Tokenizer backend for FLUX/Qwen text encoders"),
    ("huggingface_hub", "Model registry + cache access"),
    # diffusers engine (v1.9.0) — second local backend (PyTorch/MPS).
    ("torch",           "PyTorch w/ MPS (diffusers engine)"),
    ("diffusers",       "HuggingFace diffusers (2nd local engine)"),
    ("accelerate",      "diffusers model loading helper"),
]

# Per-engine dependency requirements. Family ids must match the catalog.
_ENGINE_REQUIREMENTS = {
    "flux2-klein":   ["mflux", "mlx", "Pillow", "numpy"],
    "flux2-dev":     ["mflux", "mlx", "Pillow", "numpy"],
    "flux1-schnell": ["mflux", "mlx", "Pillow", "numpy"],
    "flux1-dev":     ["mflux", "mlx", "Pillow", "numpy"],
    "flux1-krea":    ["mflux", "mlx", "Pillow", "numpy"],
    "seedvr2":       ["mflux", "mlx", "Pillow", "numpy"],
    # diffusers-engine families (v1.9.0+) — PyTorch/MPS, not mflux/MLX.
    "sd35":          ["torch", "diffusers", "Pillow", "numpy"],
    "sana":          ["torch", "diffusers", "Pillow", "numpy"],
    "pixart-sigma":  ["torch", "diffusers", "Pillow", "numpy"],
    "lumina2":       ["torch", "diffusers", "Pillow", "numpy"],
    "auraflow":      ["torch", "diffusers", "Pillow", "numpy"],
    # roadmap engines — declared so the UI shows what they'll need
    "flux1-kontext": ["mflux", "mlx", "Pillow", "numpy"],
    "qwen-edit":     ["transformers", "mlx", "Pillow", "numpy"],
    # MLX-community ecosystem additions (Phase D). All ride mflux today; if a
    # future worker uses a different inference library, update this list and
    # _WIRED_FAMILIES together.
    "flux1-lite":    ["mflux", "mlx", "Pillow", "numpy"],
    "shuttle":       ["mflux", "mlx", "Pillow", "numpy"],
    "hidream":       ["mflux", "mlx", "Pillow", "numpy"],
    "qwen-image":    ["transformers", "mlx", "Pillow", "numpy"],
}

# Which engines have a fully-working worker. Keep in sync with the branches in
# `_dispatch_txt2img` + `_dispatch_edit` in this file. The audit_truth.py
# script verifies this set against actual dispatch coverage on every release.
#
# Wired families (workers exist):
# - flux2-klein   ← _generate_flux2_klein + _generate_klein_edit
# - flux1-schnell ← _generate_flux1 (mflux's Flux1 with ModelConfig.schnell())
# - flux1-dev     ← _generate_flux1 (mflux's Flux1 with ModelConfig.dev())
# - flux1-krea    ← _generate_flux1 (mflux's Flux1 with ModelConfig.krea_dev()) — v1.5.0
# - flux1-kontext ← _generate_kontext (mflux's Flux1Kontext)
# - qwen-image    ← _generate_qwen_image (mflux's QwenImage) — v1.3.0
# - qwen-edit     ← _generate_qwen_edit (mflux's QwenImageEdit) — v1.3.0
# - fibo          ← _generate_fibo (mflux's FIBO + FIBOEdit) — v1.3.0
# - z-image       ← _generate_z_image (mflux's ZImage) — v1.3.0
# - seedvr2       ← _generate_seedvr2 (mflux's SeedVR2 upscaler; img2img tab) — v1.7.0
#
# NOT wired (no mflux inference class):
# - flux2-dev — mflux has no Flux2Dev class. Would need a future mflux release.
_WIRED_FAMILIES = {
    "flux2-klein", "flux1-schnell", "flux1-dev", "flux1-krea", "flux1-kontext",
    "qwen-image", "qwen-edit", "fibo", "z-image", "seedvr2",
}

# Families that run on the diffusers engine (PyTorch/MPS) instead of mflux. They
# don't go through mflux family dispatch (routed by `engine` in _dispatch_txt2img),
# so they're tracked separately and excluded from the mflux truth audit. Listed
# here so diagnostics() can mark them "wired" once torch/diffusers are installed.
_DIFFUSERS_FAMILIES = {"sd35", "sana", "pixart-sigma", "lumina2", "auraflow"}


def _probe_package(display_name: str, import_name: Optional[str] = None) -> dict:
    """Try to import a package, report its version + status. `import_name`
    overrides the importable module when it differs from the display name
    (e.g. Pillow → PIL)."""
    target = import_name or display_name
    try:
        import importlib
        mod = importlib.import_module(target)
        version = getattr(mod, "__version__", None)
        return {"installed": True, "version": version, "error": None}
    except Exception as e:
        return {"installed": False, "version": None, "error": f"{type(e).__name__}: {e}"}


def diagnostics() -> dict:
    """Per-package + per-engine health check. The frontend renders this as a
    checklist in the Generate tab so users see what's installed and which
    engines are ready BEFORE submitting a generation."""
    pkg_results = []
    pkg_status: dict[str, bool] = {}
    for entry in _PACKAGE_CHECKLIST:
        if len(entry) == 3:
            display_name, role, import_name = entry
        else:
            display_name, role = entry
            import_name = None
        probe = _probe_package(display_name, import_name)
        pkg_results.append({"package": display_name, "role": role, **probe})
        pkg_status[display_name] = probe["installed"]

    engine_results = []
    for family, requires in _ENGINE_REQUIREMENTS.items():
        missing = [p for p in requires if not pkg_status.get(p)]
        deps_ok = not missing
        wired = family in _WIRED_FAMILIES or family in _DIFFUSERS_FAMILIES
        engine_results.append({
            "family": family,
            "requires": requires,
            "missing": missing,
            "deps_ok": deps_ok,
            "wired": wired,
            "ready": deps_ok and wired,
        })

    return {
        # ImageStudio uses MLX, not a CUDA/MPS device picker — surface MLX
        # availability instead so the UI still shows something useful.
        "device": "mlx" if MFLUX_AVAILABLE else None,
        "packages": pkg_results,
        "engines": engine_results,
        "any_missing": any(not p["installed"] for p in pkg_results),
        "ready_count": sum(1 for e in engine_results if e["ready"]),
        "total_engines": len(engine_results),
    }


# ───────────── aspect-ratio presets ─────────────
# Sizes are chosen to be multiples of 16 (FLUX prefers /16) at ~1MP each
# so latency is roughly comparable across ratios.

ASPECT_PRESETS: dict[str, tuple[int, int]] = {
    "1:1":  (1024, 1024),
    "16:9": (1344, 768),
    "9:16": (768, 1344),
    "4:3":  (1152, 864),
    "3:4":  (864, 1152),
    "21:9": (1536, 640),
    "3:2":  (1216, 832),
    "2:3":  (832, 1216),
}


def aspect_options() -> list[dict]:
    return [
        {"ratio": ratio, "width": w, "height": h}
        for ratio, (w, h) in ASPECT_PRESETS.items()
    ]


# ───────────── job model ─────────────

@dataclass
class GenerationJob:
    job_id: str
    mode: str                            # "txt2img" (only one supported for now)
    params: dict                         # echoed back so the UI can show settings
    state: str = "queued"                # queued | running | done | error | cancelled
    progress: float = 0.0                # 0.0 - 1.0; only updates on step boundaries
    current_step: int = 0
    total_steps: int = 0
    output_path: Optional[str] = None
    resolved_seed: Optional[int] = None  # the actual seed used (for reproducibility,
                                         # populated even when the user passed -1)
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    thread: Optional[threading.Thread] = None

    def serialize(self) -> dict:
        duration = None
        if self.started_at is not None:
            end = self.finished_at if self.finished_at is not None else time.time()
            duration = max(0.0, end - self.started_at)
        return {
            "id": self.job_id,
            "mode": self.mode,
            "state": self.state,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "params": self.params,
            "output_path": self.output_path,
            "output_url": f"/api/generate/jobs/{self.job_id}/image" if self.output_path else None,
            "resolved_seed": self.resolved_seed,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": duration,
        }


# ───────────── generation manager ─────────────

class GenerationManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, GenerationJob] = {}
        self._load_history()

    # ----- public API -----

    def is_available(self) -> bool:
        return MFLUX_AVAILABLE

    def availability(self) -> dict:
        return {
            "available": MFLUX_AVAILABLE,
            "error": MFLUX_IMPORT_ERROR,
            "presets": aspect_options(),
        }

    def list_jobs(self) -> list[GenerationJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> Optional[GenerationJob]:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        """
        Cancel a job. Behavior depends on state:

        - **queued**: the worker thread is blocked on `_GEN_LOCK` waiting for
          the running job to finish, so it CAN'T check the cancel_event yet.
          We immediately flip state → "cancelled" so the UI updates within the
          next SSE snapshot (~1 sec). When the worker eventually acquires the
          lock, it sees cancel_event is set and exits cleanly without
          overwriting our state.

        - **running**: mflux's generate_image() is a blocking call that doesn't
          honor mid-flight cancellation. We can only set cancel_event so the
          worker discards the result AFTER generation completes. The UI keeps
          showing "running" until that finishes — a frontend toast tells the
          user about this upstream limitation.
        """
        job = self._jobs.get(job_id)
        if job is None or job.state in ("done", "error", "cancelled"):
            return False
        # Always signal — the worker checks at multiple points.
        job.cancel_event.set()
        # IMMEDIATE state flip for queued jobs so the UI reacts instantly.
        if job.state == "queued":
            job.state = "cancelled"
            job.finished_at = time.time()
            try:
                self._persist()
            except Exception:
                pass
        return True

    def start_txt2img(self, params: dict) -> GenerationJob:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        job = GenerationJob(
            job_id=uuid.uuid4().hex[:12],
            mode="txt2img",
            params=params,
            total_steps=int(params.get("steps", 4)),
        )
        self._jobs[job.job_id] = job
        job.thread = threading.Thread(
            target=self._run_txt2img,
            args=(job,),
            name=f"gen-{job.job_id}",
            daemon=True,
        )
        job.thread.start()
        return job

    def start_img2img(self, params: dict) -> GenerationJob:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        job = GenerationJob(
            job_id=uuid.uuid4().hex[:12],
            mode="img2img",
            params=params,
            total_steps=int(params.get("steps", 4)),
        )
        self._jobs[job.job_id] = job
        # Same worker as txt2img — the Flux2Klein.generate_image call below
        # reads `image_path` and `image_strength` from params when present.
        job.thread = threading.Thread(
            target=self._run_txt2img,
            args=(job,),
            name=f"gen-{job.job_id}",
            daemon=True,
        )
        job.thread.start()
        return job

    def start_edit(self, params: dict) -> GenerationJob:
        """
        Instruction-based image edit. Dispatches to the right mflux variant
        based on the model's family (klein → Flux2KleinEdit, etc.). Reuses
        the txt2img worker scaffolding — same locking, persistence, SSE.
        """
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        job = GenerationJob(
            job_id=uuid.uuid4().hex[:12],
            mode="edit",
            params=params,
            total_steps=int(params.get("steps", 4)),
        )
        self._jobs[job.job_id] = job
        job.thread = threading.Thread(
            target=self._run_edit,
            args=(job,),
            name=f"gen-{job.job_id}",
            daemon=True,
        )
        job.thread.start()
        return job

    def clear_history(self) -> int:
        """Remove all terminal-state jobs from memory and disk. Returns count removed."""
        with self._lock:
            terminal = [jid for jid, j in self._jobs.items()
                        if j.state in ("done", "error", "cancelled")]
            for jid in terminal:
                self._jobs.pop(jid, None)
        self._persist()
        return len(terminal)

    # ----- persistence -----

    def _persist(self) -> None:
        """
        Write the last HISTORY_MAX completed jobs to disk so they survive a
        server restart. Uses atomic rename so a crash mid-write can't corrupt
        the history file.
        """
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            # Only persist terminal-state jobs (running ones get re-discovered
            # next session if they survived, but threads are gone after restart).
            terminal = [j for j in self._jobs.values()
                        if j.state in ("done", "error", "cancelled")]
            terminal.sort(key=lambda j: j.finished_at or 0, reverse=True)
            terminal = terminal[:HISTORY_MAX]
            payload = {"jobs": [self._to_disk(j) for j in terminal]}
            tmp = HISTORY_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, default=str))
            os.replace(tmp, HISTORY_FILE)
        except Exception as e:
            print(f"[gen] persist failed: {e}", file=sys.stderr, flush=True)

    def _load_history(self) -> None:
        if not HISTORY_FILE.exists():
            return
        try:
            payload = json.loads(HISTORY_FILE.read_text())
            for raw in payload.get("jobs", []):
                job = self._from_disk(raw)
                if job is not None:
                    self._jobs[job.job_id] = job
            print(f"[gen] loaded {len(self._jobs)} jobs from history", flush=True)
        except Exception as e:
            print(f"[gen] load history failed: {e}", file=sys.stderr, flush=True)

    @staticmethod
    def _to_disk(job: GenerationJob) -> dict:
        return {
            "job_id": job.job_id,
            "mode": job.mode,
            "state": job.state,
            "progress": job.progress,
            "current_step": job.current_step,
            "total_steps": job.total_steps,
            "params": job.params,
            "output_path": job.output_path,
            "resolved_seed": job.resolved_seed,
            "error": job.error,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }

    @staticmethod
    def _from_disk(raw: dict) -> Optional["GenerationJob"]:
        try:
            output_path = raw.get("output_path")
            # If the PNG was deleted out-of-band, drop the output_url so the UI
            # doesn't try to fetch a 404.
            if output_path and not Path(output_path).exists():
                output_path = None
            return GenerationJob(
                job_id=raw["job_id"],
                mode=raw.get("mode", "txt2img"),
                params=raw.get("params") or {},
                state=raw.get("state", "done"),
                progress=raw.get("progress", 1.0),
                current_step=raw.get("current_step", 0),
                total_steps=raw.get("total_steps", 0),
                output_path=output_path,
                resolved_seed=raw.get("resolved_seed"),
                error=raw.get("error"),
                started_at=raw.get("started_at"),
                finished_at=raw.get("finished_at"),
            )
        except Exception:
            return None

    # ----- worker -----

    def _run_edit(self, job: GenerationJob) -> None:
        """
        Edit worker — mirrors _run_txt2img's locking/persist/error pattern
        but dispatches to the right mflux variant class based on the model
        family. Klein family uses Flux2KleinEdit; Kontext / Qwen / Fibo are
        stubbed for future implementation but produce a clear error so the
        user knows the catalog entry exists but the worker hasn't shipped yet.

        NOTE: don't re-set `job.state = "queued"` here. The dataclass default
        already initialised it to "queued", and `cancel()` may legitimately
        have flipped it to "cancelled" between submit_job() and this thread
        being scheduled. Re-asserting "queued" outside the lock clobbers that
        cancel decision — the cancel_event flag still survives, but the UI
        would see the job pop back to "queued" until the worker eventually
        acquired the lock (potentially minutes later).
        """
        with _GEN_LOCK:
            if job.cancel_event.is_set():
                job.state = "cancelled"
                job.finished_at = time.time()
                self._persist()
                return

            job.state = "running"
            job.started_at = time.time()
            print(f"[gen] starting edit {job.job_id}: {job.params}", flush=True)

            if not MFLUX_AVAILABLE:
                job.state = "error"
                job.error = f"mflux not installed: {MFLUX_IMPORT_ERROR}"
                job.finished_at = time.time()
                self._persist()
                return

            try:
                output_path = OUTPUT_DIR / f"{job.job_id}.png"
                self._dispatch_edit(job, output_path)
                if job.cancel_event.is_set():
                    job.state = "cancelled"
                else:
                    job.output_path = str(output_path.resolve())
                    job.progress = 1.0
                    job.state = "done"
                    print(f"[gen] edit done {job.job_id} → {output_path}", flush=True)
            except Exception as e:
                if job.cancel_event.is_set():
                    job.state = "cancelled"
                else:
                    job.state = "error"
                    job.error = f"{type(e).__name__}: {e}"
                    print(f"[gen] edit error {job.job_id}: {job.error}", file=sys.stderr, flush=True)
                    traceback.print_exc()
            finally:
                job.finished_at = time.time()
                self._persist()

    def _dispatch_edit(self, job: GenerationJob, output_path: Path) -> None:
        """
        Pick the right mflux Edit class for the chosen model. Currently only
        the klein family has a working implementation; other edit-capable
        models in the catalog raise NotImplementedError with a clear message.
        """
        params = job.params
        repo = params["repo"]
        model = catalog.get_model(repo)
        if model is None:
            raise ValueError(f"Repo {repo} is not in the catalog")
        if cache.cache_state(repo) != "cached":
            raise ValueError(f"Model {repo} is not fully cached locally — download it first")
        if "edit" not in (model.capabilities or ()):
            raise ValueError(f"Model {repo} does not support edit mode")

        family = model.family
        if family == "flux2-klein":
            self._generate_klein_edit(job, output_path)
        elif family == "flux1-kontext":
            self._generate_kontext(job, output_path)
        elif family == "qwen-edit":
            self._generate_qwen_edit(job, output_path)
        elif family == "fibo":
            # FIBO Edit + FIBO Edit RMBG share the same edit worker, the model
            # config differentiates which behavior we get. Plain FIBO/FIBO Lite
            # in edit mode is unusual but technically the same class accepts it.
            self._generate_fibo_edit(job, model, output_path)
        else:
            raise NotImplementedError(
                f"No edit worker implemented for model family '{family}'."
            )

    def _generate_klein_edit(self, job: GenerationJob, output_path: Path) -> None:
        """Run Flux2KleinEdit. Mirrors _generate_flux2_klein but uses the Edit class."""
        from mflux.models.flux2.variants.edit.flux2_klein_edit import Flux2KleinEdit  # type: ignore

        params = job.params
        repo = params["repo"]
        quantize = params.get("quantize")
        lora_paths = params.get("lora_paths") or None
        lora_scales = params.get("lora_scales") or None

        flux = Flux2KleinEdit(
            model_path=repo,
            quantize=quantize,
            lora_paths=lora_paths,
            lora_scales=lora_scales,
            model_config=None,    # let mflux pick from the repo name
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        # Klein Edit expects `image_paths` (plural list) — supports combining
        # multiple inputs ("place this product on this background"). We pass a
        # single-element list for the common case.
        image_paths = params.get("image_paths") or []
        if not image_paths and params.get("image_path"):
            image_paths = [params["image_path"]]
        if not image_paths:
            raise ValueError("At least one input image is required for edit mode")

        result = flux.generate_image(
            seed=int(seed),
            prompt=params["prompt"],
            num_inference_steps=int(params.get("steps", 4)),
            height=int(params.get("height", 1024)),
            width=int(params.get("width", 1024)),
            guidance=float(params.get("guidance", 1.0)),
            image_paths=image_paths,
            image_strength=float(params.get("image_strength", 0.85)),
        )
        if not hasattr(result, "save"):
            raise RuntimeError("mflux returned an unexpected result; expected GeneratedImage.")
        result.save(str(output_path), overwrite=True)

    def _generate_kontext(self, job: GenerationJob, output_path: Path) -> None:
        """
        Run mflux's FLUX.1 Kontext for instruction-style edits — "make the sky
        red", "add sunglasses", "swap background to a beach", etc. Subject and
        composition are preserved; only the requested change is applied.

        Requires the user-supplied edit prompt + a reference image
        (params['image_path']). For pure txt2img, FLUX.1 dev is the better tool.
        """
        from mflux.models.flux.variants.kontext.flux_kontext import Flux1Kontext  # type: ignore

        params = job.params
        repo = params["repo"]
        if not params.get("image_path"):
            raise ValueError(
                "FLUX.1 Kontext is an instruction-edit model — it needs an "
                "input image. Use the Image Edit tab and attach a reference."
            )

        quantize = params.get("quantize")
        lora_paths = params.get("lora_paths") or None
        lora_scales = params.get("lora_scales") or None

        print(f"[gen] kontext repo={repo} prompt_len={len(params['prompt'])}", flush=True)

        flux = Flux1Kontext(
            model_path=repo,
            quantize=quantize,
            lora_paths=lora_paths,
            lora_scales=lora_scales,
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            # Kontext default in mflux is 4 steps + guidance 4.0; expose to user.
            "num_inference_steps": int(params.get("steps", 4)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", 4.0)),
            "image_path": params["image_path"],
        }
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])

        result = flux.generate_image(**gen_kwargs)
        if not hasattr(result, "save"):
            raise RuntimeError(
                "mflux Flux1Kontext returned an unexpected result; expected GeneratedImage."
            )
        result.save(str(output_path), overwrite=True)

    def _run_txt2img(self, job: GenerationJob) -> None:
        # Serialize all generation across the process so concurrent submissions
        # queue up rather than OOMing the GPU.
        #
        # NOTE: don't re-set `job.state = "queued"` here. The dataclass default
        # already initialised it to "queued", and `cancel()` may legitimately
        # have flipped it to "cancelled" between submit_job() and this thread
        # being scheduled. Re-asserting "queued" outside the lock clobbers that
        # cancel decision — the cancel_event flag still survives, but the UI
        # would see the job pop back to "queued" until the worker eventually
        # acquired the lock (potentially minutes later).
        with _GEN_LOCK:
            if job.cancel_event.is_set():
                job.state = "cancelled"
                job.finished_at = time.time()
                self._persist()
                return

            job.state = "running"
            job.started_at = time.time()
            print(f"[gen] starting {job.job_id}: {job.params}", flush=True)

            # Cloud models don't need mflux — they're an HTTP call. Only gate the
            # local engines behind the mflux availability check.
            _repo = job.params.get("repo")
            _model = catalog.get_model(_repo) if _repo else None
            _is_cloud = bool(_model and _model.is_cloud)
            if not MFLUX_AVAILABLE and not _is_cloud:
                job.state = "error"
                job.error = f"mflux not installed: {MFLUX_IMPORT_ERROR}"
                job.finished_at = time.time()
                print(f"[gen] {job.job_id}: {job.error}", file=sys.stderr, flush=True)
                self._persist()
                return

            try:
                output_path = OUTPUT_DIR / f"{job.job_id}.png"
                self._dispatch_txt2img(job, output_path)
                if job.cancel_event.is_set():
                    job.state = "cancelled"
                else:
                    job.output_path = str(output_path.resolve())
                    job.progress = 1.0
                    job.state = "done"
                    print(f"[gen] done {job.job_id} → {output_path}", flush=True)
            except Exception as e:
                if job.cancel_event.is_set():
                    job.state = "cancelled"
                else:
                    job.state = "error"
                    job.error = f"{type(e).__name__}: {e}"
                    print(f"[gen] error {job.job_id}: {job.error}", file=sys.stderr, flush=True)
                    traceback.print_exc()
            finally:
                job.finished_at = time.time()
                self._persist()

    def _dispatch_txt2img(self, job: GenerationJob, output_path: Path) -> None:
        """
        Route to the right per-family txt2img worker. Mirrors `_dispatch_edit`'s
        shape for consistency. Families with no worker raise NotImplementedError
        with a clear hint about what to use instead.
        """
        params = job.params
        repo = params["repo"]
        model = catalog.get_model(repo)
        if model is None:
            raise ValueError(f"Repo {repo} is not in the catalog")

        # Cloud models route to a provider (HTTP), not a local mflux class, and
        # have nothing to cache — handle them before the local cache check.
        if model.is_cloud:
            self._generate_cloud(job, model, output_path)
            return

        if cache.cache_state(repo) != "cached":
            raise ValueError(f"Model {repo} is not fully cached locally — download it first")

        # Diffusers-engine models run on PyTorch/MPS via a separate worker,
        # routed by engine (not by mflux family). Handle before family dispatch.
        if model.is_diffusers:
            self._generate_diffusers(job, model, output_path)
            return

        family = model.family
        if family == "flux2-klein":
            self._generate_flux2_klein(job, output_path)
        elif family in ("flux1-schnell", "flux1-dev", "flux1-krea"):
            # mflux ships ONE Flux1 class that handles schnell, dev, AND the Krea
            # finetune — the variant is selected via the ModelConfig (schnell() /
            # dev() / krea_dev()) inside _generate_flux1.
            self._generate_flux1(job, model, output_path)
        elif family == "qwen-image":
            self._generate_qwen_image(job, model, output_path)
        elif family == "fibo":
            self._generate_fibo(job, model, output_path)
        elif family == "z-image":
            self._generate_z_image(job, model, output_path)
        elif family == "seedvr2":
            self._generate_seedvr2(job, model, output_path)
        elif family == "flux2-dev":
            raise NotImplementedError(
                "FLUX.2 dev isn't supported by mflux yet — only FLUX.2 klein has "
                "a wired mflux class. Use FLUX.2 klein 9B (full) for the highest "
                "klein quality, or wait for mflux to add a Flux2Dev variant."
            )
        else:
            raise NotImplementedError(
                f"No txt2img worker implemented for family '{family}'."
            )

    def _generate_diffusers(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """
        Run a model via HuggingFace diffusers on PyTorch/MPS — the second local
        engine (v1.9.0), for models mflux has no class for (SD3.5, Sana, Ideogram
        4, …). Loads from the app's HF cache (same HF_HOME as downloads), runs on
        Apple's MPS device, and saves a PNG. The loaded pipeline is cached in
        the process so repeat generations skip the multi-GB reload.

        Requires the diffusers/torch deps from requirements-generation.txt — if
        they're missing, the import error below is surfaced to the user as a
        clear job error telling them to run Install Generation.
        """
        try:
            import torch  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "The diffusers engine needs PyTorch, which isn't installed. "
                "Run 'Install Generation' to add the torch/diffusers deps "
                f"(import error: {type(e).__name__}: {e})."
            ) from e

        from . import settings as app_settings

        params = job.params
        repo = params["repo"]

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        # bf16 is the recommended dtype for SD3-class models (fp16 can yield black
        # images) and is supported on recent MPS; CPU falls back to float32.
        dtype = torch.bfloat16 if device == "mps" else torch.float32
        token = app_settings.get_hf_token()

        pipe = self._load_diffusers_pipeline(model_entry, repo=repo, dtype=dtype, token=token)
        pipe = pipe.to(device)

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)
        generator = torch.Generator(device=device).manual_seed(int(seed))

        negative = (params.get("negative_prompt") or "").strip() or None
        print(
            f"[gen] diffusers {repo} on {device} ({dtype}) "
            f"{params.get('width')}x{params.get('height')} steps={params.get('steps')}",
            flush=True,
        )
        result = pipe(
            prompt=params["prompt"],
            negative_prompt=negative,
            num_inference_steps=int(params.get("steps", 28)),
            guidance_scale=float(params.get("guidance", 3.5)),
            height=int(params["height"]),
            width=int(params["width"]),
            generator=generator,
        )
        image = result.images[0]
        image.save(str(output_path))

    def _load_diffusers_pipeline(self, model_entry, *, repo, dtype, token):
        """
        Load the diffusers pipeline for `repo`, caching ONE pipeline in-process
        (keyed by repo) so back-to-back generations don't reload multi-GB weights.
        Switching models evicts the previous pipeline (bounded memory). All
        generation is serialized by _GEN_LOCK, so no concurrency guard is needed.
        """
        prev = getattr(self, "_diffusers_pipe", None)   # (repo, pipe) or None
        if prev is not None and prev[0] == repo:
            return prev[1]

        # Evict any previously loaded pipeline before loading a new one.
        if prev is not None:
            self._diffusers_pipe = None
            del prev
            try:
                import torch  # type: ignore
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except Exception:
                pass

        if model_entry.diffusers_pipeline:
            # Explicit pipeline class (e.g. a custom Ideogram4Pipeline).
            import importlib
            mod = importlib.import_module("diffusers")
            pipe_cls = getattr(mod, model_entry.diffusers_pipeline)
            pipe = pipe_cls.from_pretrained(repo, torch_dtype=dtype, token=token)
        else:
            # Let diffusers resolve the right pipeline from model_index.json.
            from diffusers import AutoPipelineForText2Image  # type: ignore
            pipe = AutoPipelineForText2Image.from_pretrained(repo, torch_dtype=dtype, token=token)

        self._diffusers_pipe = (repo, pipe)
        return pipe

    def _generate_seedvr2(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """
        SeedVR2 — diffusion upscaler / restorer. Takes the uploaded image and
        reconstructs a higher-resolution version (fixed ~2× of the input's short
        side). NOT txt2img: the prompt / guidance / steps / strength controls are
        ignored. Lives in the Image-to-Image tab because it needs an input image.
        Self-contained — one repo (numz/SeedVR2_comfyUI), no base model.
        """
        from mflux.models.seedvr2.variants.upscale.seedvr2 import SeedVR2  # type: ignore
        from mflux.models.common.config.model_config import ModelConfig  # type: ignore
        from mflux.utils.scale_factor import ScaleFactor  # type: ignore

        params = job.params
        repo = params["repo"]
        image_path = params.get("image_path")
        if not image_path:
            raise RuntimeError(
                "SeedVR2 is an upscaler — it needs an input image. Use the "
                "Image-to-Image tab and attach the image you want to upscale."
            )

        model = SeedVR2(
            quantize=params.get("quantize"),
            model_path=repo,
            model_config=ModelConfig.seedvr2_7b(),
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        # Fixed 2× upscale of the input's short side. The generate form has no
        # scale control yet; a dedicated upscale UI is a future enhancement.
        result = model.generate_image(
            seed=int(seed),
            image_path=image_path,
            resolution=ScaleFactor(2.0),
        )
        if not hasattr(result, "save"):
            raise RuntimeError("mflux SeedVR2 returned an unexpected result; expected GeneratedImage.")
        result.save(str(output_path), overwrite=True)

    def _generate_cloud(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """
        Route a cloud (provider="cloud") model to its provider in
        app/backend/providers. No mflux, no local weights — just an HTTP call.
        The provider returns encoded image bytes which we normalise to PNG.
        """
        from . import providers  # lazy: keeps providers optional at import time
        from . import settings as app_settings

        params = job.params
        provider = providers.get_provider(model_entry.cloud_provider or "")
        if provider is None:
            raise RuntimeError(
                f"No cloud provider registered for '{model_entry.cloud_provider}'."
            )
        # Resolve this provider's credentials (api keys etc.) from app settings.
        # Keyless providers (Pollinations) get an empty config and ignore it.
        config = app_settings.get_cloud_credentials(model_entry.cloud_provider or "")

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        # Cloud providers don't report step progress — present an indeterminate
        # single-step job so the UI spinner still animates.
        job.total_steps = 1
        job.current_step = 0

        req = providers.CloudRequest(
            prompt=params["prompt"],
            width=int(params["width"]),
            height=int(params["height"]),
            seed=int(seed),
            model_id=model_entry.cloud_model_id,
            negative_prompt=(params.get("negative_prompt") or "").strip() or None,
        )
        print(
            f"[gen] cloud {model_entry.cloud_provider} model={model_entry.cloud_model_id} "
            f"{req.width}x{req.height} seed={seed}",
            flush=True,
        )
        image_bytes = provider.generate(req, config)

        # Normalise to PNG at output_path. Pillow is present in the generation
        # env; if it's somehow absent (cloud-only, no mflux install) or the
        # bytes aren't decodable, fall back to writing them raw — browsers
        # content-sniff the served file either way.
        try:
            import io
            from PIL import Image  # type: ignore
            Image.open(io.BytesIO(image_bytes)).save(str(output_path), format="PNG")
        except Exception:
            output_path.write_bytes(image_bytes)

        job.current_step = 1

    def _generate_flux2_klein(self, job: GenerationJob, output_path: Path) -> None:
        """
        Run mflux's FLUX.2 klein pipeline. Implementation is defensive because
        the mflux API surface changes between versions — we try the modern path
        first, then fall back to the older one if needed.
        """
        params = job.params
        repo = params["repo"]
        # Family + cache checks already performed by _dispatch_txt2img.

        # Lazy import so server start doesn't pay this cost.
        from mflux.models.flux2.variants.txt2img.flux2_klein import Flux2Klein  # type: ignore

        # Resolve quantization: for "AITRADER/...-mlx-Nbit" repos the weights
        # are pre-quantized; mflux reads that from the repo. For full checkpoints,
        # an explicit `quantize` value forces on-the-fly quant.
        quantize = params.get("quantize")  # None | 3 | 4 | 6 | 8

        lora_paths = params.get("lora_paths") or None
        lora_scales = params.get("lora_scales") or None
        negative_prompt = (params.get("negative_prompt") or "").strip() or " "

        # mflux's Flux2Klein hardcodes negative_prompt=" " inside generate_image.
        # We subclass to override _encode_prompt_pair so the user-supplied negative
        # actually reaches the encoder. For klein (distilled, guidance fixed to 1.0)
        # the negative has little effect, but it's surfaced for forward-compat with
        # dev models that respect classifier-free guidance.
        class Flux2KleinWithNegative(Flux2Klein):
            _user_negative = " "
            def _encode_prompt_pair(self, prompt, negative_prompt=" ", guidance=1.0):  # type: ignore[override]
                neg = self._user_negative or " "
                return super()._encode_prompt_pair(prompt=prompt, negative_prompt=neg, guidance=guidance)

        flux = Flux2KleinWithNegative(
            model_path=repo,
            quantize=quantize,
            lora_paths=lora_paths,
            lora_scales=lora_scales,
        )
        flux._user_negative = negative_prompt

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        # mflux returns a GeneratedImage with .save(path, overwrite=False).
        # For img2img, image_path and image_strength bias generation toward the
        # input image instead of pure noise.
        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "num_inference_steps": int(params.get("steps", 4)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", 3.5)),
        }
        if params.get("image_path"):
            gen_kwargs["image_path"] = params["image_path"]
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])
        result = flux.generate_image(**gen_kwargs)

        if not hasattr(result, "save"):
            raise RuntimeError(
                "mflux returned an unexpected result; expected GeneratedImage. "
                "Update generation.py to match this mflux version."
            )
        result.save(str(output_path), overwrite=True)

    def _generate_flux1(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """
        Run mflux's FLUX.1 pipeline (handles schnell, dev, AND the Krea finetune —
        mflux ships one Flux1 class, the variant is selected via model_config).
        Covers:
        - black-forest-labs/FLUX.1-schnell (full)
        - black-forest-labs/FLUX.1-dev (full, gated)
        - black-forest-labs/FLUX.1-Krea-dev (photorealism finetune, gated)

        Defaults differ by variant:
        - schnell — distilled, 1-4 steps, guidance fixed at 0.0
        - dev/krea — full guidance model, 20-30 steps, guidance ~3.5
        """
        from mflux.models.flux.variants.txt2img.flux import Flux1  # type: ignore
        from mflux.models.common.config.model_config import ModelConfig  # type: ignore

        params = job.params
        repo = params["repo"]
        family = model_entry.family

        # Pick the right ModelConfig for the family — mflux uses this to route
        # weight loading + scheduler selection internally. Krea is a dev-class
        # finetune, so it shares dev's guidance/step defaults below.
        if family == "flux1-schnell":
            model_config = ModelConfig.schnell()
        elif family == "flux1-krea":
            model_config = ModelConfig.krea_dev()
        else:
            model_config = ModelConfig.dev()

        # Schnell is distilled and ignores guidance/negative; dev respects both.
        # Pick sane per-variant defaults but let the user override.
        default_steps    = 4   if family == "flux1-schnell" else 20
        default_guidance = 0.0 if family == "flux1-schnell" else 3.5

        quantize = params.get("quantize")
        lora_paths = params.get("lora_paths") or None
        lora_scales = params.get("lora_scales") or None
        negative_prompt = (params.get("negative_prompt") or "").strip() or None

        print(
            f"[gen] flux1 {family} repo={repo} steps={params.get('steps', default_steps)} "
            f"guidance={params.get('guidance', default_guidance)}",
            flush=True,
        )

        flux = Flux1(
            model_path=repo,
            quantize=quantize,
            lora_paths=lora_paths,
            lora_scales=lora_scales,
            model_config=model_config,
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "num_inference_steps": int(params.get("steps", default_steps)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", default_guidance)),
        }
        # Negative prompt only matters for dev (schnell ignores it). Forwarding
        # for both is harmless — mflux's Flux1 accepts the kwarg either way.
        if negative_prompt:
            gen_kwargs["negative_prompt"] = negative_prompt
        # img2img: image_path + image_strength bias generation toward the input.
        if params.get("image_path"):
            gen_kwargs["image_path"] = params["image_path"]
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])

        try:
            result = flux.generate_image(**gen_kwargs)
        except ValueError as e:
            # mflux 0.17.5 introduced a stricter MLX quantization format.
            # Several community-uploaded 4-bit FLUX.1 repos (notably the
            # `madroid/*-mflux-4bit` pair) were quantized with an older mflux
            # release and store weight matrices in a dtype the current
            # mx.dequantize() rejects with "The matrix should be given as a
            # uint32". Translate the cryptic MLX error into actionable advice.
            msg = str(e)
            if "dequantize" in msg and "uint32" in msg:
                raise RuntimeError(
                    f"The pre-quantized repo `{repo}` uses an older MLX "
                    f"quantization format incompatible with mflux 0.17.x. "
                    f"This is an upstream issue with the repo, not the launcher.\n\n"
                    f"Workarounds:\n"
                    f"  1. Download the full {family} model (e.g. "
                    f"`black-forest-labs/FLUX.1-{('schnell' if family == 'flux1-schnell' else 'dev')}`) "
                    f"and pick THAT in the model dropdown — mflux will "
                    f"quantize at load time and it'll work.\n"
                    f"  2. Switch to FLUX.2 klein 4B — MLX 4-bit "
                    f"(`AITRADER/FLUX2-klein-4B-mlx-4bit`). Same memory "
                    f"footprint, known-working, generally higher quality."
                ) from e
            raise

        if not hasattr(result, "save"):
            raise RuntimeError(
                "mflux Flux1 returned an unexpected result; expected GeneratedImage."
            )
        result.save(str(output_path), overwrite=True)

    # ──────────────────────────────────────────────────────────────────────
    # mflux-native non-FLUX workers (v1.3.0) — Qwen-Image, FIBO, Z-Image.
    # All follow the same pattern as _generate_flux1:
    #   1. Resolve the right Class + ModelConfig from mflux's registry
    #   2. Build the model with on-the-fly quantize=4 (fits 16 GB Macs)
    #   3. Call .generate_image() with seed/prompt/dims/guidance/steps
    #   4. Save the result
    # ──────────────────────────────────────────────────────────────────────

    def _generate_qwen_image(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """Run mflux's QwenImage (Alibaba's Qwen-Image txt2img model).
        Strong on Chinese prompts + non-Latin text rendering."""
        from mflux.models.qwen.variants.txt2img.qwen_image import QwenImage  # type: ignore
        from mflux.models.common.config.model_config import ModelConfig  # type: ignore

        params = job.params
        repo = params["repo"]
        quantize = params.get("quantize")

        print(f"[gen] qwen-image repo={repo} steps={params.get('steps', 20)} "
              f"guidance={params.get('guidance', 4.0)}", flush=True)

        flux = QwenImage(
            model_path=repo,
            quantize=quantize,
            model_config=ModelConfig.qwen_image(),
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "num_inference_steps": int(params.get("steps", 20)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", 4.0)),
        }
        negative_prompt = (params.get("negative_prompt") or "").strip() or None
        if negative_prompt:
            gen_kwargs["negative_prompt"] = negative_prompt
        if params.get("image_path"):
            gen_kwargs["image_path"] = params["image_path"]
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])

        result = flux.generate_image(**gen_kwargs)
        result.save(str(output_path), overwrite=True)

    def _generate_qwen_edit(self, job: GenerationJob, output_path: Path) -> None:
        """Run mflux's QwenImageEdit — ungated instruction-edit model.
        Requires an input image (edit mode only)."""
        from mflux.models.qwen.variants.edit.qwen_image_edit import QwenImageEdit  # type: ignore

        params = job.params
        repo = params["repo"]
        if not params.get("image_path"):
            raise ValueError(
                "Qwen-Image Edit needs an input image. Use the Image Edit tab "
                "and attach a reference."
            )
        quantize = params.get("quantize")

        print(f"[gen] qwen-edit repo={repo} prompt_len={len(params['prompt'])}", flush=True)

        flux = QwenImageEdit(
            model_path=repo,
            quantize=quantize,
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        # QwenImageEdit's generate_image accepts image_paths (list) instead of
        # a single image_path — pass the user's input as a single-element list.
        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "image_paths": [params["image_path"]],
            "num_inference_steps": int(params.get("steps", 20)),
            "guidance": float(params.get("guidance", 4.0)),
        }
        # height/width are optional for Qwen-Edit — it can auto-size from the input image.
        if params.get("width"):
            gen_kwargs["width"] = int(params["width"])
        if params.get("height"):
            gen_kwargs["height"] = int(params["height"])

        result = flux.generate_image(**gen_kwargs)
        result.save(str(output_path), overwrite=True)

    def _generate_fibo(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """Run mflux's FIBO (BRIA AI). Handles both FIBO and FIBO Lite via
        ModelConfig.fibo() vs ModelConfig.fibo_lite(). Commercial-safe."""
        from mflux.models.fibo.variants.txt2img.fibo import FIBO  # type: ignore
        from mflux.models.common.config.model_config import ModelConfig  # type: ignore

        params = job.params
        repo = params["repo"]
        # Repo name → ModelConfig: "Fibo-lite" → fibo_lite(), else fibo()
        if "lite" in repo.lower():
            model_config = ModelConfig.fibo_lite()
        else:
            model_config = ModelConfig.fibo()
        quantize = params.get("quantize")

        print(f"[gen] fibo repo={repo} (config={model_config.aliases[0]}) "
              f"steps={params.get('steps', 20)}", flush=True)

        flux = FIBO(
            model_path=repo,
            quantize=quantize,
            model_config=model_config,
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "num_inference_steps": int(params.get("steps", 20)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", 4.0)),
        }
        negative_prompt = (params.get("negative_prompt") or "").strip() or None
        if negative_prompt:
            gen_kwargs["negative_prompt"] = negative_prompt
        if params.get("image_path"):
            gen_kwargs["image_path"] = params["image_path"]
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])

        result = flux.generate_image(**gen_kwargs)
        result.save(str(output_path), overwrite=True)

    def _generate_fibo_edit(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """Run mflux's FIBOEdit. Handles both Fibo-Edit and Fibo-Edit-RMBG."""
        from mflux.models.fibo.variants.edit.fibo_edit import FIBOEdit  # type: ignore
        from mflux.models.common.config.model_config import ModelConfig  # type: ignore

        params = job.params
        repo = params["repo"]
        if not params.get("image_path"):
            raise ValueError(
                "FIBO Edit needs an input image. Use the Image Edit tab "
                "and attach a reference."
            )
        # Repo name → ModelConfig: "-RMBG" → fibo_edit_rmbg(), else fibo_edit()
        if "rmbg" in repo.lower():
            model_config = ModelConfig.fibo_edit_rmbg()
        else:
            model_config = ModelConfig.fibo_edit()
        quantize = params.get("quantize")

        print(f"[gen] fibo-edit repo={repo} (config={model_config.aliases[0]})", flush=True)

        flux = FIBOEdit(
            model_path=repo,
            quantize=quantize,
            model_config=model_config,
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "num_inference_steps": int(params.get("steps", 20)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", 4.0)),
            "image_path": params["image_path"],
        }
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])

        result = flux.generate_image(**gen_kwargs)
        result.save(str(output_path), overwrite=True)

    def _generate_z_image(self, job: GenerationJob, model_entry, output_path: Path) -> None:
        """Run mflux's ZImage (Tongyi Lab). Handles both Z-Image + Z-Image Turbo.
        Stylized output strength — illustration, anime, painterly."""
        from mflux.models.z_image.variants.z_image import ZImage  # type: ignore
        from mflux.models.common.config.model_config import ModelConfig  # type: ignore

        params = job.params
        repo = params["repo"]
        # Repo name → ModelConfig: "Turbo" → z_image_turbo(), else z_image()
        if "turbo" in repo.lower():
            model_config = ModelConfig.z_image_turbo()
            default_steps = 6   # Turbo is distilled — fewer steps
        else:
            model_config = ModelConfig.z_image()
            default_steps = 20
        quantize = params.get("quantize")

        print(f"[gen] z-image repo={repo} (config={model_config.aliases[0]}) "
              f"steps={params.get('steps', default_steps)}", flush=True)

        flux = ZImage(
            model_path=repo,
            quantize=quantize,
            model_config=model_config,
        )

        seed = params.get("seed")
        if seed is None or seed < 0:
            import random
            seed = random.randint(0, 2**32 - 1)
        job.resolved_seed = int(seed)

        gen_kwargs = {
            "seed": int(seed),
            "prompt": params["prompt"],
            "num_inference_steps": int(params.get("steps", default_steps)),
            "height": int(params["height"]),
            "width": int(params["width"]),
            "guidance": float(params.get("guidance", 4.0)),
        }
        negative_prompt = (params.get("negative_prompt") or "").strip() or None
        if negative_prompt:
            gen_kwargs["negative_prompt"] = negative_prompt
        if params.get("image_path"):
            gen_kwargs["image_path"] = params["image_path"]
        if params.get("image_strength") is not None:
            gen_kwargs["image_strength"] = float(params["image_strength"])

        result = flux.generate_image(**gen_kwargs)
        result.save(str(output_path), overwrite=True)


manager = GenerationManager()
