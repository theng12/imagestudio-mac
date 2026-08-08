"""
Static catalog of image-generation models supported by ImageStudio (Mac).

Each entry describes a Hugging Face repo plus metadata that helps the UI:
download size, gating status, hardware floor, and a long-form explainer.

Models with the same `family` share an explainer in the UI so we don't repeat
ourselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import model_audits
from . import sizes as _sizes


@dataclass(frozen=True)
class Family:
    id: str
    label: str
    summary: str
    how_to_use: str


FAMILIES: dict[str, Family] = {
    "flux2-klein": Family(
        id="flux2-klein",
        label="FLUX.2 klein",
        summary=(
            "Black Forest Labs' distilled FLUX.2 line. Smaller and faster than "
            "FLUX.2 dev, designed to run on Apple Silicon."
        ),
        how_to_use=(
            "Distilled models use guidance=1.0 — the UI sets that automatically. "
            "Good starting settings: 4 steps, 512x512 or 768x768. Klein is the "
            "image-generation model; klein-base is the same architecture without "
            "instruction tuning and is better for fine-tuning workflows."
        ),
    ),
    "flux2-dev": Family(
        id="flux2-dev",
        label="FLUX.2 dev",
        summary=(
            "The full FLUX.2 dev checkpoint. Highest quality of the FLUX.2 line "
            "but extremely large — multi-tens-of-GB on disk and needs lots of "
            "unified memory."
        ),
        how_to_use=(
            "Use guidance 3.5-5.0 and 20-30 steps for the best quality. Long "
            "load times on first use; subsequent loads are faster once weights "
            "are memory-mapped. Gated on Hugging Face — accept the license on "
            "the repo page first."
        ),
    ),
    "flux1-schnell": Family(
        id="flux1-schnell",
        label="FLUX.1 schnell",
        summary=(
            "Original FLUX.1 schnell — distilled for speed, Apache 2.0 licensed, "
            "no gate. The best ungated option."
        ),
        how_to_use=(
            "Use guidance=0.0 and 1-4 steps. Schnell ignores guidance because "
            "it's distilled. Great for fast iteration."
        ),
    ),
    "flux1-dev": Family(
        id="flux1-dev",
        label="FLUX.1 dev",
        summary=(
            "Original FLUX.1 dev — non-commercial license, gated. Higher fidelity "
            "than schnell but slower."
        ),
        how_to_use=(
            "Use guidance 3.5 and 20-30 steps. Accept the license on the "
            "Hugging Face page before downloading."
        ),
    ),
    "flux1-krea": Family(
        id="flux1-krea",
        label="FLUX.1 Krea dev",
        summary=(
            "Black Forest Labs × Krea's opinionated FLUX.1 dev finetune, tuned "
            "for photorealism and a less 'AI-looking' aesthetic — fewer plastic "
            "skin / blown-out-highlight tells than stock FLUX.1 dev."
        ),
        how_to_use=(
            "Use guidance 3.5-5.0 and 20-30 steps, same as FLUX.1 dev — the UI "
            "defaults match. Gated on Hugging Face: accept the license on the "
            "repo page first. Best when stock FLUX output looks too synthetic."
        ),
    ),
    "flux1-kontext": Family(
        id="flux1-kontext",
        label="FLUX.1 Kontext",
        summary=(
            "Black Forest Labs' dedicated instruction-edit model. Preserves subject "
            "and composition while applying targeted text-described changes."
        ),
        how_to_use=(
            "Provide an input image and a clear instruction like 'make the sky red' "
            "or 'add sunglasses'. Best for surgical edits where the rest of the image "
            "must stay identical. Gated, requires HF token + license acceptance."
        ),
    ),
    "qwen-edit": Family(
        id="qwen-edit",
        label="Qwen-Image Edit",
        summary=(
            "Alibaba's Qwen-Image edit model. Alternative instruction-edit architecture, "
            "often ungated and smaller than Kontext."
        ),
        how_to_use=(
            "Same instruction-style prompts as Kontext. A good lightweight alternative "
            "when you don't want a 24 GB download for the FLUX.1 Kontext models."
        ),
    ),
    # NOTE: hidream/shuttle/flux1-lite removed in v1.3.0. mflux 0.17.5 has no
    # inference classes for these architectures — they'd need diffusers + their
    # own pipelines, which is a separate library + significant new install
    # weight. If a future mflux release adds them (or we add diffusers as a
    # second backend), re-add the Family + ModelEntry rows.
    "fibo": Family(
        id="fibo",
        label="FIBO",
        summary=(
            "BRIA AI's image-generation family. Trained on a fully-licensed dataset "
            "(no copyright concerns), high prompt fidelity, multiple variants from "
            "lite to full + a dedicated instruction-edit model with background-removal."
        ),
        how_to_use=(
            "20-30 steps, guidance 3.5-5.0 for finals. FIBO Lite is faster + smaller. "
            "FIBO Edit + FIBO Edit RMBG handle instruction edits ('add sunglasses') "
            "and background removal respectively. Commercial-safe by design."
        ),
    ),
    "qwen-image": Family(
        id="qwen-image",
        label="Qwen-Image (txt2img)",
        summary=(
            "Alibaba's Qwen-Image base model — the txt2img counterpart to Qwen-Image "
            "Edit. Strong multilingual prompt comprehension (especially Chinese), "
            "competitive with FLUX-class models for general-purpose generation."
        ),
        how_to_use=(
            "Standard txt2img prompts — Qwen-Image is unusually good at following "
            "Chinese prompts but works fine in English too. Recommended 20-30 steps, "
            "guidance 4.0."
        ),
    ),
    # ── Diffusers-engine families (v1.9.0) — PyTorch/MPS, NOT mflux ──────────
    "pixart-sigma": Family(
        id="pixart-sigma",
        label="PixArt-Σ (Sigma)",
        summary=(
            "PixArt-Sigma — a lightweight, efficient DiT text-to-image model. "
            "Small + fast on the diffusers engine (PyTorch/MPS), ungated. The "
            "lowest-footprint diffusers option here."
        ),
        how_to_use=(
            "Standard txt2img prompts. ~20 steps, guidance ~4.5, 1024px. Ungated "
            "— no HF token needed. The lightest diffusers model in the catalog."
        ),
    ),
    "lumina2": Family(
        id="lumina2",
        label="Lumina-Image 2.0",
        summary=(
            "Alpha-VLLM's Lumina-Image 2.0 — a ~2B flow-based DiT with a Gemma "
            "text encoder. Mid-weight, strong multilingual prompt comprehension, "
            "ungated. Runs via the diffusers engine on MPS."
        ),
        how_to_use=(
            "Standard txt2img prompts. ~30-50 steps, guidance ~4, 1024px. Ungated "
            "— no HF token needed."
        ),
    ),
    "auraflow": Family(
        id="auraflow",
        label="AuraFlow",
        summary=(
            "AuraFlow v0.3 — fal.ai's open flow-based text-to-image model (~6.8B). "
            "Larger/heavier than PixArt, Sana, or Lumina but strong prompt "
            "following. Runs via the diffusers engine on MPS; ungated."
        ),
        how_to_use=(
            "Standard txt2img prompts. Flow models like ~50 steps; guidance ~3.5, "
            "1024px+. Ungated. Heavier — best on a high-memory Mac."
        ),
    ),
    "sana": Family(
        id="sana",
        label="Sana (NVlabs)",
        summary=(
            "NVIDIA's Sana — an efficient linear-attention DiT that's fast and "
            "ungated (Apache-licensed). Runs via the diffusers engine on "
            "PyTorch/MPS. Lighter + quicker than SD3.5, and needs no HF license, "
            "so it's the easiest diffusers model to try."
        ),
        how_to_use=(
            "Standard txt2img prompts. ~18-20 steps, guidance ~4.5. Native 1024px. "
            "Ungated — no HF token or license needed. Runs on MPS; the first "
            "generation loads the pipeline, later ones reuse it."
        ),
    ),
    "sd35": Family(
        id="sd35",
        label="Stable Diffusion 3.5",
        summary=(
            "Stability AI's Stable Diffusion 3.5 — a strong general-purpose "
            "text-to-image model. Runs via the HuggingFace diffusers engine on "
            "PyTorch/MPS (not mflux/MLX), so it's slower than the FLUX-MLX models "
            "but is the gateway to the broader diffusers model ecosystem."
        ),
        how_to_use=(
            "Standard txt2img prompts. Recommended ~28 steps, guidance ~3.5-4.5 "
            "(the FLUX-style 4-step defaults will look bad — raise the steps). "
            "Gated on Hugging Face: accept the license on the repo page and set "
            "your HF token in Settings first. The first generation is slow (the "
            "pipeline loads + warms up on MPS); later ones reuse the loaded model."
        ),
    ),
    "sdxl": Family(
        id="sdxl",
        label="SDXL",
        summary=(
            "Community Stable Diffusion XL checkpoints on the diffusers engine "
            "(PyTorch/MPS). Two shapes live here: **Lightning** finetunes, "
            "step-distilled to 4-8 steps at low CFG, and **size-distilled** "
            "variants like Segmind Vega with a much smaller UNet that run in "
            "far less memory at normal step counts. All are ungated and "
            "permissively licensed, unlike the non-commercial FLUX.1-dev line."
        ),
        how_to_use=(
            "Standard txt2img prompts, native 1024x1024. Settings differ by "
            "model and the UI applies the right ones automatically: Lightning "
            "models want 4-7 steps at CFG 1.5-2.0 (higher guidance washes them "
            "out), while Segmind Vega wants ~25 steps at CFG ~9 and benefits "
            "from a negative prompt. Note these are step- or size-distilled, "
            "NOT guidance-distilled — unlike FLUX schnell/klein, they all use "
            "real classifier-free guidance, so the CFG control stays live."
        ),
    ),
    "seedvr2": Family(
        id="seedvr2",
        label="SeedVR2 (upscaler)",
        summary=(
            "SeedVR2 — a diffusion-based image upscaler / restorer, NOT a "
            "text-to-image model. Give it an image and it reconstructs a higher-"
            "resolution version. Self-contained: one repo, no base model needed."
        ),
        how_to_use=(
            "Use the Image-to-Image tab: attach the image you want to upscale and "
            "generate. SeedVR2 ignores the prompt, guidance, steps, and strength "
            "controls — it just upscales (currently a fixed 2× of the input). "
            "The 7B model is heavy; best on a high-memory Mac (M3 Ultra is ideal)."
        ),
    ),
}


@dataclass(frozen=True)
class ModelEntry:
    repo: str
    label: str
    family: str
    size_gb: float          # approximate full-precision download size
    gated: bool
    quantization: Optional[str] = None  # None | "mlx-2bit" | "mlx-4bit" | "mlx-8bit"
    min_unified_memory_gb: int = 8
    recommended_hardware: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)  # mflux aliases
    # Generation modes this model supports. All FLUX checkpoints can do txt2img
    # and img2img via mflux; only the klein family currently has an "edit"
    # variant (Flux2KleinEdit) in mflux.
    capabilities: tuple[str, ...] = ("txt2img", "img2img")
    # Plain-English use-case description shown on the model card so users can
    # self-select without having to know the technical specs.
    best_for: str = ""
    # Structured per-model use cases — each entry is (kind, text) where kind is
    # one of "good" / "weak" / "avoid". The UI renders these as ✅ / ⚠️ / ❌
    # bullets under the "Best for:" line. Helps users set realistic expectations
    # BEFORE they pick a model — e.g. MLX 4-bit quants have known anatomy
    # artifacts on multi-subject scenes, and saying so up front avoids the
    # "this model sucks" reaction after a bad generation.
    use_cases: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    # ── Execution provider ──────────────────────────────────────────────────
    # Every model in this catalog runs locally. Cloud providers were removed in
    # v1.29.0; this field is retained only because the catalog payload still
    # reports it to downstream consumers (Story Studio, Studio Hub).
    provider: str = "local"                 # always "local"
    # ── Local inference engine (v1.9.0) ─────────────────────────────────────
    # Which engine runs the model. "mflux" (default) = Apple MLX via mflux.
    # "diffusers" = HuggingFace diffusers on PyTorch/MPS, for models mflux has no
    # class for (SD3.5, Sana, Ideogram 4, …).
    engine: str = "mflux"                   # "mflux" | "diffusers"
    # Optional explicit diffusers pipeline class name (e.g. "StableDiffusion3Pipeline"
    # or a custom "Ideogram4Pipeline"). None → AutoPipelineForText2Image resolves it.
    diffusers_pipeline: Optional[str] = None
    # Optional huggingface_hub `allow_patterns` globs restricting what gets
    # downloaded from `repo`. None (default) downloads the whole repo. Needed
    # when a repo bundles files the pipeline never loads alongside the ones it
    # does — e.g. some SDXL repos publish a Civitai-style single-file
    # .safetensors checkpoint next to the diffusers-format subdirs
    # (unet/, vae/, text_encoder*/, tokenizer*/, model_index.json) that
    # from_pretrained() actually reads, roughly doubling the download for no
    # benefit. `size_gb` above should reflect the filtered total, not the
    # full repo, when this is set.
    download_allow_patterns: Optional[tuple[str, ...]] = None
    # ── Output-dimension capability (v1.15.0) ───────────────────────────────
    # Whether this model honors the requested width/height (i.e. the aspect-ratio
    # presets do anything). False for fixed-output models that ignore width/height
    # and emit a model-chosen size. Exposed in the catalog so the UI hides the
    # aspect picker and Story Studio knows not to offer ratios for these models.
    supports_custom_dimensions: bool = True
    # For fixed-output models (supports_custom_dimensions=False): the single real
    # output size the endpoint emits, used to build the one `sizes` entry. Defaults
    # to 1024×1024 when unset.
    fixed_size: Optional[tuple] = None
    # A repository can contain MLX weights without using the on-disk format
    # expected by this app's mflux worker. Keep such models discoverable while
    # preventing a misleading "Engine ready" state and a guaranteed load crash.
    runtime_compatible: bool = True
    runtime_note: str = ""
    # Optional internal qualification and license evidence. These fields are
    # intentionally technical inventory metadata, not customer-facing branding.
    qualified_revision: Optional[str] = None
    license_spdx: Optional[str] = None
    license_source_repo: Optional[str] = None
    license_source_revision: Optional[str] = None
    license_evidence_url: Optional[str] = None
    license_evidence_sha256: Optional[str] = None
    license_repackage_copy_present: Optional[bool] = None

    @property
    def is_apple_optimized(self) -> bool:
        return self.quantization is not None and self.quantization.startswith("mlx")

    @property
    def is_diffusers(self) -> bool:
        return self.engine == "diffusers"


CATALOG: tuple[ModelEntry, ...] = (
    # ──────────── FLUX.2 klein ────────────
    ModelEntry(
        repo="AITRADER/FLUX2-klein-4B-mlx-4bit",
        label="FLUX.2 klein 4B — MLX 4-bit",
        family="flux2-klein",
        size_gb=4.6,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=8,  # operator-confirmed on 8 GB; peak not yet measured
        recommended_hardware="8 GB unified memory minimum; 16 GB recommended for stronger operating headroom.",
        capabilities=("txt2img", "img2img", "edit"),
        best_for="The recommended starter on Apple Silicon. Fastest loads and smallest disk footprint. Great for daily exploration and instruction edits.",
        qualified_revision="7fd24828501390b67a92c8b66d2fc5a707d0ba1a",
        license_spdx="Apache-2.0",
        license_source_repo="black-forest-labs/FLUX.2-klein-4B",
        license_source_revision="e7b7dc27f91deacad38e78976d1f2b499d76a294",
        license_evidence_url=(
            "https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/blob/"
            "e7b7dc27f91deacad38e78976d1f2b499d76a294/LICENSE.md"
        ),
        license_evidence_sha256="ca02bc51900ab07789d1b70283329e7137f5af98f5161c23a1c81fc38a4af1fe",
        # The immutable AITRADER repackage names the upstream base model but
        # contains no LICENSE file or license card field. Keep that fact visible.
        license_repackage_copy_present=False,
        use_cases=(
            ("good",  "Quick concept iteration — single landscapes, abstract art, isolated objects"),
            ("good",  "Style exploration ('cinematic 35mm', 'oil painting', 'isometric voxel')"),
            ("good",  "Simple instruction edits ('add sunglasses', 'make sky red')"),
            ("weak",  "Faces under close-up — 4-bit quantization sometimes softens features"),
            ("avoid", "Multi-subject scenes (two animals, group portraits, complex compositions) — 4-bit quants regularly produce extra heads / limbs / fused subjects. Use klein 4B 8-bit or full klein 4B for these."),
            ("avoid", "Final-quality print or commercial work — use the 8-bit or full variant"),
        ),
    ),
    ModelEntry(
        repo="AITRADER/FLUX2-klein-4B-mlx-8bit",
        label="FLUX.2 klein 4B — MLX 8-bit",
        family="flux2-klein",
        size_gb=8.6,
        gated=False,
        quantization="mlx-8bit",
        min_unified_memory_gb=16,  # 8.6 GB of weights cannot fit an 8.6 GB machine
        recommended_hardware="M2 Pro / M3 16 GB or better. Best quality among klein 4B quants.",
        capabilities=("txt2img", "img2img", "edit"),
        best_for="The quality sweet spot for klein 4B. Near-full-precision output at half the disk and memory cost. Pick this over 4-bit when you can afford 16 GB.",
        use_cases=(
            ("good",  "Multi-subject scenes — significantly fewer anatomy artifacts than 4-bit"),
            ("good",  "Portraits + close-up faces (sharper than 4-bit)"),
            ("good",  "Instruction edits where the original details must be preserved"),
            ("good",  "Final-quality renders at the klein 4B tier"),
            ("weak",  "Slower load + ~2× the memory footprint of 4-bit"),
        ),
    ),
    ModelEntry(
        repo="AITRADER/FLUX2-klein-9B-mlx-4bit",
        label="FLUX.2 klein 9B — MLX 4-bit",
        family="flux2-klein",
        size_gb=9.5,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=16,  # 9.5 GB of weights exceed an 8.6 GB machine
        recommended_hardware="M2 Pro / M3 16 GB or better.",
        capabilities=("txt2img", "img2img", "edit"),
        best_for="Run klein 9B on 16 GB Macs without compromise on architecture. Step up from 4B-4bit if you want more nuanced prompt following.",
        use_cases=(
            ("good",  "9B architecture's nuanced prompt comprehension at 16 GB-Mac memory budget"),
            ("good",  "Complex compositions where 4B can't follow the prompt fully"),
            ("good",  "Style mixing prompts ('art deco poster meets cyberpunk neon')"),
            ("weak",  "4-bit anatomy artifacts still apply — multi-subject scenes risk extra heads/limbs"),
            ("avoid", "Final-quality close-up portraits — use the 8-bit variant if your Mac has 24 GB+"),
        ),
    ),
    # NOTE: 4 klein-base entries (FLUX.2-klein-base-4B/9B full + MLX 4-bit/8-bit)
    # removed in v1.2.5. They're foundation models intended for LoRA fine-tuning,
    # not for generation — every use_case in the old entries said "avoid for
    # everyday generation, use the non-base klein". Keeping them was just adding
    # decision noise to the picker. If/when LoRA fine-tuning becomes a feature
    # of this app, re-add them and route to a dedicated fine-tuning UI.

    # ──────────── FLUX.2 dev ────────────
    # NOTE: this family has no catalog rows. black-forest-labs/FLUX.2-dev was
    # removed in v1.26.0 — it is gated (licence acceptance on the Hugging Face
    # website, so no unattended fleet download) and carries a 64 GB floor with
    # a 177.6 GB download, putting it outside every 8/16/24 GB machine. The
    # family and its mflux wiring are kept so an ungated, smaller FLUX.2
    # conversion can be added later without rewiring; the UI hides empty
    # families.
    # ──────────── FLUX.1 schnell ────────────
    ModelEntry(
        repo="black-forest-labs/FLUX.1-schnell",
        label="FLUX.1 schnell (full)",
        family="flux1-schnell",
        size_gb=57.9,
        gated=False,
        min_unified_memory_gb=24,
        recommended_hardware="M2 Pro 32 GB+ for the full checkpoint.",
        capabilities=("txt2img", "img2img"),
        best_for="Original FLUX.1 schnell — distilled for 1–4 step generation. Ungated, Apache-licensed. Great for ultra-fast iteration if you have the memory for the full checkpoint.",
        use_cases=(
            ("good",  "Full-precision schnell quality — sharpest schnell output available"),
            ("good",  "Apache-2.0 license — safe for commercial use"),
            ("good",  "Rapid 1-4 step iteration if memory isn't a constraint"),
            ("weak",  "Large download (24 GB) + ≥24 GB memory floor — heavy for what you get"),
            ("avoid", "16 GB Macs — use the MLX 4-bit variant instead, near-identical quality at quarter the size"),
        ),
    ),
    # NOTE: madroid/flux.1-schnell-mflux-4bit removed in v1.2.5 — its older
    # MLX quantization format is incompatible with mflux 0.17.x (dequantize
    # ValueError on T5 text encoder load). If a maintained 4-bit schnell repo
    # appears (e.g. under mflux-community/*), add it here.

    # ──────────── FLUX.1 dev ────────────
    # NOTE: this family has no catalog rows. madroid/flux.1-dev-mflux-4bit was
    # removed in v1.2.5 (same MLX-format incompatibility as the madroid schnell
    # repo), and the full black-forest-labs/FLUX.1-dev was removed in v1.26.0
    # because it is gated — it cannot be fetched without accepting a licence on
    # the Hugging Face website, so it could never be part of an automated fleet
    # download. The family entry and its mflux wiring are kept deliberately so
    # an ungated dev conversion can be added later without rewiring; the UI
    # hides families with no models.

    # ──────────── FLUX.1 Krea dev (photorealism finetune) — new in v1.5.0 ──────
    # Rides the same mflux Flux1 class as schnell/dev. _generate_flux1 selects
    # ModelConfig.krea_dev() for this family. Pure txt2img/img2img, no new deps
    # beyond the existing FLUX.1 stack — a near drop-in catalog add.
    # Pre-quantized MLX 4-bit Krea, by filipstrand (the mflux author) — the
    # "maintained 4-bit repo" the removed-madroid notes above were waiting for.
    # Same flux1-krea family → _generate_flux1 with ModelConfig.krea_dev(). Its
    # T5 encoder is stored in the current U32 quant format (mflux 0.10.0), so it
    # loads on current mflux (unlike the old madroid repos). Ungated repo.
    ModelEntry(
        repo="filipstrand/FLUX.1-Krea-dev-mflux-4bit",
        label="FLUX.1 Krea dev — MLX 4-bit",
        family="flux1-krea",
        size_gb=9.6,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=16,
        recommended_hardware="M-series with 16 GB unified memory. Pre-quantized MLX 4-bit — no HF license gate on this repo.",
        capabilities=("txt2img", "img2img"),
        best_for="FLUX.1 Krea dev (BFL × Krea's photorealism finetune) pre-quantized to MLX 4-bit by the mflux author — brings the natural, less 'AI-looking' Krea photorealism to 16 GB Macs, where the full 24 GB checkpoint won't fit. The repo is ungated (no token/license acceptance to download). Underlying FLUX.1-dev license is still non-commercial.",
        use_cases=(
            ("good",  "Photoreal FLUX (natural skin/lighting) on a 16 GB Mac — no 24 GB checkpoint"),
            ("good",  "Ungated download — no HF license-acceptance step (unlike the full Krea dev)"),
            ("good",  "Pre-quantized MLX 4-bit — loads fast, no on-the-fly quantization wait"),
            ("weak",  "Underlying FLUX.1-dev license is non-commercial — personal projects only"),
            ("avoid", "8 GB Macs — 9.6 GB download + ~16 GB floor; use a klein 4-bit for tight memory"),
        ),
    ),

    # ──────────── FLUX.1 Kontext (dedicated instruction-edit model) ────────────
    # Wired via _generate_kontext (mflux's Flux1Kontext). Requires an input
    # image — txt2img-only flows will error with a clear "needs reference" message.
    # Pre-quantized MLX 4-bit Kontext (akx) — same flux1-kontext family →
    # _generate_kontext (mflux's Flux1Kontext, model_path=repo). T5 encoder is in
    # the current U32 quant format (mflux 0.9.6), so it loads on current mflux.
    # Ungated repo. Requires an input image (Image Edit tab) like the full model.
    ModelEntry(
        repo="akx/FLUX.1-Kontext-dev-mflux-4bit",
        label="FLUX.1 Kontext dev — MLX 4-bit",
        family="flux1-kontext",
        size_gb=9.6,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=16,
        recommended_hardware="M-series with 16 GB unified memory. Pre-quantized MLX 4-bit — no HF license gate on this repo.",
        capabilities=("edit",),
        best_for="FLUX.1 Kontext dev (instruction image-editing) pre-quantized to MLX 4-bit — brings surgical, subject-preserving photo edits to 16 GB Macs, where the full 24 GB checkpoint won't fit. Ungated repo. Use the Image Edit tab with a reference image attached. Underlying FLUX.1-dev license is non-commercial.",
        use_cases=(
            ("good",  "Surgical instruction edits on a 16 GB Mac — 4-bit, no 24 GB checkpoint"),
            ("good",  "'Add sunglasses' / 'change the shirt colour' / 'remove that object' style edits"),
            ("good",  "Ungated download + pre-quantized (no on-the-fly quantization wait)"),
            ("weak",  "Underlying FLUX.1-dev license is non-commercial — personal projects only"),
            ("avoid", "Pure txt2img — Kontext is edit-specialized; needs a reference image (Image Edit tab)"),
        ),
    ),

    # ──────────── Qwen-Image Edit (wired in v1.3.0) ────────────
    ModelEntry(
        repo="Qwen/Qwen-Image-Edit-2509",
        label="Qwen-Image Edit (2509)",
        family="qwen-edit",
        size_gb=57.7,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro 16 GB+. On-the-fly mflux quantization (quantize=4 fits 16 GB).",
        capabilities=("edit",),
        best_for="Alibaba's Qwen-Image Edit — ungated alternative to FLUX.1 Kontext. Wired in v1.3.0 via mflux's QwenImageEdit class.",
        use_cases=(
            ("good",  "Ungated alternative to FLUX.1 Kontext for instruction-edits"),
            ("good",  "Particularly strong on Chinese-language prompts + non-Latin text in images"),
            ("good",  "Multilingual prompt comprehension beyond English"),
            ("weak",  "20 GB download — large initial setup"),
        ),
    ),

    # NOTE: HiDream / Shuttle / FLUX.1 lite entries removed in v1.3.0 —
    # mflux 0.17.5 has no inference classes for these architectures. They
    # would need diffusers + their own pipelines as a separate backend,
    # which is a significant new install dependency. Per the v1.2.5 rule
    # (don't keep entries that can't work), they're cut. If a future mflux
    # release adds them, re-add Family + ModelEntry rows.

    # ──────────── FIBO (BRIA AI) — new in v1.3.0 ────────────
    # mflux ships FIBO + FIBO Lite (txt2img) + FIBO Edit + FIBO Edit RMBG
    # (background removal). BRIA's selling point: 100% licensed training
    # data → no copyright concerns for commercial work.
    ModelEntry(
        repo="briaai/Fibo-lite",
        label="FIBO Lite (recommended)",
        family="fibo",
        size_gb=24.2,   # rough estimate — half-tier of full FIBO
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB. On-the-fly mflux quantization.",
        capabilities=("txt2img", "img2img"),
        best_for="BRIA's smaller / faster FIBO tier — commercial-safe (fully licensed training data), competitive quality on portraits + products. Pick this over full FIBO unless you need maximum detail.",
        use_cases=(
            ("good",  "Commercial work — BRIA's training data is fully licensed (no copyright concerns)"),
            ("good",  "Portrait + product photography (BRIA's training emphasis)"),
            ("good",  "Faster + lighter than full FIBO at minor quality cost"),
            ("weak",  "Newer to mflux — fewer community LoRAs vs FLUX"),
        ),
    ),
    ModelEntry(
        repo="briaai/FIBO",
        label="FIBO (full)",
        family="fibo",
        size_gb=25.6,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB+. On-the-fly mflux quantization (quantize=4 fits 16 GB).",
        capabilities=("txt2img", "img2img"),
        best_for="BRIA's flagship FIBO — highest quality for final renders. Commercial-safe via licensed training data. Use FIBO Lite for iteration, switch to this for finals.",
        use_cases=(
            ("good",  "Final renders for commercial use (fully licensed training data)"),
            ("good",  "Highest FIBO quality"),
            ("weak",  "Slower per-generation than FIBO Lite"),
            ("avoid", "Quick iteration — use FIBO Lite first"),
        ),
    ),
    ModelEntry(
        repo="briaai/Fibo-Edit",
        label="FIBO Edit",
        family="fibo",
        size_gb=40.7,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB+. Edit mode only (requires input image).",
        capabilities=("edit",),
        best_for="BRIA's instruction-edit model. Alternative to FLUX.1 Kontext with commercial-safe licensing. Provide an image + edit prompt like 'change shirt to red'.",
        use_cases=(
            ("good",  "Commercial-safe instruction editing (licensed training data)"),
            ("good",  "Surgical edits — preserve composition, apply targeted changes"),
            ("weak",  "Larger memory footprint than the txt2img variants"),
            ("avoid", "Pure txt2img — use FIBO Lite/full for that, not Edit"),
        ),
    ),
    # Onyx Z-Image Turbo quants (wabibito) — a genuine 3-bit/4-bit MLX
    # quantization of Tongyi-MAI/Z-Image-Turbo (the card is explicit that this
    # is a quantization, not a finetune). The andrevp MLX conversions this
    # family used to carry were removed in v1.26.0 as unloadable; these repos
    # instead declare library_name: diffusers with pipeline
    # ZImagePipeline, which the installed diffusers 0.38.0 has natively
    # (registered in AUTO_TEXT2IMAGE_PIPELINES_MAPPING under "z-image") — so
    # these are wired through engine="diffusers", NOT mflux, and are expected
    # to actually load, where the removed andrevp rows were externally-packed
    # MLX with no mflux quantization metadata and could not be loaded at all.
    ModelEntry(
        repo="Qwen/Qwen-Image",
        label="Qwen-Image",
        family="qwen-image",
        size_gb=57.7,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB+. On-the-fly mflux quantization (quantize=4 fits 16 GB).",
        capabilities=("txt2img", "img2img"),
        best_for="Alibaba's Qwen-Image — particularly strong on Chinese prompts and non-Latin text rendering in images. Multilingual prompt comprehension is the headline feature.",
        use_cases=(
            ("good",  "Chinese-language prompts (Qwen-Image's training emphasis)"),
            ("good",  "Non-Latin text rendering inside images (signs, posters)"),
            ("good",  "Multilingual prompt comprehension beyond English"),
            ("good",  "Apache-2.0 license — commercial use OK"),
            ("weak",  "English-only prompts: FLUX-tier alternatives often beat it on photoreal"),
            ("weak",  "20 GB download — biggest catalog entry"),
        ),
    ),

    # ──────────── Diffusers engine (PyTorch/MPS) — new in v1.9.0 ────────────
    # Routed via _generate_diffusers (HuggingFace diffusers), NOT mflux.
    # engine="diffusers" entries are excluded from audit_truth.py (it audits
    # mflux wiring only). Needs the diffusers/torch deps from
    # requirements-generation.txt (Install Generation).
    #
    # Sana (v1.10.0) — ungated + MPS-friendly, so the easiest diffusers model to
    # actually run on a Mac. (Ideogram 4 was evaluated here but CANNOT run on
    # Apple MPS: its weights are fp8/nf4 — fp8 isn't a supported MPS dtype and
    # nf4 needs CUDA-only bitsandbytes. Revisit when mflux ships native MLX
    # Ideogram support.)
    ModelEntry(
        repo="Efficient-Large-Model/Sana_1600M_1024px_diffusers",
        label="Sana 1600M (1024px)",
        family="sana",
        size_gb=25.8,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="Apple Silicon 16 GB+. Efficient linear-attention DiT — lighter/faster than SD3.5 on MPS.",
        capabilities=("txt2img",),
        engine="diffusers",
        best_for="NVIDIA's Sana via the diffusers engine — fast, efficient, ungated (no HF license needed), 1024px native. The easiest diffusers model to try on a Mac and a good second proof that the engine generalizes beyond SD3.5.",
        use_cases=(
            ("good",  "Ungated — no HF token / license gate, downloads immediately"),
            ("good",  "Fast, memory-efficient diffusers txt2img on MPS"),
            ("good",  "1024px native; good general-purpose quality"),
            ("weak",  "PyTorch/MPS is still slower than the mflux/MLX models"),
            ("avoid", "Maximum fidelity — SD3.5 / large FLUX models edge it on detail"),
        ),
    ),
    ModelEntry(
        repo="PixArt-alpha/PixArt-Sigma-XL-2-1024-MS",
        label="PixArt-Σ XL 1024",
        family="pixart-sigma",
        size_gb=21.8,
        gated=False,
        min_unified_memory_gb=12,
        recommended_hardware="Apple Silicon 12 GB+. One of the lightest diffusers models — quick to download + run on MPS.",
        capabilities=("txt2img",),
        engine="diffusers",
        diffusers_pipeline="PixArtSigmaPipeline",
        best_for="A lightweight, fast diffusers DiT — small download, low memory, ungated. Good when you want a quick diffusers-engine model without SD3.5's size.",
        use_cases=(
            ("good",  "Lightest/fastest diffusers model here — small download"),
            ("good",  "Ungated — no HF token / license"),
            ("good",  "Good general 1024px quality for its size"),
            ("weak",  "Lower detail ceiling than SD3.5 / large FLUX models"),
        ),
    ),
    ModelEntry(
        repo="Alpha-VLLM/Lumina-Image-2.0",
        label="Lumina-Image 2.0",
        family="lumina2",
        size_gb=31.7,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="Apple Silicon 16 GB+. ~2B flow DiT with a Gemma text encoder.",
        capabilities=("txt2img",),
        engine="diffusers",
        diffusers_pipeline="Lumina2Pipeline",
        best_for="A ~2B flow-based DiT with strong multilingual prompt comprehension (Gemma text encoder), fully open. A mid-weight middle ground between PixArt and the large models.",
        use_cases=(
            ("good",  "Strong multilingual prompt comprehension (Gemma encoder)"),
            ("good",  "Ungated, mid-weight — between PixArt and the large models"),
            ("weak",  "Flow model — ~30-50 steps for best quality"),
        ),
    ),
    ModelEntry(
        repo="fal/AuraFlow-v0.3",
        label="AuraFlow v0.3",
        family="auraflow",
        size_gb=66.0,
        gated=False,
        min_unified_memory_gb=24,
        recommended_hardware="High-memory Apple Silicon (24 GB+). ~6.8B flow model — heavier on MPS.",
        capabilities=("txt2img",),
        engine="diffusers",
        diffusers_pipeline="AuraFlowPipeline",
        best_for="fal.ai's open flow-based model — strong prompt following, fully open weights. Heavier than PixArt/Sana/Lumina; a higher-capacity diffusers option for a powerful Mac.",
        use_cases=(
            ("good",  "Strong prompt adherence; fully open weights"),
            ("good",  "A larger-capacity diffusers option than PixArt/Sana/Lumina"),
            ("weak",  "~6.8B — heavier download + slower on MPS"),
            ("weak",  "Flow model wants more steps (~50) — longer generations"),
        ),
    ),

    # SDXL Lightning finetunes (diffusers-format community repos, not the raw
    # Civitai single-file checkpoints). Both repos publish their diffusers-
    # format subdirs (unet/, vae/, text_encoder*/, tokenizer*/) ALONGSIDE a
    # Civitai-style single-file .safetensors checkpoint the app's generic
    # AutoPipelineForText2Image.from_pretrained() loader never reads — that
    # extra file is excluded via download_allow_patterns so users don't pay
    # for bytes the engine can't use. DreamShaper additionally ships redundant
    # `.fp16.*` variant weights alongside the default-precision ones (the
    # loader never requests a variant, so it always reads the default files);
    # those are excluded too. If _load_diffusers_pipeline() is ever changed to
    # pass variant="fp16", this entry's allow_patterns must be updated to match.
    ModelEntry(
        repo="RunDiffusion/Juggernaut-XL-Lightning",
        label="Juggernaut XL Lightning",
        family="sdxl",
        size_gb=13.9,
        gated=False,
        # QUALIFIED BY MEASUREMENT on a 16 GB Apple M4 (2026-08-05), 1280x720.
        # Its sibling DreamShaper XL Lightning — architecturally identical, same
        # 13.88 GB of weights — ran at 29.2 s/step and grew swap by 5.58 GB,
        # i.e. it thrashed rather than computed. 16 GB is not a usable floor for
        # a full-size SDXL UNet + dual CLIP encoders on MPS.
        min_unified_memory_gb=24,
        recommended_hardware="Apple Silicon 24 GB+. Measured on a 16 GB M4 the sibling model swapped ~5.6 GB and ran ~29 s/step at 1280x720 — usable only with real headroom.",
        capabilities=("txt2img",),
        engine="diffusers",
        download_allow_patterns=(
            "model_index.json",
            "scheduler/*",
            "text_encoder/*",
            "text_encoder_2/*",
            "tokenizer/*",
            "tokenizer_2/*",
            "unet/*",
            "vae/*",
        ),
        best_for="RunDiffusion's photoreal Juggernaut XL, distilled to SDXL Lightning's 5-7 step schedule — same aesthetic as full Juggernaut at roughly 5x the speed. Ungated, permissively licensed (OpenRAIL-M). Use low CFG (1.5-2.0) — high guidance washes out Lightning models.",
        use_cases=(
            ("good",  "Fast photoreal portraits/scenes — 5-7 steps instead of 30-40"),
            ("good",  "Real-time iteration on prompts before committing to a slower model"),
            ("good",  "Ungated + OpenRAIL-M license — broader use than the non-commercial FLUX.1-dev finetunes"),
            ("weak",  "Ships PyTorch .bin (pickle) weights, not safetensors — RunDiffusion's official upload, but note the format if that matters to you"),
            ("avoid", "Maximum per-image fidelity — use full Juggernaut XL v9 (30-40 steps) or a FLUX model for that"),
        ),
    ),
    ModelEntry(
        repo="Lykon/dreamshaper-xl-lightning",
        label="DreamShaper XL Lightning",
        family="sdxl",
        size_gb=13.9,
        gated=False,
        # QUALIFIED BY MEASUREMENT on a 16 GB Apple M4 (2026-08-05), 1280x720,
        # 6 steps: 29.2 s/step, swap grew 5.58 GB, free RAM fell to 18%. It
        # completes, but by thrashing — 6.5x slower per step than Segmind Vega
        # doing the same resolution on the same machine. Raised 16 -> 24.
        min_unified_memory_gb=24,
        recommended_hardware="Apple Silicon 24 GB+. Measured on a 16 GB M4: ~29 s/step at 1280x720 with ~5.6 GB of swap growth — it runs, but thrashes.",
        capabilities=("txt2img",),
        engine="diffusers",
        download_allow_patterns=(
            "model_index.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder/model.safetensors",
            "text_encoder_2/config.json",
            "text_encoder_2/model.safetensors",
            "tokenizer/*",
            "tokenizer_2/*",
            "unet/config.json",
            "unet/diffusion_pytorch_model.safetensors",
            "vae/config.json",
            "vae/diffusion_pytorch_model.safetensors",
        ),
        best_for="Lykon's all-around SDXL finetune (fantasy art, renders, stylized/anime-leaning output), distilled to SDXL Lightning's 4-step schedule. Ungated, permissively licensed (OpenRAIL++). Use low CFG (~2.0) — high guidance washes out Lightning models.",
        use_cases=(
            ("good",  "Fast stylized/fantasy art and illustration — 4 steps"),
            ("good",  "Broader stylistic range than a photoreal-only model like Juggernaut"),
            ("good",  "Ungated + OpenRAIL++ license — broader use than the non-commercial FLUX.1-dev finetunes"),
            ("weak",  "4-step Lightning ceiling — less fine detail than a full-step SDXL or FLUX model"),
            ("avoid", "Photoreal portraits — Juggernaut XL Lightning is the stronger pick for that"),
        ),
    ),

    # Segmind Vega — SIZE-distilled SDXL (v1.24.0). Not a Lightning model: it
    # keeps a normal ~25-step schedule at high CFG, but its UNet is 2.98 GB vs
    # SDXL's 10.27 GB (~0.74B params), which is what brings it into 8 GB reach.
    # Note the text encoders are NOT shrunk — they're byte-identical in size to
    # full SDXL's, so they dominate the footprint here (3.27 of 6.59 GB).
    ModelEntry(
        repo="segmind/Segmind-Vega",
        label="Segmind Vega — compact SDXL",
        family="sdxl",
        size_gb=6.6,
        gated=False,
        # QUALIFIED BY MEASUREMENT on a 16 GB Apple M4 (2026-08-05), 1280x720,
        # 25 steps: 4.5 s/step, swap grew 4.0 GB, free RAM floor 13%. It does
        # touch swap on 16 GB, but stays responsive — 6.5x faster per step than
        # the full-size SDXL Lightning pair on the same machine, which is why
        # this stays at 16 while they were raised to 24.
        #
        # An earlier 8 GB guess (from the small 2.98 GB UNet) was WRONG: live
        # weights are 3.29 GB but the allocator reached 12.54 GB. Attention/VAE
        # slicing is NOT a workaround — on MPS + bfloat16 it produced pure black
        # images (std=0.0) while barely reducing peak. See CHANGELOG 1.24.0.
        min_unified_memory_gb=16,
        recommended_hardware="Apple Silicon 16 GB+. Measured on a 16 GB M4: 4.5 s/step at 1280x720 with ~4 GB swap growth — the only SDXL here that stays responsive on 16 GB.",
        capabilities=("txt2img",),
        engine="diffusers",
        download_allow_patterns=(
            "model_index.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder/model.safetensors",
            "text_encoder_2/config.json",
            "text_encoder_2/model.safetensors",
            "tokenizer/*",
            "tokenizer_2/*",
            "unet/config.json",
            "unet/diffusion_pytorch_model.safetensors",
            "vae/config.json",
            "vae/diffusion_pytorch_model.safetensors",
        ),
        best_for="Segmind's size-distilled SDXL — a ~70% smaller UNet (2.98 GB vs SDXL's 10.27 GB) and the lightest SDXL download here at 6.6 GB. Apache-2.0, the most permissive license in this catalog — genuinely unrestricted commercially, unlike the OpenRAIL Lightning pair. Unlike those, it wants a NORMAL schedule: ~25 steps at CFG ~9, plus a negative prompt (Segmind's own recommendation). Note it still needs 16 GB despite the small weights.",
        use_cases=(
            ("good",  "Apache-2.0 — genuinely unrestricted, including commercial use"),
            ("good",  "Lightest SDXL download here (6.6 GB vs 13.9 GB) and lowest peak memory of the three"),
            ("good",  "General 1024px / 1280x720 txt2img with the broad SDXL prompt vocabulary"),
            ("weak",  "~25 steps at CFG ~9 — roughly 90 s at 1280x720, vs ~6 steps for the Lightning pair"),
            ("weak",  "Distilled UNet gives up fine detail vs a full-size SDXL finetune"),
            ("avoid", "8 GB Macs — the small weights are misleading; measured peak is 12.5 GB"),
            ("avoid", "Stylized explainer / pixel-art work on Apple Silicon — FLUX.2 klein 4B is stronger there AND runs on 8 GB"),
        ),
    ),

    # ──────────── ERNIE-Image Turbo (Baidu) — diffusers engine ────────────
    # 4-bit MLX/diffusers conversion of baidu/ERNIE-Image-Turbo. Repo declares
    # library_name: diffusers with pipeline ErnieImagePipeline. Unlike
    # ZImagePipeline, ErnieImagePipeline is NOT registered in diffusers
    # 0.38.0's AUTO_TEXT2IMAGE_PIPELINES_MAPPING, so AutoPipelineForText2Image
    # would fail to resolve it — diffusers_pipeline is set explicitly below,
    # not optionally, or loading breaks.
    ModelEntry(
        repo="numz/SeedVR2_comfyUI",
        label="SeedVR2 7B — Upscaler",
        family="seedvr2",
        size_gb=60.1,   # rough — the 7B weights
        gated=False,
        min_unified_memory_gb=24,
        recommended_hardware="High-memory Apple Silicon (M2 Max / M3 Max / M3 Ultra). The 7B upscaler is heavy.",
        capabilities=("img2img",),
        best_for="Diffusion upscaler / restorer — turn a small or soft image into a higher-resolution one. Use the Image-to-Image tab, attach an image, and generate; it upscales ~2×. NOT a txt2img model — the prompt / steps / strength controls are ignored.",
        use_cases=(
            ("good",  "Upscaling + restoring generated images to higher resolution"),
            ("good",  "Cleaning up soft / low-res photos (diffusion restoration)"),
            ("good",  "Two-pass workflow: fast low-res generation → SeedVR2 upscale"),
            ("weak",  "Heavy 7B model — best on 24 GB+ (ideal on M3 Ultra)"),
            ("avoid", "Text-to-image — SeedVR2 only upscales an existing image, it can't generate from a prompt"),
            ("avoid", "Exact output sizing — currently a fixed ~2× upscale (no scale control in the UI yet)"),
        ),
    ),
)


def get_model(repo: str) -> Optional[ModelEntry]:
    for m in CATALOG:
        if m.repo == repo:
            return m
    return None


def generation_profile(m: ModelEntry) -> dict:
    """Describe the controls and defaults the Generate UI should expose.

    Providers and engines accept different parameters. Keeping this contract
    beside the catalog prevents the frontend from showing controls that are
    silently ignored and gives future catalog additions one place to declare
    their generation behavior.
    """
    repo = m.repo.lower()
    distilled = (
        m.family in {"flux2-klein", "flux1-schnell"}
        or (m.family != "sdxl" and ("turbo" in repo or "lightning" in repo))
    )
    # SDXL Lightning is step-distilled (fewer steps), not guidance-distilled —
    # unlike FLUX schnell/klein or z-image turbo, it still uses real
    # classifier-free guidance (just a low value) and negative prompts are a
    # normal, commonly-used control for it. So it's excluded from `distilled`
    # above even though "lightning" is in the repo id, and gets its own
    # defaults below instead of guidance=0 / hidden controls.
    is_upscaler = m.family == "seedvr2"

    defaults = {"steps": 20, "guidance": 4.0, "image_strength": 0.6}
    if m.family == "flux2-klein":
        defaults.update(steps=4, guidance=1.0, image_strength=0.85)
    elif m.family == "flux1-schnell":
        defaults.update(steps=4, guidance=0.0)
    elif m.family in {"flux1-dev", "flux1-krea", "flux1-kontext"}:
        defaults.update(steps=24, guidance=3.5)
    elif m.family in {"qwen-image", "qwen-edit", "fibo"}:
        defaults.update(steps=20, guidance=4.0)
    elif m.family == "z-image":
        defaults.update(steps=9 if "turbo" in repo else 24, guidance=0.0 if "turbo" in repo else 4.0)
    elif m.family == "sd35":
        defaults.update(steps=28, guidance=4.0)
    elif m.family in {"sana", "pixart-sigma"}:
        defaults.update(steps=20, guidance=4.5)
    elif m.family == "lumina2":
        defaults.update(steps=35, guidance=4.0)
    elif m.family == "auraflow":
        defaults.update(steps=40, guidance=3.5)
    elif m.family == "ernie-image":
        # ERNIE-Image Turbo's own card benchmark used 5 steps — that's the one
        # hard number we have, so steps=5 is measured, not guessed. The card
        # does not state a guidance value. It's named "Turbo" and its repo id
        # contains "turbo", which already trips the `distilled` check above
        # (hiding the guidance/negative-prompt controls in the UI) — by
        # analogy to the other guidance-distilled turbo models in this catalog
        # (FLUX.1 schnell, Z-Image Turbo) we default guidance to 0.0 rather
        # than inheriting the generic 4.0. If real-world output looks
        # undercooked at guidance=0.0, that's a signal this assumption is
        # wrong and the card should be re-checked for an explicit CFG value.
        defaults.update(steps=5, guidance=0.0)
    elif m.family == "sdxl":
        # Two very different tunings share this family. Lightning finetunes are
        # step-distilled: few steps, low CFG (high guidance washes them out).
        # Size-distilled models like Segmind Vega keep a normal schedule and
        # actually want HIGH guidance — Segmind's card explicitly asks for
        # CFG ~9 plus a negative prompt. Getting this backwards produces washed
        # -out slop on one and undercooked noise on the other.
        if "lightning" in repo:
            defaults.update(steps=6, guidance=2.0)
        else:
            defaults.update(steps=25, guidance=9.0)

    controls = {
        "prompt": not is_upscaler,
        "aspect_ratio": m.supports_custom_dimensions and not is_upscaler,
        "negative_prompt": not is_upscaler and not distilled,
        "steps": not is_upscaler,
        "guidance": not is_upscaler and not distilled,
        "seed": not is_upscaler,
        "batch": True,
        # Qwen-Edit and FIBO-Edit accept a reference image but their
        # installed mflux edit signatures do not accept image_strength.
        "image_strength": (
            not is_upscaler
            and any(c in m.capabilities for c in ("img2img", "edit"))
            and not (m.family == "qwen-edit" or (m.family == "fibo" and "edit" in m.capabilities))
        ),
        "runtime_quantization": m.engine == "mflux" and not m.is_apple_optimized and not is_upscaler,
        "loras": m.family in {"flux2-klein", "flux1-schnell", "flux1-dev", "flux1-krea"},
    }
    summary = (
        "Upscaler workflow: provide an image; generation tuning is handled by the model."
        if is_upscaler else
        ("Distilled model: its fast trained defaults are applied automatically."
         if distilled else "Balanced defaults for this model family are applied automatically.")
    )

    return {"controls": controls, "defaults": defaults, "summary": summary}


def serialize_model(m: ModelEntry) -> dict:
    # Compute a per-model hardware-fit verdict against the running Mac's
    # detected RAM. Imported lazily to avoid a circular import at module load.
    try:
        from . import system_info
        fit = system_info.fit_for(m.min_unified_memory_gb)
    except Exception:
        fit = None

    return {
        "repo": m.repo,
        "label": m.label,
        "family": m.family,
        "family_label": FAMILIES[m.family].label,
        "size_gb": m.size_gb,
        "gated": m.gated,
        "quantization": m.quantization,
        "min_unified_memory_gb": m.min_unified_memory_gb,
        "recommended_hardware": m.recommended_hardware,
        "apple_optimized": m.is_apple_optimized,
        "aliases": list(m.aliases),
        "capabilities": list(m.capabilities),
        "best_for": m.best_for,
        # New in v1.1 — structured use cases + hardware fit verdict.
        "use_cases": [{"kind": k, "text": t} for k, t in m.use_cases],
        "fit": fit,   # {state, label, hint, actual_gb, required_gb} or None
        # Every model in this catalog runs locally (v1.29.0 removed the cloud
        # providers). Kept in the payload because downstream consumers (Story
        # Studio, Studio Hub) read it; it is now always "local".
        "provider": m.provider,
        # New (v1.15.0) — does the model honor width/height? False for fixed-size
        # endpoints. Story Studio + the UI use this to hide/disable the
        # aspect-ratio picker.
        "supports_custom_dimensions": m.supports_custom_dimensions,
        # New (v1.17.0) — ready-to-use per-model size menu so clients (Story
        # Studio) drive aspect-ratio + resolution pickers with no pixel math.
        # `sizes`: [{aspect_ratio,label,width,height,tier,[default],[fixed]}]
        # `default_aspect_ratio`: the AR to preselect.
        # `custom`: {min_px,max_px,step,max_pixels} free-sizing range, or null.
        **_sizes.build_sizes(m),
        # New in v1.9.0 — local inference engine (mflux vs diffusers).
        "engine": m.engine,
        "is_diffusers": m.is_diffusers,
        "runtime_compatible": m.runtime_compatible,
        "runtime_note": m.runtime_note,
        "qualified_revision": m.qualified_revision,
        "license_evidence": (
            {
                "spdx": m.license_spdx,
                "source_repo": m.license_source_repo,
                "source_revision": m.license_source_revision,
                "url": m.license_evidence_url,
                "sha256": m.license_evidence_sha256,
                "repackage_copy_present": m.license_repackage_copy_present,
            }
            if m.license_spdx else None
        ),
        "generation_profile": generation_profile(m),
        # Audited candidates are sibling evidence, not publication authority.
        # Studio Hub applies its separate owner-controlled exposure decision.
        "genstudio_candidate": model_audits.candidate_for(m.repo),
    }


def serialize_family(f: Family) -> dict:
    return {
        "id": f.id,
        "label": f.label,
        "summary": f.summary,
        "how_to_use": f.how_to_use,
    }
