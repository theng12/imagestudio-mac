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
            "Cloudflare model and generate. Several models share the free "
            "10k-neuron/day quota: FLUX.1 schnell (fast, but fixed output size — it "
            "ignores the width/height controls), plus SDXL, SDXL-Lightning, "
            "DreamShaper, and Leonardo Lucid/Phoenix, which DO honor width/height. "
            "Runs on Cloudflare's servers — prompts leave this Mac."
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
    "gemini": Family(
        id="gemini",
        label="Google AI Studio (cloud, needs billing)",
        summary=(
            "Image generation with Google's Gemini 2.5 Flash Image ('Nano Banana'). "
            "A different model family from the FLUX/SD providers. NOTE: this is NOT "
            "free — Google's free tier allows 0 image-generation requests, so it "
            "needs a Google AI Studio / Cloud account with BILLING ENABLED."
        ),
        how_to_use=(
            "Enable billing on your Google AI Studio / Cloud account, add the API "
            "key in Settings, then pick the Gemini model and generate. Without "
            "billing you'll get a quota error (free tier = 0 image requests). Output "
            "size is chosen by the model (~1024px) — width/height + seed are ignored. "
            "Stricter content filters than the open models. Runs on Google's servers."
        ),
    ),
    "nebius": Family(
        id="nebius",
        label="Nebius AI Studio (cloud)",
        summary=(
            "Image generation via Nebius AI Studio (OpenAI-compatible). New accounts "
            "get free trial credits (no credit card) covering FLUX dev, FLUX schnell, "
            "and SDXL. Needs a free Nebius API key (set it in Settings). FLUX dev is "
            "a quality step up from the free schnell-only cloud options."
        ),
        how_to_use=(
            "Add your Nebius API key in Settings, then pick the Nebius model and "
            "generate. Honors width/height. FLUX dev gives higher quality than "
            "schnell at the cost of more trial credit per image. Runs on Nebius' "
            "servers — prompts leave this Mac."
        ),
    ),
    "huggingface": Family(
        id="huggingface",
        label="Hugging Face (cloud)",
        summary=(
            "Image generation via Hugging Face Inference Providers. Uses the SAME "
            "Hugging Face token you set for downloads — as long as that token has the "
            "'Inference Providers' permission. Free users get only a small monthly "
            "inference credit, so this is best as a bring-your-own-token option."
        ),
        how_to_use=(
            "Set a Hugging Face token (Settings → Hugging Face token) that has the "
            "'Inference Providers' permission, then pick the Hugging Face model and "
            "generate. Honors width/height. The free monthly credit is small — for "
            "heavy use, the other cloud providers go further. Runs on Hugging Face's "
            "servers — prompts leave this Mac."
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
    # ── Output-dimension capability (v1.15.0) ───────────────────────────────
    # Whether this model honors the requested width/height (i.e. the aspect-ratio
    # presets do anything). False for fixed-output endpoints — Cloudflare's FLUX
    # schnell and Gemini both ignore width/height and emit a model-chosen size.
    # Exposed in the catalog so the UI hides the aspect picker and Story Studio
    # knows not to offer ratios for these models.
    supports_custom_dimensions: bool = True
    # For fixed-output models (supports_custom_dimensions=False): the single real
    # output size the endpoint emits, used to build the one `sizes` entry. Defaults
    # to 1024×1024 when unset.
    fixed_size: Optional[tuple] = None
    # True when the cloud model needs a BILLING-enabled account, not just a key
    # (Gemini image gen: free-tier quota is 0). Surfaced as fit.state="needs_billing".
    requires_billing: bool = False
    # A repository can contain MLX weights without using the on-disk format
    # expected by this app's mflux worker. Keep such models discoverable while
    # preventing a misleading "Engine ready" state and a guaranteed load crash.
    runtime_compatible: bool = True
    runtime_note: str = ""

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
        repo="AITRADER/FLUX2-klein-4B-mlx-4bit",
        label="FLUX.2 klein 4B — MLX 4-bit",
        family="flux2-klein",
        size_gb=4.6,
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
        size_gb=8.6,
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
        repo="AITRADER/FLUX2-klein-9B-mlx-4bit",
        label="FLUX.2 klein 9B — MLX 4-bit",
        family="flux2-klein",
        size_gb=9.5,
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
        size_gb=17.9,
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
        size_gb=177.6,
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
    ModelEntry(
        repo="black-forest-labs/FLUX.1-dev",
        label="FLUX.1 dev (full)",
        family="flux1-dev",
        size_gb=57.9,
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
        size_gb=57.9,
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
    ModelEntry(
        repo="black-forest-labs/FLUX.1-Kontext-dev",
        label="FLUX.1 Kontext dev",
        family="flux1-kontext",
        size_gb=57.9,
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
    ModelEntry(
        repo="andrevp/Z-Image-Turbo-MLX",
        label="Z-Image Turbo — MLX fp16",
        family="z-image",
        size_gb=20.54,
        gated=False,
        min_unified_memory_gb=32,
        recommended_hardware="M2 Max / M3 Max with 32 GB+. Full float16 MLX conversion; 9 inference steps and guidance 0.",
        capabilities=("txt2img", "img2img"),
        best_for="Full-precision MLX conversion of Z-Image Turbo. Use when you want the publisher's highest-fidelity conversion and have enough unified memory.",
        use_cases=(
            ("good",  "Highest fidelity in andrevp's Z-Image Turbo MLX set"),
            ("good",  "Photorealism, bilingual English/Chinese text, and instruction adherence"),
            ("good",  "Apache-2.0 license and ungated download"),
            ("weak",  "20.54 GB download and a practical 32 GB memory floor"),
        ),
    ),
    ModelEntry(
        repo="andrevp/Z-Image-Turbo-MLX-8bit",
        label="Z-Image Turbo — MLX 8-bit",
        family="z-image",
        size_gb=11.37,
        gated=False,
        quantization="mlx-8bit",
        min_unified_memory_gb=16,
        recommended_hardware="16 GB+ unified memory. Downloadable, but this external packed-MLX format is not yet loadable by mflux.",
        capabilities=("txt2img", "img2img"),
        runtime_compatible=False,
        runtime_note="This repository uses external packed MLX weights without mflux quantization metadata. Loader support is required before generation.",
        best_for="Higher-fidelity quantized Z-Image Turbo conversion with a smaller footprint than fp16. Catalogued now for future loader support.",
        use_cases=(
            ("good",  "11.37 GB, roughly half the fp16 download"),
            ("good",  "8-bit quality is the safest quantized option in this set"),
            ("weak",  "Not currently loadable by Image Studio's mflux worker"),
        ),
    ),
    ModelEntry(
        repo="andrevp/Z-Image-Turbo-MLX-4bit",
        label="Z-Image Turbo — MLX 4-bit",
        family="z-image",
        size_gb=6.48,
        gated=False,
        quantization="mlx-4bit",
        min_unified_memory_gb=16,
        recommended_hardware="16 GB+ unified memory. Downloadable, but this external packed-MLX format is not yet loadable by mflux.",
        capabilities=("txt2img", "img2img"),
        runtime_compatible=False,
        runtime_note="This repository uses external packed MLX weights without mflux quantization metadata. Loader support is required before generation.",
        best_for="Balanced-size Z-Image Turbo MLX conversion. Catalogued now for future loader support.",
        use_cases=(
            ("good",  "6.48 GB download; the practical size/quality midpoint"),
            ("good",  "VAE remains float16 to preserve image decoding quality"),
            ("weak",  "Not currently loadable by Image Studio's mflux worker"),
        ),
    ),
    ModelEntry(
        repo="andrevp/Z-Image-Turbo-MLX-2bit",
        label="Z-Image Turbo — MLX 2-bit",
        family="z-image",
        size_gb=4.04,
        gated=False,
        quantization="mlx-2bit",
        min_unified_memory_gb=8,
        recommended_hardware="8 GB minimum. Smallest conversion, with noticeable quality loss; external packed-MLX format is not yet loadable by mflux.",
        capabilities=("txt2img", "img2img"),
        runtime_compatible=False,
        runtime_note="This repository uses external packed MLX weights without mflux quantization metadata. Loader support is required before generation.",
        best_for="Smallest Z-Image Turbo MLX download. Catalogued for experimentation once loader support lands; expect visible 2-bit quality degradation.",
        use_cases=(
            ("good",  "Smallest option at 4.04 GB"),
            ("good",  "Potential path for memory-constrained Apple Silicon"),
            ("weak",  "Publisher warns of noticeable 2-bit quality degradation"),
            ("weak",  "Not currently loadable by Image Studio's mflux worker"),
        ),
    ),
    ModelEntry(
        repo="Tongyi-MAI/Z-Image",
        label="Z-Image (full)",
        family="z-image",
        size_gb=20.6,
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

    ModelEntry(
        repo="stabilityai/stable-diffusion-3.5-large",
        label="Stable Diffusion 3.5 Large",
        family="sd35",
        size_gb=71.6,
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

    # ──────────── Cloud providers (v1.5.0) — free, no local GPU ────────────
    # These do NOT use mflux. provider="cloud" routes _dispatch_txt2img to the
    # providers/ registry instead of a local inference class. `repo` is a
    # synthetic stable id (never fetched from HF); /api/catalog synthesises a
    # "cached" cache state so the UI shows them ready with no download button.
    # Excluded from audit_truth.py (it audits mflux wiring only).
    # NOTE: `repo` stays "pollinations/flux" as a stable id (consumers like Story
    # Studio reference it), but Pollinations' free anonymous tier now serves only
    # NVIDIA Sana — the `model` param is normalised to it regardless of value — so
    # the label + cloud_model_id reflect that reality instead of claiming FLUX.
    ModelEntry(
        repo="pollinations/flux",
        label="Pollinations (cloud, free — no key)",
        family="pollinations",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs in the cloud. Works on any Mac; no GPU or download needed.",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="pollinations",
        cloud_model_id="sana",
        best_for="Zero-setup free image generation in the cloud — no download, no API key, no local GPU. Pollinations' free anonymous tier currently serves NVIDIA Sana, a fast and compact non-FLUX/SD model. Great for trying the app instantly or generating on a Mac that can't run the local MLX models. Your prompt is sent to Pollinations' servers.",
        use_cases=(
            ("good",  "Instant first generation — nothing to download, install, or sign up for"),
            ("good",  "A free non-FLUX/SD model (NVIDIA Sana) with zero setup"),
            ("good",  "Macs without the memory/GPU for local models (8 GB, Intel, etc.)"),
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
        supports_custom_dimensions=False,  # Workers AI schnell ignores width/height
        fixed_size=(1024, 1024),           # measured: emits 1024×1024 regardless of request
        best_for="Free cloud FLUX.1 schnell on Cloudflare's edge — fast, with a real free-tier quota (10k neurons/day). Needs a free Cloudflare Account ID + API token. NOTE: this endpoint has a fixed output size and ignores the aspect-ratio control — for custom dimensions on Cloudflare, use SDXL, SDXL-Lightning, or Leonardo Lucid/Phoenix instead.",
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
    ModelEntry(
        repo="gemini/gemini-2.5-flash-image",
        label="Gemini 2.5 Flash Image — Google (needs billing)",
        family="gemini",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Google. Needs a Google AI Studio API key WITH billing enabled (the free tier allows 0 image requests).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="gemini",
        cloud_model_id="gemini-2.5-flash-image",
        supports_custom_dimensions=False,  # Gemini chooses the output size
        fixed_size=(1024, 1024),           # Nano Banana emits ~1024×1024
        requires_billing=True,             # free-tier quota is 0 for image gen
        best_for="Google's Gemini 2.5 Flash Image ('Nano Banana') — a different model family from FLUX/SD, strong at photorealism, text rendering, and following complex instructions. IMPORTANT: this is NOT free — Google's free tier allows 0 image-generation requests, so it needs a Google AI Studio / Cloud account with BILLING ENABLED. Output size is model-chosen (~1024px); width/height + seed are ignored.",
        use_cases=(
            ("good",  "A non-FLUX/SD look — photoreal scenes and legible text in images"),
            ("good",  "Macs without the GPU/memory for local models"),
            ("avoid", "Free-only setups — Gemini image gen requires billing enabled (free tier = 0 requests)"),
            ("weak",  "Fixed model-chosen output size — width/height + seed are ignored"),
            ("weak",  "Stricter content filters than the open FLUX/SD models"),
            ("avoid", "Private/sensitive prompts — they're sent to Google's servers"),
        ),
    ),
    ModelEntry(
        repo="nebius/flux-dev",
        label="FLUX.1 dev — Nebius (cloud)",
        family="nebius",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Nebius. Needs a free Nebius API key with trial credits (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="nebius",
        cloud_model_id="black-forest-labs/flux-dev",
        best_for="FLUX.1 [dev] on Nebius AI Studio — the quality step up from the free schnell-only cloud options, honoring width/height. New accounts get free trial credits (no credit card). Pick this when you want the best cloud FLUX quality and don't mind that it draws from trial credit.",
        use_cases=(
            ("good",  "Higher-quality cloud FLUX (dev, not just distilled schnell)"),
            ("good",  "Honors width/height — aspect-ratio presets apply"),
            ("good",  "Macs without the GPU/memory for local FLUX"),
            ("weak",  "Runs on trial credits, not an unlimited free tier — dev costs more credit/image than schnell"),
            ("weak",  "Requires a (free) Nebius API key in Settings"),
            ("avoid", "Private/sensitive prompts — they're sent to Nebius' servers"),
        ),
    ),
    ModelEntry(
        repo="huggingface/flux-1-schnell",
        label="FLUX.1 schnell — Hugging Face (cloud)",
        family="huggingface",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Hugging Face. Uses your HF token (with Inference Providers permission).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="huggingface",
        cloud_model_id="black-forest-labs/FLUX.1-schnell",
        best_for="FLUX.1 [schnell] via Hugging Face Inference Providers, using the SAME Hugging Face token you already set for downloads (it must have the 'Inference Providers' permission). The free monthly inference credit is small, so this is a bring-your-own-token convenience option rather than a heavy-use free tier.",
        use_cases=(
            ("good",  "Reuses your existing Hugging Face token — nothing new to sign up for"),
            ("good",  "Honors width/height — aspect-ratio presets apply"),
            ("weak",  "Free monthly inference credit is small — runs out quickly under heavy use"),
            ("weak",  "Token must have the 'Inference Providers' permission (a download-only token gives a 403)"),
            ("avoid", "Private/sensitive prompts — they're sent to Hugging Face's servers"),
        ),
    ),
    # ── More free cloud models (v1.14.0) — variety beyond FLUX/SD ──
    ModelEntry(
        repo="cloudflare/leonardo-lucid-origin",
        label="Leonardo Lucid Origin — Cloudflare (cloud)",
        family="cloudflare",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Cloudflare. Needs a free Cloudflare Account ID + API token (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="cloudflare",
        cloud_model_id="@cf/leonardo/lucid-origin",
        best_for="Leonardo's Lucid Origin on Cloudflare's free tier — a non-FLUX/SD model family known for sharp, photoreal results and strong prompt adherence. Honors width/height (up to 2500px). A genuinely different look from the FLUX/SD cloud options, with no signup beyond the Cloudflare key you already use.",
        use_cases=(
            ("good",  "A distinct, non-FLUX/SD look — photoreal, crisp detail"),
            ("good",  "Free on Cloudflare's 10k-neuron/day quota; honors width/height"),
            ("good",  "Macs without the GPU/memory for local models"),
            ("weak",  "Shares the Cloudflare daily free quota with the other CF models"),
            ("avoid", "Private/sensitive prompts — they're sent to Cloudflare's servers"),
        ),
    ),
    ModelEntry(
        repo="cloudflare/leonardo-phoenix",
        label="Leonardo Phoenix 1.0 — Cloudflare (cloud)",
        family="cloudflare",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Cloudflare. Needs a free Cloudflare Account ID + API token (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="cloudflare",
        cloud_model_id="@cf/leonardo/phoenix-1.0",
        best_for="Leonardo's Phoenix 1.0 on Cloudflare's free tier — a non-FLUX/SD model with excellent prompt adherence and coherent compositions, including legible in-image text. Honors width/height and a negative prompt. Pairs well with Lucid Origin for a different aesthetic from the FLUX/SD options.",
        use_cases=(
            ("good",  "Strong prompt adherence + coherent layouts (good with text in images)"),
            ("good",  "Non-FLUX/SD family, free on Cloudflare; honors width/height + negative prompt"),
            ("good",  "Macs without the GPU/memory for local models"),
            ("weak",  "Shares the Cloudflare daily free quota with the other CF models"),
            ("avoid", "Private/sensitive prompts — they're sent to Cloudflare's servers"),
        ),
    ),
    ModelEntry(
        repo="cloudflare/sdxl-base",
        label="Stable Diffusion XL 1.0 — Cloudflare (cloud)",
        family="cloudflare",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Cloudflare. Needs a free Cloudflare Account ID + API token (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="cloudflare",
        cloud_model_id="@cf/stabilityai/stable-diffusion-xl-base-1.0",
        best_for="Stable Diffusion XL 1.0 on Cloudflare's free tier — the classic SDXL base model, free, and (unlike the Cloudflare FLUX schnell endpoint) it honors width/height and a negative prompt. Good for SDXL-style results and custom aspect ratios in the cloud without a Together/Nebius key.",
        use_cases=(
            ("good",  "Free SDXL that honors width/height + negative prompt"),
            ("good",  "Custom aspect ratios in the cloud without a Together/Nebius key"),
            ("good",  "Macs without the GPU/memory for local models"),
            ("weak",  "Classic SDXL — less sharp than FLUX/Leonardo on fine detail"),
            ("avoid", "Private/sensitive prompts — they're sent to Cloudflare's servers"),
        ),
    ),
    ModelEntry(
        repo="cloudflare/sdxl-lightning",
        label="SDXL-Lightning — Cloudflare (cloud)",
        family="cloudflare",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Cloudflare. Needs a free Cloudflare Account ID + API token (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="cloudflare",
        cloud_model_id="@cf/bytedance/stable-diffusion-xl-lightning",
        best_for="ByteDance's SDXL-Lightning on Cloudflare's free tier — a distilled SDXL that produces images in just a few steps, so it's the fastest free Cloudflare option. Honors width/height. Great for rapid drafts and iterating on prompts.",
        use_cases=(
            ("good",  "Fastest free Cloudflare model — few-step distilled SDXL"),
            ("good",  "Rapid drafting / prompt iteration; honors width/height"),
            ("good",  "Macs without the GPU/memory for local models"),
            ("weak",  "Few-step output trades some quality for speed"),
            ("avoid", "Private/sensitive prompts — they're sent to Cloudflare's servers"),
        ),
    ),
    ModelEntry(
        repo="cloudflare/dreamshaper-lcm",
        label="DreamShaper 8 LCM — Cloudflare (cloud)",
        family="cloudflare",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Cloudflare. Needs a free Cloudflare Account ID + API token (Settings).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="cloudflare",
        cloud_model_id="@cf/lykon/dreamshaper-8-lcm",
        best_for="Lykon's DreamShaper 8 (LCM) on Cloudflare's free tier — a popular Stable Diffusion 1.5 finetune with a stylized, illustrative, slightly painterly look. Fast (LCM, few steps) and honors width/height. A different aesthetic from the photoreal FLUX/SDXL/Leonardo options.",
        use_cases=(
            ("good",  "Stylized / illustrative / painterly look (SD 1.5 DreamShaper)"),
            ("good",  "Fast few-step LCM; free on Cloudflare; honors width/height"),
            ("weak",  "SD 1.5 base — lower native resolution/detail than SDXL/FLUX"),
            ("avoid", "Photoreal or text-in-image needs — pick Leonardo/SDXL/FLUX instead"),
            ("avoid", "Private/sensitive prompts — they're sent to Cloudflare's servers"),
        ),
    ),
    ModelEntry(
        repo="huggingface/sd3-medium",
        label="Stable Diffusion 3 Medium — Hugging Face (cloud)",
        family="huggingface",
        size_gb=0.0,
        gated=False,
        min_unified_memory_gb=0,
        recommended_hardware="None — runs on Hugging Face. Uses your HF token (with Inference Providers permission).",
        capabilities=("txt2img",),
        provider="cloud",
        cloud_provider="huggingface",
        cloud_model_id="stabilityai/stable-diffusion-3-medium-diffusers",
        best_for="Stable Diffusion 3 Medium via Hugging Face Inference Providers, using the same HF token you set for downloads (it must have the 'Inference Providers' permission). SD3's architecture differs from SDXL — better text rendering and prompt adherence. Free on the small HF monthly credit, so best for light use.",
        use_cases=(
            ("good",  "SD3 (newer architecture than SDXL) — better text + prompt adherence"),
            ("good",  "Reuses your existing Hugging Face token; honors width/height"),
            ("weak",  "Free monthly HF inference credit is small — light use only"),
            ("weak",  "Token must have the 'Inference Providers' permission (else a 403)"),
            ("avoid", "Private/sensitive prompts — they're sent to Hugging Face's servers"),
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
        or "turbo" in repo
        or "lightning" in repo
    )
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

    if m.is_cloud:
        supports_negative = m.cloud_provider in {"huggingface", "nebius"}
        if m.cloud_provider == "cloudflare":
            model_id = (m.cloud_model_id or "").lower()
            supports_negative = "flux" not in model_id and "lucid" not in model_id
        controls = {
            "prompt": True,
            "aspect_ratio": m.supports_custom_dimensions,
            "negative_prompt": supports_negative,
            "steps": False,
            "guidance": False,
            "seed": m.cloud_provider != "gemini",
            "batch": True,
            "image_strength": False,
            "runtime_quantization": False,
            "loras": False,
        }
        summary = "Hosted model: only settings accepted by this provider are shown."
    else:
        controls = {
            "prompt": not is_upscaler,
            "aspect_ratio": m.supports_custom_dimensions and not is_upscaler,
            "negative_prompt": not is_upscaler and not distilled,
            "steps": not is_upscaler,
            "guidance": not is_upscaler and not distilled,
            "seed": not is_upscaler,
            "batch": True,
            "image_strength": not is_upscaler and any(c in m.capabilities for c in ("img2img", "edit")),
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

    # ── Cloud-credential readiness (v1.11.x) ────────────────────────────────
    # A cloud model is only truly "ready" when its required API credential is
    # configured. Local models need no cloud credential → always ok. For a
    # keyed cloud model with the credential MISSING we (a) report
    # cloud_credentials_ok=false (the machine-readable signal Story Studio and
    # any other consumer gate on) and (b) override the hardware `fit` verdict to
    # state="needs_key" so the existing fit chip surfaces it with no extra UI
    # logic. Pollinations needs no key → always ok.
    cloud_credentials_ok = True
    cloud_provider_label = None
    cloud_signup_url = None
    if m.is_cloud:
        try:
            from . import settings
            cloud_provider_label = settings.cloud_provider_label(m.cloud_provider)
            cloud_signup_url = settings.cloud_signup_url(m.cloud_provider) or None
            cloud_credentials_ok = settings.cloud_credentials_ok(m.cloud_provider)
            if not cloud_credentials_ok:
                fit = {
                    "state": "needs_key",
                    "label": "Needs API key",
                    "hint": settings.cloud_credentials_hint(m.cloud_provider),
                    "actual_gb": None,
                    "required_gb": None,
                }
            elif m.requires_billing:
                # Credential is set, but the provider needs a billing-enabled
                # account (Gemini image gen: free-tier quota is 0). Surface it
                # the same way as needs_key so the UI/Story Studio can gate it.
                fit = {
                    "state": "needs_billing",
                    "label": "Needs billing",
                    "hint": (
                        "Requires billing enabled on your Google AI Studio / Cloud "
                        "account — the free tier allows 0 image-generation requests."
                    ),
                    "actual_gb": None,
                    "required_gb": None,
                }
        except Exception:
            # If settings can't be read for any reason, fail safe to not-ready
            # for keyed providers (so we never falsely claim ready).
            cloud_credentials_ok = (m.cloud_provider == "pollinations")

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
        # New (v1.11.x) — true when the model's required cloud credential is set.
        # Always true for local models and Pollinations (no key needed); false
        # for Cloudflare/Together when their key/token is absent. Downstream
        # consumers (Story Studio) gate cloud-model readiness on this.
        "cloud_credentials_ok": cloud_credentials_ok,
        # New (v1.12.0) — provider display name ("Together AI") + the URL where a
        # user gets the credential, so the UI can link straight from the
        # "needs API key" state. Null for local models.
        "cloud_provider_label": cloud_provider_label,
        "cloud_signup_url": cloud_signup_url,
        # New (v1.15.0) — does the model honor width/height? False for fixed-size
        # endpoints (Cloudflare FLUX schnell, Gemini). Story Studio + the UI use
        # this to hide/disable the aspect-ratio picker. requires_billing flags a
        # cloud model that needs a billing-enabled account, not just a key.
        "supports_custom_dimensions": m.supports_custom_dimensions,
        "requires_billing": m.requires_billing,
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
        "generation_profile": generation_profile(m),
    }


def serialize_family(f: Family) -> dict:
    return {
        "id": f.id,
        "label": f.label,
        "summary": f.summary,
        "how_to_use": f.how_to_use,
    }
