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
    "z-image": Family(
        id="z-image",
        label="Z-Image (Tongyi)",
        summary=(
            "Tongyi Lab's Z-Image — an open Chinese-team image model with a turbo "
            "(distilled, few-step) variant alongside the standard release. Mixed "
            "training data with strong stylization and prompt comprehension."
        ),
        how_to_use=(
            "Z-Image Turbo: 4-8 steps for fast iteration. Standard Z-Image: 20-30 "
            "steps for quality. Z-Image is particularly strong on stylized outputs "
            "(illustration, anime, painterly) compared to FLUX's photorealistic lean."
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
    # ── Cloud families (v1.5.0) — NOT mflux engines; routed via providers/ ──
    "pollinations": Family(
        id="pollinations",
        label="Pollinations (cloud, free)",
        summary=(
            "Free hosted text-to-image via Pollinations.ai — no API key, no "
            "download, no local GPU. Runs on Pollinations' servers, so your "
            "prompt leaves this Mac. Best-effort and rate-limited."
        ),
        how_to_use=(
            "Pick it like any model and generate — there's nothing to download. "
            "Standard txt2img prompts. Because it's a free shared service, expect "
            "variable latency and occasional queueing. Don't send private or "
            "sensitive prompts to a third-party cloud service."
        ),
    ),
    "cloudflare": Family(
        id="cloudflare",
        label="Cloudflare Workers AI (cloud)",
        summary=(
            "Image generation on Cloudflare's Workers AI edge network. Free tier: "
            "10,000 'neurons'/day, no credit card. Needs a free Cloudflare Account "
            "ID + API token (set them once in Settings → Cloud provider keys)."
        ),
        how_to_use=(
            "Add your Cloudflare Account ID + API token in Settings, then pick a "
            "Cloudflare model and generate. FLUX.1 schnell runs in 1-8 steps. The "
            "Workers AI schnell endpoint outputs a fixed size (it ignores the "
            "width/height controls). Runs on Cloudflare's servers — prompts leave "
            "this Mac."
        ),
    ),
    "together": Family(
        id="together",
        label="Together AI (cloud)",
        summary=(
            "Image generation via Together AI. The FLUX.1 [schnell] Free endpoint "
            "is free with a (free) Together API key; new accounts also get trial "
            "credits for the paid endpoints. Set the key in Settings."
        ),
        how_to_use=(
            "Add your Together API key in Settings, then pick a Together model and "
            "generate. The free schnell endpoint honors width/height and caps at "
            "4 steps. Runs on Together's servers — prompts leave this Mac."
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
    quantization: Optional[str] = None  # None | "mlx-4bit" | "mlx-8bit"
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
    # ── Cloud-provider routing (v1.5.0) ─────────────────────────────────────
    # Local models leave these at defaults. A cloud model sets provider="cloud"
    # + cloud_provider (a registry id in app/backend/providers) + cloud_model_id
    # (the model name to request from that provider). Cloud models have NO
    # Hugging Face download — `repo` is a synthetic stable id used only as the
    # catalog key + job param, never fetched from HF. cache state is synthesised
    # as "cached" by the /api/catalog endpoint so the UI treats them as ready.
    provider: str = "local"                 # "local" | "cloud"
    cloud_provider: Optional[str] = None    # e.g. "pollinations"
    cloud_model_id: Optional[str] = None    # provider-specific model name, e.g. "flux"
    # ── Local inference engine (v1.9.0) ─────────────────────────────────────
    # Which engine runs a LOCAL model. "mflux" (default) = Apple MLX via mflux.
    # "diffusers" = HuggingFace diffusers on PyTorch/MPS, for models mflux has no
    # class for (SD3.5, Sana, Ideogram 4, …). Cloud models ignore this — a
    # provider="cloud" entry short-circuits before engine dispatch.
    engine: str = "mflux"                   # "mflux" | "diffusers"
    # Optional explicit diffusers pipeline class name (e.g. "StableDiffusion3Pipeline"
    # or a custom "Ideogram4Pipeline"). None → AutoPipelineForText2Image resolves it.
    diffusers_pipeline: Optional[str] = None

    @property
    def is_apple_optimized(self) -> bool:
        return self.quantization is not None and self.quantization.startswith("mlx")

    @property
    def is_cloud(self) -> bool:
        return self.provider == "cloud"

    @property
    def is_diffusers(self) -> bool:
        return self.engine == "diffusers"


CATALOG: tuple[ModelEntry, ...] = (
    # ──────────── FLUX.2 klein ────────────
    ModelEntry(
        repo="black-forest-labs/FLUX.2-klein-4B",
        label="FLUX.2 klein 4B (full)",
        family="flux2-klein",
        size_gb=8.0,
        gated=True,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 / M4 with 16 GB unified memory minimum.",
        aliases=("flux2-klein-4b",),
        capabilities=("txt2img", "img2img", "edit"),
        best_for="Maximum klein 4B quality, on-the-fly quantization. Best for users who want full-precision weights and have the memory headroom.",
        use_cases=(
            ("good",  "Quality reference for klein-tier output — no quantization artifacts"),
            ("good",  "Portrait + product photography with one clear subject"),
            ("good",  "Instruction edits where original-image fidelity matters"),
            ("weak",  "Slow first-load on 16 GB Macs (on-the-fly quantization)"),
            ("avoid", "Quick iteration — use an MLX quant for 3-5× faster loads"),
        ),
    ),
    ModelEntry(
        repo="AITRADER/FLUX2-klein-4B-mlx-4bit",
        label="FLUX.2 klein 4B — MLX 4-bit",
        family="flux2-klein",
        size_gb=2.3,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=8,
        recommended_hardware="M1/M2 8 GB works but is tight. M2 Pro / M3 16 GB is comfortable.",
        capabilities=("txt2img", "img2img", "edit"),
        best_for="The recommended starter on Apple Silicon. Fastest loads, smallest disk footprint, runs on 8 GB Macs. Great for daily exploration and instruction edits.",
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
        size_gb=4.5,
        gated=False,
        quantization="mlx-8bit",
        min_unified_memory_gb=16,
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
        repo="black-forest-labs/FLUX.2-klein-9B",
        label="FLUX.2 klein 9B (full)",
        family="flux2-klein",
        size_gb=18.0,
        gated=True,
        min_unified_memory_gb=32,
        recommended_hardware="M2 Max / M3 Max 32 GB+ recommended.",
        aliases=("flux2-klein-9b",),
        capabilities=("txt2img", "img2img", "edit"),
        best_for="Larger klein for more detail and prompt comprehension. Needs serious memory — M2 Max+ territory.",
        use_cases=(
            ("good",  "Complex multi-element prompts ('busy market street, dozens of people, golden hour')"),
            ("good",  "Architectural + interior photography with intricate detail"),
            ("good",  "Final-quality renders where klein 4B isn't catching all your prompt details"),
            ("weak",  "Slow per-generation vs the 4B tier (2-3× longer at the same step count)"),
            ("avoid", "Quick iteration — drop to klein 4B for prompt scouting, then upgrade to 9B for finals"),
        ),
    ),
    ModelEntry(
        repo="AITRADER/FLUX2-klein-9B-mlx-4bit",
        label="FLUX.2 klein 9B — MLX 4-bit",
        family="flux2-klein",
        size_gb=5.0,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=16,
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
    ModelEntry(
        repo="AITRADER/FLUX2-klein-9B-mlx-8bit",
        label="FLUX.2 klein 9B — MLX 8-bit",
        family="flux2-klein",
        size_gb=9.5,
        gated=False,
        quantization="mlx-8bit",
        min_unified_memory_gb=24,
        recommended_hardware="M2 Pro / M3 Pro 32 GB or better recommended.",
        capabilities=("txt2img", "img2img", "edit"),
        best_for="Best quality + best architecture combo for klein. Needs 24+ GB. Pick this if you want the most out of klein and have the hardware.",
        use_cases=(
            ("good",  "Reference quality for the klein line — sharpest details + best prompt following"),
            ("good",  "Multi-subject scenes (group portraits, animals together, busy scenes) — 8-bit quant on 9B handles these well"),
            ("good",  "Final-quality client work where you can't afford anatomy artifacts"),
            ("weak",  "Slow per-generation — 9B + 8-bit is the most compute-heavy klein variant"),
            ("avoid", "16 GB Macs — needs ≥24 GB headroom for stable operation"),
        ),
    ),
    # NOTE: 4 klein-base entries (FLUX.2-klein-base-4B/9B full + MLX 4-bit/8-bit)
    # removed in v1.2.5. They're foundation models intended for LoRA fine-tuning,
    # not for generation — every use_case in the old entries said "avoid for
    # everyday generation, use the non-base klein". Keeping them was just adding
    # decision noise to the picker. If/when LoRA fine-tuning becomes a feature
    # of this app, re-add them and route to a dedicated fine-tuning UI.

    # ──────────── FLUX.2 dev ────────────
    ModelEntry(
        repo="black-forest-labs/FLUX.2-dev",
        label="FLUX.2 dev",
        family="flux2-dev",
        size_gb=64.0,
        gated=True,
        min_unified_memory_gb=64,
        recommended_hardware=(
            "M3 Max 64 GB / M3 Ultra / M4 Max. Long download (multi-tens of GB)."
        ),
        capabilities=("txt2img", "img2img"),
        best_for="Highest quality FLUX.2 generation. Needs serious hardware (64 GB+) and patience (multi-tens of GB download). The choice for final renders when quality > speed.",
        use_cases=(
            ("good",  "Reference quality — the open-source FLUX line's peak"),
            ("good",  "Final commercial renders, print-resolution outputs"),
            ("good",  "The hardest prompts (complex scenes, accurate text rendering)"),
            ("weak",  "Slow per-generation — minutes, not seconds"),
            ("weak",  "Long initial download (60+ GB)"),
            ("avoid", "Any Mac with less than 64 GB — won't fit, will swap or OOM"),
        ),
    ),

    # ──────────── FLUX.1 schnell ────────────
    ModelEntry(
        repo="black-forest-labs/FLUX.1-schnell",
        label="FLUX.1 schnell (full)",
        family="flux1-schnell",
        size_gb=24.0,
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
    ModelEntry(
        repo="black-forest-labs/FLUX.1-dev",
        label="FLUX.1 dev (full)",
        family="flux1-dev",
        size_gb=24.0,
        gated=True,
        min_unified_memory_gb=24,
        recommended_hardware="M2 Pro 32 GB+ for the full checkpoint. License-gated.",
        capabilities=("txt2img", "img2img"),
        best_for="The original high-quality FLUX.1 — needs 20–30 steps but produces excellent results. Gated, non-commercial license. Pick over schnell when fidelity > speed.",
        use_cases=(
            ("good",  "Highest-quality FLUX.1 output — full-precision reference"),
            ("good",  "Slow, thoughtful renders with 20-30 inference steps"),
            ("weak",  "License is non-commercial — personal projects only"),
            ("avoid", "16 GB Macs — use the MLX 4-bit variant"),
            ("avoid", "Quick iteration — schnell is built for that"),
        ),
    ),
    # NOTE: madroid/flux.1-dev-mflux-4bit removed in v1.2.5 — same MLX-format
    # incompatibility as the madroid schnell repo. The full
    # black-forest-labs/FLUX.1-dev entry above still works via on-the-fly
    # quantization (mflux loads + quantizes during weight loading).

    # ──────────── FLUX.1 Krea dev (photorealism finetune) — new in v1.5.0 ──────
    # Rides the same mflux Flux1 class as schnell/dev. _generate_flux1 selects
    # ModelConfig.krea_dev() for this family. Pure txt2img/img2img, no new deps
    # beyond the existing FLUX.1 stack — a near drop-in catalog add.
    ModelEntry(
        repo="black-forest-labs/FLUX.1-Krea-dev",
        label="FLUX.1 Krea dev",
        family="flux1-krea",
        size_gb=24.0,
        gated=True,
        min_unified_memory_gb=24,
        recommended_hardware="M2 Pro 32 GB+ for the full checkpoint. License-gated (HF token + license acceptance).",
        capabilities=("txt2img", "img2img"),
        best_for="BFL × Krea's photorealism-tuned FLUX.1 — noticeably less 'AI-looking' than stock FLUX.1 dev (more natural skin, lighting, texture). Pick this over FLUX.1 dev when you want photographic realism rather than the default glossy FLUX look.",
        use_cases=(
            ("good",  "Photorealistic portraits + people — more natural skin/lighting than stock FLUX.1 dev"),
            ("good",  "Editorial / lifestyle / documentary-style photography"),
            ("good",  "Anything where stock FLUX output looks too glossy or synthetic"),
            ("weak",  "License is non-commercial — personal projects only"),
            ("avoid", "16 GB Macs — 24 GB checkpoint; use an MLX-quant klein for tight memory"),
            ("avoid", "Quick iteration — 20-30 steps; use FLUX.1 schnell or a klein quant for speed"),
        ),
    ),

    # ──────────── FLUX.1 Kontext (dedicated instruction-edit model) ────────────
    # Wired via _generate_kontext (mflux's Flux1Kontext). Requires an input
    # image — txt2img-only flows will error with a clear "needs reference" message.
    ModelEntry(
        repo="black-forest-labs/FLUX.1-Kontext-dev",
        label="FLUX.1 Kontext dev",
        family="flux1-kontext",
        size_gb=24.0,
        gated=True,
        min_unified_memory_gb=24,
        recommended_hardware="M2 Pro 32 GB+ for the full checkpoint. Gated, needs HF token + license acceptance.",
        capabilities=("edit",),
        best_for="Black Forest Labs' dedicated instruction-edit model. Best-in-class for surgical photo edits (subject preserved, only the requested change applied). Use the Image Edit tab with a reference image attached.",
        use_cases=(
            ("good",  "Surgical photo edits — change just one element, preserve everything else"),
            ("good",  "'Add sunglasses', 'change shirt color', 'remove background object' style prompts"),
            ("weak",  "License is non-commercial — personal projects only"),
            ("avoid", "Pure txt2img generation — Kontext is edit-specialized and requires a reference image (use the Image Edit tab)"),
        ),
    ),

    # ──────────── Qwen-Image Edit (wired in v1.3.0) ────────────
    ModelEntry(
        repo="Qwen/Qwen-Image-Edit-2509",
        label="Qwen-Image Edit (2509)",
        family="qwen-edit",
        size_gb=20.0,
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
        size_gb=10.0,   # rough estimate — half-tier of full FIBO
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
        size_gb=20.0,
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
        size_gb=20.0,
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
    ModelEntry(
        repo="briaai/Fibo-Edit-RMBG",
        label="FIBO Edit — Background Removal",
        family="fibo",
        size_gb=20.0,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB+. Specialized for background removal.",
        capabilities=("edit",),
        best_for="BRIA's dedicated background-removal model. Provide an image, get back the same image with the background removed (transparent). Cleaner than prompting a general edit model.",
        use_cases=(
            ("good",  "Background removal for product photos, profile pics, asset prep"),
            ("good",  "Cleaner output than asking a general edit model to 'remove background'"),
            ("weak",  "Single-purpose — for general edits use FIBO Edit"),
        ),
    ),

    # ──────────── Z-Image (Tongyi Lab) — new in v1.3.0 ────────────
    # mflux ships Z-Image + Z-Image Turbo (distilled fast variant). Tongyi
    # Lab's open Chinese-team model with strong stylization.
    ModelEntry(
        repo="Tongyi-MAI/Z-Image-Turbo",
        label="Z-Image Turbo (recommended)",
        family="z-image",
        size_gb=12.0,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB. Distilled — 4-8 steps for fast iteration.",
        capabilities=("txt2img", "img2img"),
        best_for="Z-Image's distilled turbo tier — fast iteration with the Z-Image aesthetic. 4-8 steps vs 20-30 for the full variant. Pick this for daily use.",
        use_cases=(
            ("good",  "Fast iteration — 4-8 steps on Apple Silicon"),
            ("good",  "Stylized output (illustration, anime, painterly) — different aesthetic from FLUX"),
            ("good",  "Strong Chinese-language prompt comprehension"),
            ("weak",  "Less detail than full Z-Image — for finals use the standard variant"),
        ),
    ),
    ModelEntry(
        repo="Tongyi-MAI/Z-Image",
        label="Z-Image (full)",
        family="z-image",
        size_gb=20.0,
        gated=False,
        min_unified_memory_gb=16,
        recommended_hardware="M2 Pro / M3 16 GB+. 20-30 steps for finals.",
        capabilities=("txt2img", "img2img"),
        best_for="Z-Image's full release — slower but higher quality. Strong on stylized output (anime, illustration, painterly) where FLUX leans photographic.",
        use_cases=(
            ("good",  "Final renders with stylized aesthetic"),
            ("good",  "Strong on Chinese-language + non-Latin script prompts"),
            ("weak",  "Slow per-generation (20-30 steps) — use Turbo for iteration"),
        ),
    ),

    # ──────────── Qwen-Image base (wired in v1.3.0) ────────────
    # Using the canonical Qwen/Qwen-Image repo + on-the-fly mflux quantization.
    # We skip the mlx-community/Qwen-Image-4bit pre-quant since we can't verify
    # its MLX format compatibility (madroid's repos taught us this lesson).
    # On-the-fly quantize=4 is the known-safe path.
    ModelEntry(
        repo="Qwen/Qwen-Image",
        label="Qwen-Image",
        family="qwen-image",
        size_gb=20.0,
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
    # Routed via _generate_diffusers (HuggingFace diffusers), NOT mflux. Phase A
    # proof model: Stable Diffusion 3.5 Large. engine="diffusers" entries are
    # excluded from audit_truth.py (it audits mflux wiring only). Needs the
    # diffusers/torch deps from requirements-generation.txt (Install Generation).
    ModelEntry(
        repo="stabilityai/stable-diffusion-3.5-large",
        label="Stable Diffusion 3.5 Large",
        family="sd35",
        size_gb=20.0,
        gated=True,
        min_unified_memory_gb=24,
        recommended_hardware="High-memory Apple Silicon (M2 Max / M3 Max / M3 Ultra). Runs on PyTorch/MPS — slower than the MLX models.",
        capabilities=("txt2img",),
        engine="diffusers",
        best_for="Stability AI's SD3.5 Large via the diffusers engine — a strong, well-supported general txt2img model, and the proof-of-concept for running non-FLUX models locally. Gated (HF token + license). Runs on MPS, so slower than the FLUX-MLX models.",
        use_cases=(
            ("good",  "General-purpose txt2img with the broad SD3.5 ecosystem"),
            ("good",  "Opens the diffusers model zoo this engine unlocks (Ideogram 4, Sana, …)"),
            ("weak",  "PyTorch/MPS is slower than mflux/MLX — expect longer generations"),
            ("weak",  "Gated + large download — needs HF token + license acceptance"),
            ("avoid", "Fast iteration on a small Mac — use an MLX klein quant for that"),
        ),
    ),

    # ──────────── SeedVR2 upscaler (image restoration) — new in v1.7.0 ──────
    # Self-contained single repo (numz/SeedVR2_comfyUI), no base model. Wired via
    # _generate_seedvr2 (mflux's SeedVR2). Lives in the Image-to-Image tab because
    # it needs an input image; prompt/guidance/steps/strength are ignored.
    ModelEntry(
        repo="numz/SeedVR2_comfyUI",
        label="SeedVR2 7B — Upscaler",
        family="seedvr2",
        size_gb=18.0,   # rough — the 7B weights
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

    # ──────────── Cloud providers (v1.5.0) — free, no local GPU ────────────
    # These do NOT use mflux. provider="cloud" routes _dispatch_txt2img to the
    # providers/ registry instead of a local inference class. `repo` is a
    # synthetic stable id (never fetched from HF); /api/catalog synthesises a
    # "cached" cache state so the UI shows them ready with no download button.
    # Excluded from audit_truth.py (it audits mflux wiring only).
    ModelEntry(
        repo="pollinations/flux",
        label="Pollinations FLUX (cloud, free)",
        family="pollinations",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs in the cloud. Works on any Mac; no GPU or download needed.",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="pollinations",
        cloud_model_id="flux",
        best_for="Zero-setup free image generation in the cloud — no download, no API key, no local GPU. Great for trying the app instantly or generating on a Mac that can't run the local MLX models. Your prompt is sent to Pollinations' servers.",
        use_cases=(
            ("good",  "Instant first generation — nothing to download or install"),
            ("good",  "Macs without the memory/GPU for local FLUX (8 GB, Intel, etc.)"),
            ("good",  "Quick throwaway concepts where local/offline isn't needed"),
            ("weak",  "Variable latency + rate limits — it's a free shared service"),
            ("avoid", "Private or sensitive prompts — they leave your Mac for a 3rd-party server"),
            ("avoid", "Reproducible/seed-locked pipelines — cloud output is best-effort, not deterministic"),
        ),
    ),
    ModelEntry(
        repo="cloudflare/flux-1-schnell",
        label="FLUX.1 schnell — Cloudflare (cloud)",
        family="cloudflare",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Cloudflare. Needs a free Cloudflare Account ID + API token (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="cloudflare",
        cloud_model_id="@cf/black-forest-labs/flux-1-schnell",
        best_for="Free cloud FLUX.1 schnell on Cloudflare's edge — fast, with a real free-tier quota (10k neurons/day). Needs a free Cloudflare Account ID + API token. Pick this over the no-key Pollinations option when you want better/known rate limits.",
        use_cases=(
            ("good",  "Free, fast schnell generation with a real free-tier quota"),
            ("good",  "Macs without the GPU/memory for local FLUX"),
            ("weak",  "Fixed output size — the schnell endpoint ignores width/height"),
            ("weak",  "Requires a (free) Cloudflare Account ID + API token in Settings"),
            ("avoid", "Private/sensitive prompts — they're sent to Cloudflare's servers"),
        ),
    ),
    ModelEntry(
        repo="together/flux-1-schnell-free",
        label="FLUX.1 schnell Free — Together (cloud)",
        family="together",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Together AI. Needs a free Together API key (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="together",
        cloud_model_id="black-forest-labs/FLUX.1-schnell-Free",
        best_for="Together AI's free FLUX.1 [schnell] endpoint — honors width/height (so the aspect-ratio presets work), 4-step schnell. Needs a free Together API key. Pick this over Cloudflare when you want custom aspect ratios in the cloud.",
        use_cases=(
            ("good",  "Free schnell with custom width/height (aspect-ratio presets apply)"),
            ("good",  "Macs without the GPU/memory for local FLUX"),
            ("weak",  "Free endpoint caps at 4 steps"),
            ("weak",  "Requires a (free) Together API key in Settings"),
            ("avoid", "Private/sensitive prompts — they're sent to Together's servers"),
        ),
    ),
)


def get_model(repo: str) -> Optional[ModelEntry]:
    for m in CATALOG:
        if m.repo == repo:
            return m
    return None


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
        # New in v1.5.0 — cloud-provider routing. Local models report
        # provider="local" and null cloud_* fields.
        "provider": m.provider,
        "cloud_provider": m.cloud_provider,
        "cloud_model_id": m.cloud_model_id,
        "is_cloud": m.is_cloud,
        # New in v1.9.0 — local inference engine (mflux vs diffusers).
        "engine": m.engine,
        "is_diffusers": m.is_diffusers,
    }


def serialize_family(f: Family) -> dict:
    return {
        "id": f.id,
        "label": f.label,
        "summary": f.summary,
        "how_to_use": f.how_to_use,
    }
