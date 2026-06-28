# Changelog — Image Studio KH

All notable changes to Image Studio KH are documented here.

Versioning follows [Semantic Versioning](https://semver.org/) with this project-specific interpretation:

- **MAJOR** (1.x.x → 2.x.x) — breaking change. Re-install required.
- **MINOR** (1.1.x → 1.2.x) — new engine / new feature / new model family. **Re-run "Install Generation"** to pick up new Python deps.
- **PATCH** (1.2.0 → 1.2.1) — bugfix / UI tweak / catalog entry within an existing family. **Just run Update** from the Pinokio sidebar.

---

## [1.14.0] — 2026-06-29

### Added — six more free cloud models (variety beyond FLUX/SD), now 12 total

The catalog now ships **twelve** cloud models across several families. Researched the genuinely-free rosters of all six providers (mid-2026) and added the ones that are actually free — prioritizing **non-FLUX/SD** families. (Qwen-Image, Imagen, Ideogram, Kolors, HiDream, Seedream are all paid/credit-gated now, so they were deliberately **not** added — no broken "free" entries.)

**New models** (no new providers, no new deps — all reuse the existing stdlib HTTP path):

| `repo` | Provider | Family | Credential |
|---|---|---|---|
| `cloudflare/leonardo-lucid-origin` | Cloudflare | **Leonardo Lucid** (non-FLUX/SD, photoreal) | Cloudflare key |
| `cloudflare/leonardo-phoenix` | Cloudflare | **Leonardo Phoenix** (non-FLUX/SD, prompt adherence) | Cloudflare key |
| `cloudflare/sdxl-base` | Cloudflare | **SDXL 1.0** (free; honors width/height + negative prompt) | Cloudflare key |
| `cloudflare/sdxl-lightning` | Cloudflare | **SDXL-Lightning** (fastest free CF model) | Cloudflare key |
| `cloudflare/dreamshaper-lcm` | Cloudflare | **DreamShaper 8 LCM** (SD1.5, stylized) | Cloudflare key |
| `huggingface/sd3-medium` | Hugging Face | **Stable Diffusion 3 Medium** | reuses `hf_token` |

### Changed — Cloudflare provider generalized; Pollinations relabelled to Sana

- **Cloudflare provider** now serves any of its text-to-image models (not just FLUX schnell). It builds the right body per model (FLUX = `prompt`+`steps`, fixed size; the SD/Leonardo models honor `width`/`height`/`num_steps`/`seed`, and `negative_prompt` where supported — Leonardo Lucid omits it) and decodes **both** response shapes: base64-in-JSON (FLUX schnell, Leonardo Lucid) and raw image bytes (SDXL, Lightning, DreamShaper, Phoenix). Model IDs + response shapes verified against Cloudflare's docs.
- **`pollinations/flux` relabelled** to "Pollinations (cloud, free — no key)" with `cloud_model_id: "sana"`. Pollinations' free anonymous tier now serves **only NVIDIA Sana** — `model=flux`/`turbo`/`sana` all return the byte-identical image (verified live) — so the entry now honestly reflects that it's Sana. The `repo` id stays `pollinations/flux` for stability (consumers reference it).

### Verification
- All 12 cloud models report correctly in `/api/catalog`. New endpoints + request/response shapes validated live (dummy key → auth error, not a 404/shape error; Cloudflare slugs confirmed against docs). A real end-to-end generation through the **Pollinations (Sana)** pipeline returned a valid JPEG.

### Notes
- MINOR — new model families, **no new Python deps** (cloud path is stdlib `urllib`). A plain **Update** is enough.

---

## [1.13.0] — 2026-06-29

### Added — three new free / free-trial cloud providers

Image Studio now ships **six** cloud (`provider: "cloud"`) models, up from three. All run through the same stdlib-only HTTP path (no extra deps, no `Install Generation` needed) and the same credential-gating + provider-link UI added in 1.12.0.

| New model (`repo`) | Provider | Credential | What it adds |
|---|---|---|---|
| `gemini/gemini-2.5-flash-image` | Google AI Studio | `gemini_api_key` | **Nano Banana** — permanent free tier, **no credit card**, ~500 img/day. A non-FLUX/SD model family (strong photoreal + text-in-image). Output size is model-chosen; width/height + seed are ignored. |
| `nebius/flux-dev` | Nebius AI Studio | `nebius_api_key` | **FLUX.1 dev** — a quality step up from the free schnell-only options. Honors width/height. Free trial credits, no card. |
| `huggingface/flux-1-schnell` | Hugging Face | reuses **`hf_token`** | FLUX.1 schnell via HF Inference Providers, using the **same token you already set for downloads** (must have the *Inference Providers* permission). No new field. Small monthly free credit — a bring-your-own-token option. |

- **New providers:** `app/backend/providers/{gemini,nebius,huggingface}.py`, registered in the providers registry. Endpoints + request shapes were validated live against each real API (a dummy key returns an auth error, not a 404/shape error).
- **Settings:** new `gemini_api_key` / `nebius_api_key` fields (masked in `/api/settings`, entered in **Settings → Cloud provider keys**). Hugging Face needs no new field — it reads the existing HF token.
- **Catalog:** each new model carries the full `fit` / `cloud_credentials_ok` / `cloud_provider_label` / `cloud_signup_url` contract, so they gate and link exactly like the existing cloud models. Because the HF model reuses `hf_token`, it reports ready as soon as a Hugging Face token is set.
- **Errors are explicit:** a Hugging Face token without the *Inference Providers* permission returns a clear 403 hint; Gemini content blocks and Nebius/Together URL-vs-base64 responses are all handled.

### Notes
- MINOR — new model families, but **no new Python deps** (cloud path is stdlib `urllib`), so a plain **Update** is enough; no need to re-run *Install Generation*.

---

## [1.12.0] — 2026-06-28

### Added — direct "get your key" links for every cloud provider

Each cloud model now carries, in `GET /api/catalog`:
- **`cloud_provider_label`** — the provider's display name (`"Pollinations"`, `"Cloudflare Workers AI"`, `"Together AI"`); null for local models.
- **`cloud_signup_url`** — the page where the user gets that provider's credential (or learns about it, for keyless Pollinations); null for local models.

In the UI:
- Every cloud model card shows a quiet **via &lt;provider&gt; ↗** link that opens the provider's API page in a new tab.
- The Generate-tab "needs an API key" banner now offers a direct **Get a &lt;provider&gt; key ↗** link alongside the "open Settings" link, so you can jump straight to the dashboard instead of hunting for it.
- (The Settings page already had per-provider get-key links; those are unchanged.)

### Fixed — cloud models no longer report "ready" without their API credential

Cloud-proxied models reported `fit.state: "ok"` / "fits comfortably" and `cache.state: "cached"` regardless of whether their required credential was configured — so a user with no Together/Cloudflare key saw them as ready, picked one, and only hit the failure at generate time.

**New machine-readable signal in `GET /api/catalog`** (per model):

- **`cloud_credentials_ok`** (boolean) — `true` when the model's required credential is set; mirrors exactly what the provider checks before a request, so "ok" means "won't fail for a missing credential." Always `true` for **Pollinations** (needs none) and for all **local** models; `false` for **Cloudflare** / **Together** when their key/token is absent. Cloudflare needs *both* `account_id` + `api_token` — one alone stays `false`.
- **`fit.state: "needs_key"`** + **`fit.hint`** (e.g. *"Add your Together API key in Settings to use this model."*) when a keyed cloud model's credential is missing — so consumers can gate off the existing `fit` object with no extra logic.

`is_cloud` / `cloud_provider` / `cloud_model_id` are unchanged. `cache.state` stays `"cached"` for cloud models (they genuinely need no download) — readiness now flows through `cloud_credentials_ok` / `fit.state`.

### Image Studio UI now honors it
- Model cards show **☁ cloud ready** vs **🔑 needs API key** (click → Settings) instead of the local-engine chips, and the fit chip renders **🔑 needs key**.
- A credential-less cloud model is no longer selectable-to-generate (`isModelReady` gates on `cloud_credentials_ok`); the Generate tab shows a "needs an API key — open Settings, or use Pollinations" banner instead of a misleading "install packages" one.

### Alignment with Story Studio
Story Studio consumes `GET /api/catalog` and treated every `is_cloud` model as ready. It can now gate on `cloud_credentials_ok` (or `fit.state === "needs_key"`) to show credential-missing cloud models as "needs API key" / unselectable. Pollinations remains always-available (no credential).

### Notes
- PATCH — additive API field + UI fix, no new deps. `Update`, then restart the server (or it auto-restarts on Update if running as the launchd service) so the backend reloads.

---

## [1.11.0] — 2026-06-26

### Added — three more diffusers models (broadening the engine)

All ungated, MPS-friendly, standard diffusers pipelines (verified the pipeline
classes resolve + repos exist/ungated):

- **PixArt-Σ XL 1024** (`PixArt-alpha/PixArt-Sigma-XL-2-1024-MS`,
  `PixArtSigmaPipeline`) — lightest diffusers model, small download, low memory.
- **Lumina-Image 2.0** (`Alpha-VLLM/Lumina-Image-2.0`, `Lumina2Pipeline`) — ~2B
  flow DiT with a Gemma text encoder; strong multilingual prompts.
- **AuraFlow v0.3** (`fal/AuraFlow-v0.3`, `AuraFlowPipeline`) — ~6.8B open flow
  model; higher capacity, heavier.

Each sets an explicit `diffusers_pipeline` class (more robust than relying on
`AutoPipeline` auto-resolution). HiDream-I1 was evaluated but held back (17B +
Llama text encoder = higher MPS risk; wants a dedicated test first).

### Notes
- MINOR — new model families on the existing diffusers engine. **No new Python
  deps**. All ungated (no HF token/license). Truth audit passes clean. Wiring +
  diagnostics verified; a real end-to-end MPS generation test (PixArt-Σ) was run
  separately to validate the shared `_generate_diffusers` worker.

---

## [1.10.0] — 2026-06-26

### Added — Sana (diffusers engine) + Ideogram 4 feasibility verdict

- **Sana 1600M** (`Efficient-Large-Model/Sana_1600M_1024px_diffusers`,
  `engine="diffusers"`, txt2img) — NVIDIA's efficient linear-attention DiT.
  **Ungated** (Apache), MPS-friendly, lighter/faster than SD3.5 — the easiest
  diffusers model to actually run on a Mac, and a second proof the engine
  generalizes beyond SD3.5. Verified: diffusers `SanaPipeline` resolves, repo
  exists + ungated, catalog/diagnostics wiring clean.

### Not added — Ideogram 4 (cannot run on Apple MPS)

Investigated for this engine and **ruled out on Apple Silicon**, with evidence:
- All Ideogram 4 weights are quantized — **nf4** (needs CUDA-only `bitsandbytes`,
  no macOS build) or **fp8**.
- Probed locally: `torch.float8_e4m3fn` is **not a supported MPS dtype** in torch
  2.12 (can't even move fp8 weights to MPS), so the fp8 path is dead too.
- The only known-working Mac path is an **unreleased mflux branch** (MLX-forge +
  `mflux-generate-ideogram4` with `MLXBits/ideogram-4-mlx-q8`), which we won't
  install over the stable mflux 0.17.5 (risks the working FLUX/Qwen/FIBO/Z-Image
  /SeedVR2 models). Revisit when mflux ships **native MLX Ideogram support** —
  then it's a clean mflux catalog add.

### Notes
- MINOR — new model family on the existing diffusers engine. **No new Python
  deps** (torch/diffusers landed in 1.9.0). Sana is ungated, so it downloads
  without an HF token/license. Truth audit passes clean.

---

## [1.9.0] — 2026-06-26

### Added — second local engine: diffusers (PyTorch/MPS) + Stable Diffusion 3.5

The big one: a second local inference engine alongside mflux/MLX, so the app can
run models mflux has no class for (SD3.5, Sana, Ideogram 4, …).

- **`engine` field on every model** — `"mflux"` (default) or `"diffusers"`. Cloud
  models are unaffected (`provider="cloud"` short-circuits before engine dispatch).
- **Diffusers worker** (`_generate_diffusers`) — loads a `DiffusionPipeline` from
  the app's HF cache (same `HF_HOME` as downloads), runs on Apple **MPS** (bf16),
  and caches one pipeline in-process so back-to-back generations skip the
  multi-GB reload. Routed by `engine` in `_dispatch_txt2img`, before mflux family
  dispatch.
- **Phase A model: Stable Diffusion 3.5 Large** (`stabilityai/stable-diffusion-3.5-large`,
  `engine="diffusers"`, txt2img). Gated — needs HF token + license. Behaves like
  any local model in the UI (download → appears in the txt2img dropdown); **no
  frontend changes needed**.
- **Install** — `requirements-generation.txt` gains `torch`, `diffusers`,
  `accelerate`, `protobuf`. Diagnostics tracks the diffusers engine
  (`_DIFFUSERS_FAMILIES`); `audit_truth.py` excludes diffusers entries (it audits
  mflux wiring only).

### Notes
- MINOR — new engine. **Re-run "Install Generation"** to pick up torch/diffusers,
  then download SD3.5 (accept its HF license + set your token first). Verified:
  compile, truth audit (clean), and — on Apple Silicon — the diffusers import
  path, MPS/bf16 availability, and SD3.5 pipeline resolution. A full end-to-end
  generation needs the gated ~20 GB SD3.5 download, so it's verified up to model
  load.
- **Phase B (next):** Ideogram 4 (custom `Ideogram4Pipeline`, `trust_remote_code`)
  + more diffusers models (Sana, HiDream, PixArt, …).

---

## [1.8.0] — 2026-06-26

### Added — RAM planner: interactive memory slider + live "Best for your RAM" picks (Models tab)

The Models tab gained a **hardware planner** so you can size models to a machine you don't own yet — set the unified-memory budget and every fit chip re-scores instantly.

- **RAM slider + numeric entry + tier presets** (8 / 16 / 24 / 32 / 48 / 64 / 128 / 256 / 512 GB). Defaults to your detected RAM; drag/type to *preview* a different Mac (e.g. plan an M3 Ultra 512 GB before buying it). A `↩ My Mac` button snaps back to detected. The chosen budget persists across reloads.
- **Live hardware fit** — per-card fit chips (✓ fits / ⚠ tight / ✗ over budget) are scored **client-side** against the slider value via `fitFor()`/`effectiveRam`, with no server round-trip.
- **✨ Best for your RAM** — surfaces the best model per lane that still fits the budget: **best quality** (heaviest), **fastest/lightest**, and **best for editing**. At 8 GB it favours the light SD-class models; at 64 GB+ it upgrades to the large FLUX-class models.
- **Segmented "RAM fit" filter** (All / ✓ Fits / ⚠ Tight / ✗ Over), mirroring the Chat Studio model-tab control for a consistent look across the suite. The old binary "Fits my Mac" chip is folded into this.

**Frontend-only — no new Python dependencies. A plain _Update_ from the Pinokio sidebar is enough (no re-install / Install Generation needed).**

---

## [1.7.0] — 2026-06-26

### Added — SeedVR2 upscaler (local)

- **SeedVR2 7B** (`numz/SeedVR2_comfyUI`) — a diffusion image **upscaler /
  restorer**, wired via mflux's `SeedVR2` class. It lives in the
  **Image-to-Image** tab: attach an image and generate, and it reconstructs a
  higher-resolution version (fixed ~2× for now). Self-contained (one repo, no
  base model). NOT txt2img — the prompt / guidance / steps / strength controls
  are ignored. Heavy 7B model; best on a high-memory Mac (M3 Ultra ideal).

### Deferred — FLUX.1 Redux
- Redux was scoped as a "quick win" alongside SeedVR2, but mflux's Redux loads
  the FLUX.1-dev **base** *plus* the Redux **adapter** repo (two downloads),
  which the current single-repo download/cache flow doesn't cover. Deferred
  until two-repo handling is added rather than ship a model that fails at
  generation time.

### Notes
- MINOR — new model family, **no new Python deps** (SeedVR2 ships in the
  installed mflux 0.17.5). Plain **Update**. Truth audit passes clean. Wiring
  verified (catalog + dispatch + mflux class/config imports); a full end-to-end
  run requires downloading the SeedVR2 repo first.

---

## [1.6.0] — 2026-06-26

### Added — two more cloud providers: Cloudflare Workers AI + Together AI

Builds on the v1.5.0 cloud-provider layer with two **keyed** free providers:

- **Cloudflare Workers AI** (`cloudflare/flux-1-schnell`) — FLUX.1 schnell on
  Cloudflare's edge. Free tier (10k neurons/day). Needs a free Account ID + API
  token. Note: the Workers AI schnell endpoint outputs a fixed size (ignores
  width/height).
- **Together AI** (`together/flux-1-schnell-free`) — the FLUX.1 [schnell] Free
  endpoint. Free with a (free) Together API key; honors width/height (so the
  aspect-ratio presets apply), capped at 4 steps.

Supporting changes:
- **Provider credentials** — `CloudProvider.generate()` now takes a `config`
  dict (resolved from settings); providers declare `required_config`. New
  settings keys `cloudflare_account_id`, `cloudflare_api_token`,
  `together_api_key`, surfaced **masked** via `/api/settings` (raw values never
  returned).
- **Settings UI** — a new "Cloud provider keys" card on the Settings tab with
  show/hide inputs, per-provider "how to get a key" help, save + clear-all.
- Providers remain **stdlib-only** (urllib + base64), so the cloud path still
  works without the heavy generation install.

### Notes
- MINOR — new feature, **no new Python deps**. Plain **Update** is enough. The
  two new models need their key set in Settings before they'll generate
  (Pollinations from v1.5.0 still needs no key). Truth audit passes clean.

---

## [1.5.0] — 2026-06-26

### Added — FLUX.1 Krea dev (local) + Pollinations cloud generation

- **FLUX.1 Krea dev** — new local model family (`flux1-krea`). BFL × Krea's
  photorealism-tuned FLUX.1 dev; less "AI-looking" than stock FLUX.1 dev
  (more natural skin/lighting/texture). Rides the existing mflux `Flux1` class
  via `ModelConfig.krea_dev()`, so it reuses the `_generate_flux1` worker —
  txt2img + img2img, gated (HF token + license), ~24 GB.
- **Cloud providers** — new `provider="cloud"` model class routed through a new
  `app/backend/providers/` registry instead of mflux. First provider:
  **Pollinations FLUX** (`pollinations/flux`) — free, no API key, no download,
  no local GPU. Works on any Mac (even without the heavy generation install,
  since the cloud path is a stdlib HTTP call). Prompts are sent to
  Pollinations' servers; output is best-effort and rate-limited.
  - Cloud models report a synthetic `cached` state so the existing UI shows
    them ready with no download button; `start_txt2img` skips the mflux/cache
    gates for them. Cloud entries are excluded from `audit_truth.py` (it audits
    mflux wiring only).

### Notes
- MINOR — new model family + new feature. **No new Python deps** (Krea uses the
  already-installed mflux 0.17.5; the cloud provider is stdlib-only), so a plain
  **Update** is enough — no need to re-run Install Generation. Truth audit
  passes clean (no drift).

---

## [1.4.2] — 2026-06-06

### Added — auto-restart on Update + "Repair · take over port" button
- **Update restarts the service:** `update.js` now ends with a `restart_service.sh` step gated on `{{exists('service/.installed')}}`, so an installed service picks up new backend code automatically after Update (no-op otherwise).
- **"Repair · take over port"** menu item (service mode) re-runs the installer to fix any wedged/conflicting state in one click.

### Fixed — take-over no longer risks killing connected clients
The v1.4.1 port take-over used `lsof -ti tcp:PORT`, which also matches connected clients (browser tab / Pinokio webview / SSE). Now filtered with `-sTCP:LISTEN` so only the listening server is targeted. Verified live.

### Notes
- PATCH — service scripts + update.js. Mirrored across all 3 KH apps (Voice 1.6.2, Music 1.2.2). `Update`, then re-run Install Service once.

---

## [1.4.1] — 2026-06-06

### Fixed — "Check Service Status" clarity + double-run conflict detection

- The watchdog is *periodic* (fires ~1s every 60s), so "not running" between checks is normal — the status now says so instead of a scary raw dump. Server line is now `✓ loaded · running (pid N)`.
- **Port-conflict detection:** if you run both Pinokio's **Start** and the service, they fight for port 47868 and the service crash-loops (`[Errno 48] address already in use`). The status script now detects this and explains it.
- **Install now takes over the port:** `Install as Startup Service` stops whatever's already on the port (your Pinokio "Start") before starting the service, so "Start, then Install Service" Just Works — no crash loop, no manual `pkill`. Uninstalling doesn't auto-restart the Pinokio instance.

### Notes
- PATCH — service scripts only. Mirrored across all 3 KH apps (Voice 1.6.1, Music 1.2.1). `Update`, then re-run Install Service once.

---

## [1.4.0] — 2026-06-06

### Added — one-click "Install as Startup Service" (always-on server + self-healing)

For running this on a headless/server Mac (e.g. a fleet reached over Tailscale), the app can now be a real background service instead of opening Pinokio and clicking Start each time.

New sidebar button **❤️ Install as Startup Service** installs a macOS **launchd LaunchAgent** that:

- runs the server (`serve.sh` → uvicorn on **47868**) **at login**, so it returns automatically after a reboot;
- **restarts on crash** via launchd `KeepAlive`;
- ships a **health watchdog** (`watchdog.sh`, every 60s) that hits `/api/health` and relaunches the server if it hangs.

No sudo needed. The button toggles to **Startup Service: ON — click to remove**. Service logs go to `logs/service/`.

New files: `serve.sh`, `watchdog.sh`, `install_service.sh`, `uninstall_service.sh`, `service.js`, `unservice.js` (self-locating; the per-machine `service/.installed` marker is gitignored).

### Service mode — manage it from the sidebar
Once installed, launchd owns the server (Pinokio doesn't see it as "running"), so the sidebar switches to a **service-mode menu** — no conflicting "Start" button:

- **Open UI / Open in Browser** — straight to the running server on port 47868 (no Pinokio Start needed).
- **Check Service Status** (`status_service.sh`) — launchd state + live `/api/health` + recent log, so you know it's actually up.
- **Restart Service** (`restart_service.sh`) — manual `launchctl kickstart -k`.
- **Service Logs** + **Uninstall Startup Service** (brings the normal Start button back).

Extra files: `status_service.sh`, `restart_service.sh`, `service_status.js`, `service_restart.js`.

### Docs — power-cut recovery, explained
The install button prints, and the README documents, the three one-time **admin** settings for full hands-off recovery after a power outage (you do these once per machine):
1. `sudo pmset -a autorestart 1` — power on automatically when electricity returns.
2. **Auto-login** — required so the Apple GPU (Metal/MLX) is available; a pre-login daemon can't use it.
3. **FileVault off** — otherwise reboot halts at the encrypted-disk password screen.

### Notes
- MINOR bump — new feature, no new deps. `Update` from the sidebar, then click **Install as Startup Service** on each Mac.
- Use the **service OR** Pinokio's **Start** — not both (they share port 47868).
- Mirrored across all 3 KH apps (Voice 1.6.0, Music 1.2.0).

---

## [1.3.2] — 2026-05-24

### Fixed — Cancelled queued jobs no longer pop back to "queued" in the UI

Follow-up to v1.3.1. The backend cancel was setting `state = "cancelled"` correctly, but the worker thread had a redundant `job.state = "queued"` statement OUTSIDE the `_GEN_LOCK` block. That created a TOCTOU race:

1. `submit_job()` → job created with `state="queued"` (dataclass default), worker thread `start()`-ed
2. User clicks Cancel before the worker thread is scheduled → `cancel()` flips `state="cancelled"` + sets `cancel_event`
3. Worker thread finally gets CPU time → `job.state = "queued"` ← **CLOBBERS THE CANCEL**
4. Worker blocks on `_GEN_LOCK` waiting for the running job to finish
5. SSE broadcasts the (re-)queued state → UI re-shows the cancelled card with its X-Cancel button
6. Eventually (after the running job completes — could be minutes) the worker acquires the lock, sees `cancel_event.is_set()`, and finally settles `state="cancelled"`

User-visible symptom: clicking Cancel showed the "✓ Cancelled — Queued job removed" toast, but the queue card stayed put for the full duration of whatever was running ahead of it.

Fix: removed the redundant `job.state = "queued"` from all worker entries (`_run_txt2img` + the edit worker). The dataclass default already initializes `state="queued"`, so the line was dead code — except in the cancel-race case where it was actively destructive.

### Mirrored across all 3 apps

Same one-line race + same fix:

- Voice Studio KH → v1.1.7 (`_run_txt2speech`)
- Music Studio KH → v1.1.9 (`_run_txt2music`)

### Notes

- PATCH bump — UX bugfix, no schema or dependency changes. Run `Update` from the Pinokio sidebar.

---

## [1.3.1] — 2026-05-24

### Fixed — Cancel button works for queued jobs (and explains itself for running jobs)

After the queue UX from v1.2.3 landed, queued jobs piled up but clicking ✕ Cancel on them did nothing visible. Root cause: `manager.cancel()` only set `cancel_event`, but the queued worker thread was blocked on `_GEN_LOCK` waiting for the running job to finish — so it couldn't observe the event for minutes. The UI stayed stuck on "queued."

Fix is two-part:

- **Backend (`generation.py`):** `manager.cancel()` now immediately flips a queued job's `state` → `"cancelled"` + persists, so the next SSE snapshot (~1 s) reflects it. The worker still safely no-ops when it eventually wakes up and sees `cancel_event.is_set()` — it never overwrites the cancelled state.
- **Frontend (`app.js`):** `cancelPending()` now distinguishes queued vs running and pushes the right toast:
  - **Queued** → "✓ Cancelled — Queued job removed."
  - **Running** → "⏸ Cancel signal sent" + explains that mflux's `generate_image()` is a blocking call that doesn't honor mid-flight cancellation, so the result will be discarded after generation finishes. (Honest about the limitation instead of pretending the click did nothing.)

### Mirrored across all 3 apps

Per the "apply UX wins to all 3 apps" rule:

- Voice Studio KH → v1.1.6 (toast wording references mlx-audio TTS engines)
- Music Studio KH → v1.1.8 (toast wording references MusicGen / Stable Audio / Bark)

### Notes

- PATCH bump — UX bugfix, no schema or dependency changes. Run `Update` from the Pinokio sidebar.

---

## [1.3.0] — 2026-05-24

### Added — 4 new wired families from mflux 0.17.5

After auditing mflux's actual module list (not just guessing from external knowledge), found 4 entire families it natively supports that I'd missed. All wired in this release using on-the-fly mflux quantization (works on 16 GB Macs):

- **Qwen-Image (txt2img)** — `Qwen/Qwen-Image` via `QwenImage` class. Strong on Chinese prompts + non-Latin text rendering in images. Apache-2.0.
- **Qwen-Image Edit** — `Qwen/Qwen-Image-Edit-2509` via `QwenImageEdit`. Ungated instruction-edit alternative to FLUX.1 Kontext. Worked the same way as Kontext (image + prompt) but no HF token / license acceptance needed.
- **FIBO family** — BRIA AI's commercial-safe family (training data is fully licensed). 4 variants wired:
  - `briaai/Fibo-lite` (recommended for daily use)
  - `briaai/FIBO` (full quality)
  - `briaai/Fibo-Edit` (instruction editing)
  - `briaai/Fibo-Edit-RMBG` (dedicated background removal)
- **Z-Image family** — Tongyi Lab's stylized-output models. 2 variants:
  - `Tongyi-MAI/Z-Image-Turbo` (4-8 steps, recommended)
  - `Tongyi-MAI/Z-Image` (20-30 steps, full quality)
  - Strong on illustration / anime / painterly output where FLUX leans photographic.

### Removed — HiDream + Shuttle + FLUX.1 lite (5 entries)

These were roadmap-only entries. mflux has no inference classes for them — they'd require installing the `diffusers` library + writing diffusers-based pipelines as a second backend. Per the v1.2.5 rule (don't keep entries that can't work), removed. If a future mflux release adds them, re-add Family + ModelEntry rows.

### Changed

- **`_WIRED_FAMILIES`** now lists 8 families: flux2-klein, flux1-schnell, flux1-dev, flux1-kontext, qwen-image, qwen-edit, fibo, z-image. Only flux2-dev remains roadmap (no mflux class yet).
- **Catalog goes 17 → 18 entries** but the SHAPE shifted dramatically:
  - Before: 4 wired families / 6 roadmap families
  - After: **8 wired families / 1 roadmap family**
- **Existing qwen-image entry** swapped from `mlx-community/Qwen-Image-4bit` to the canonical `Qwen/Qwen-Image` repo with on-the-fly quantization. Avoids the same MLX-format-incompatibility risk that bit us with the madroid repos.

### Investigation that prevented mistakes

User asked about wiring HiDream + Shuttle + Flux.1-lite. Direct inspection of mflux's `models/` directory found:
- ✅ `qwen/` (with txt2img + edit variants)
- ✅ `fibo/` (with txt2img + edit + edit-rmbg)
- ✅ `z_image/`
- ❌ no `hidream/`, `shuttle/`, or `flux_lite/`

So instead of wiring what was asked, I told the truth: HiDream/Shuttle/Flux-lite need a separate library (diffusers). But I found 4 families nobody mentioned that ARE in mflux and wired those instead. Net gain: 7 newly-wired model entries vs the 0 that would have happened if I'd tried to force HiDream et al.

### Truth audit

```
$ python3 audit_truth.py --strict
  Catalog families       :  9
  _WIRED_FAMILIES claims :  8
  Dispatch handles       :  8
  Dispatch raises NotImpl:  1  (flux2-dev only)
  ✓ NO DRIFT
```

### Notes

- MINOR bump (1.2.x → 1.3.x) — 4 new wired families, no new Python deps (mflux already includes all the classes), no breaking changes.
- Just run `Update` from the Pinokio sidebar; no re-install needed.
- All new entries use on-the-fly `quantize=4` — large downloads (10-20 GB each) but they fit memory-wise on 16 GB Macs.

---

## [1.2.5] — 2026-05-24

### Removed — 6 catalog entries that weren't earning their slot

Catalog goes 23 → 17 entries, all 10 families still represented.

**Broken (don't work with current mflux):**
- `madroid/flux.1-schnell-mflux-4bit` — older MLX quantization format, fails on T5 dequantize
- `madroid/flux.1-dev-mflux-4bit` — same issue

**Foundation models for fine-tuning (not generation):**
- `black-forest-labs/FLUX.2-klein-base-4B` (full)
- `AITRADER/FLUX2-klein-base-4B-mlx-4bit`
- `AITRADER/FLUX2-klein-base-4B-mlx-8bit`
- `black-forest-labs/FLUX.2-klein-base-9B` (full)

Every `use_cases` entry for the klein-base models said some version of "avoid for everyday generation, use the non-base klein instead." Keeping them just added decision noise to the picker. If/when LoRA fine-tuning becomes a feature of this launcher, they get re-added behind a dedicated fine-tuning UI.

### How to recover disk space for the removed entries

The cache folders are still on disk — the launcher just doesn't reference them anymore. To reclaim the 6 GB from madroid + however much you downloaded of klein-base:

```
# Find the orphaned folders
ls ~/pinokio/api/imagestudio-mac/cache/HF_HOME/hub/ | grep -E "madroid|klein-base"

# Delete what you don't need (verify list first!)
rm -rf ~/pinokio/api/imagestudio-mac/cache/HF_HOME/hub/models--madroid--*
rm -rf ~/pinokio/api/imagestudio-mac/cache/HF_HOME/hub/models--*--FLUX2-klein-base-*
rm -rf ~/pinokio/api/imagestudio-mac/cache/HF_HOME/hub/models--*--FLUX.2-klein-base-*
```

Or use the HF Cache sidebar item to browse + delete manually.

### Per-family after the prune

| Family | Entries | Wired |
|---|---|---|
| flux2-klein | 6 | ✓ |
| flux1-schnell | 1 (full BFL, on-the-fly quant) | ✓ |
| flux1-dev | 1 (full BFL, on-the-fly quant) | ✓ |
| flux1-kontext | 1 | ✓ |
| flux1-lite | 1 | roadmap |
| flux2-dev | 1 | roadmap |
| hidream | 2 | roadmap |
| qwen-image | 1 | roadmap |
| qwen-edit | 1 | roadmap |
| shuttle | 2 | roadmap |

Truth-audit reports ✓ NO DRIFT.

### Notes

- PATCH bump — pure catalog cleanup, no code change, no behavior change for the entries that remained.
- If you have a 32 GB+ Mac later, the larger entries (FLUX.2 dev, klein 9B 8-bit) still cover that ground. You're not losing options at any hardware tier — just losing the broken ones and the fine-tuning bases.

---

## [1.2.4] — 2026-05-24

### Fixed — actionable error for the `madroid/*-mflux-4bit` MLX-format incompatibility

The `madroid/flux.1-schnell-mflux-4bit` and `madroid/flux.1-dev-mflux-4bit` repos were uploaded with an older MLX quantization format. mflux 0.17.5 (current) expects weight matrices stored as uint32 for dequantization — madroid's repos have them in a different dtype. The T5 text encoder load fails with the cryptic:

```
ValueError: [dequantize] The matrix should be given as a uint32
```

That came out of MLX's internals so the user had no idea what to do. This release replaces it with actionable advice.

### Changed

- **`_generate_flux1`** now catches the dequantize ValueError and surfaces a clear message naming the broken repo, explaining the upstream cause, and offering two workarounds: (1) download the full FLUX.1 schnell/dev (24 GB) and let mflux quantize on the fly, or (2) switch to FLUX.2 klein 4B — MLX 4-bit (known-working, same memory footprint).
- **Catalog use_cases** for both madroid entries now lead with an `❌ KNOWN BROKEN with mflux 0.17.x` warning so users see it BEFORE downloading 6 GB. Labels also gained the "(incompatible)" suffix.

### Notes

- This is an upstream issue with the community repos, NOT something the launcher can patch around without re-quantizing the weights ourselves. The advice in the error message is the best the launcher can offer today.
- If a new mflux-compatible 4-bit schnell/dev repo gets uploaded (e.g. to `mflux-community/*`), we can swap in the new repo name in the catalog and the error path stays as a safety net for the old one.
- The truth-audit script still reports ✓ NO DRIFT — the families are still wired in code; only the specific community-quant repos are broken. Full FLUX.1-schnell + FLUX.1-dev (the BFL canonical repos) still work via on-the-fly `quantize=4`.
- PATCH bump — UX clarity fix, no API change.

---

## [1.2.3] — 2026-05-24

### Fixed — Generate button no longer blocks queueing during a running job

The Generate button was disabled whenever any job was running or queued (the old `gen.busy` check was part of the `:disabled` condition). That meant: submit one image, wait several minutes for it to finish, THEN submit the next — completely defeating the queue panel we built earlier.

### Changed

- Introduced `canSubmit` getter as the single gate for the Generate button. It checks for the transient `gen.submitting` flag (true ONLY during the POST round-trip, ~300ms) rather than the persistent `gen.busy` flag (true while ANY job is in flight).
- Button text now flips between "Generate" / "Generate ×N" / "Queueing…" — never gets stuck on "Generating… 2/4" anymore. Progress for the running job is shown in the output frame and queue panel where it belongs.
- Added a hint below the button: when a job is running and the button is enabled, you see "💡 A job is running. Click Generate again to queue another — backend serializes them automatically."

### Why

Backend's `_GEN_LOCK` already serializes execution. The frontend had no reason to block queueing — that was leftover paranoia from the pre-queue-panel era. The queue panel makes pending jobs visible + cancellable, so multi-submit is now a first-class workflow.

### Notes

- Same fix shipped to MusicStudio v1.1.7 (had the identical bug). Voice already had the `canSubmit` getter pattern from the Phase B+ queue UX work.
- PATCH bump — UX fix, no breaking changes.

---

## [1.2.2] — 2026-05-24

### Changed — MLX-only filter is ON by default for fresh sessions

The app is Apple-Silicon-only, so non-MLX entries are usually suboptimal. The Models tab now opens with `🍎 Apple Silicon (MLX) only` pre-toggled, hiding the 9 non-MLX entries (FLUX.1 dev/schnell full-precision, FLUX.2 dev, FLUX.1 Kontext, Qwen-Image-Edit, klein-base variants). On your M4 + 16 GB this turns 23 cards → 14 cards on first load.

### Added — filter preferences persist across sessions

If you untoggle the MLX filter (or toggle the Fits-my-Mac filter), your choice is saved to localStorage and restored on next visit. No more fighting the default every session. Cleared by the browser's "clear site data" or by explicitly toggling back.

### Notes

- **Non-destructive change** — no models were removed from the catalog. You can still untoggle MLX-only to see everything.
- localStorage keys are app-namespaced (`imagestudio.modelFilters.mlxOnly` / `…fitsMyMac`) so the 3 apps don't collide.
- Voice + Music get the same mechanism. Music's MLX chip is auto-hidden (catalog has 0 MLX entries today), and the default-to-true logic correctly skips when there's nothing to filter to.
- PATCH bump — no runtime change, no new deps. Just `Update` from Pinokio.

---

## [1.2.1] — 2026-05-24

### Added — `audit_truth.py` script (the "no more walls" check)

After v1.2.0 caught the FLUX.1-schnell lie (green chip, runtime crash), we added a script that prevents that class of drift from ever happening again. Run before any release that touches `generation.py`:

```
python3 audit_truth.py            # human report
python3 audit_truth.py --strict   # exit non-zero on drift, for CI
```

The script AST-parses `catalog.py` + `generation.py` and reports 4 kinds of drift:

- **Commission lies** — family in `_WIRED_FAMILIES` but dispatch raises `NotImplementedError` (the v1.2.0 bug)
- **Omission lies** — dispatch handles the family but `_WIRED_FAMILIES` doesn't list it (UI underreports)
- **Orphan families** — in catalog but no dispatch branch (silent fall-through)
- **Phantom wires** — in `_WIRED_FAMILIES` but no catalog model uses it (dead config)

Result for v1.2.1: `✓ NO DRIFT — _WIRED_FAMILIES matches actual dispatch coverage.`

The script also caught a bug in its OWN first version (didn't handle `MLX_AUDIO_FAMILIES: dict[str, dict] = {...}` type-annotated assignments) — fixed before shipping.

### Notes

- Mirrors to VoiceStudio + MusicStudio per the "apply UX wins to all 3 apps" rule.
- PATCH bump — pure dev tooling, no runtime change.
- Documented in README "Truth audit (for contributors)" section.

---

## [1.2.0] — 2026-05-24

### Fixed — the "Phase 2 currently supports only FLUX.2 klein" bug

The Models tab was showing a green "✓ engine ready" chip on FLUX.1 schnell, FLUX.1 dev, and FLUX.2 dev — but clicking Generate threw `NotImplementedError: Phase 2 currently supports only FLUX.2 klein family`. **The diagnostic was lying.** This release fixes that by actually wiring the engines.

### Added — 3 newly-wired engine families

- **FLUX.1 schnell** — both `black-forest-labs/FLUX.1-schnell` (full, 24 GB) and `madroid/flux.1-schnell-mflux-4bit` (MLX, 6 GB) now generate via mflux's `Flux1` class with `ModelConfig.schnell()`. Distilled — 1–4 steps, guidance fixed at 0.0. Best for rapid iteration.
- **FLUX.1 dev** — both full + MLX 4-bit. Uses `Flux1` with `ModelConfig.dev()`. 20–30 steps, guidance 3.5. Best for higher-fidelity renders.
- **FLUX.1 Kontext** — instruction-edit pipeline. Uses `Flux1Kontext`. Surgical edits like "add sunglasses", "change sky to red" while preserving subject + composition. Edit-mode only (requires input image).

### Changed — `_WIRED_FAMILIES` truth audit

- **REMOVED `flux2-dev`** from the wired set. mflux doesn't ship a `Flux2Dev` class yet; the entry was misleading. FLUX.2 dev now correctly shows "🕓 worker in roadmap" until mflux adds it.
- **Refactored** `_run_txt2img` to use a proper `_dispatch_txt2img` router (mirrors `_dispatch_edit`). Per-family workers are now cleanly separated; adding the next mflux engine is one new branch + one new worker function.
- **Better roadmap error messages** — picking HiDream / Shuttle / FLUX.1 lite / Qwen-Image now returns "mflux doesn't ship an inference class for it yet" instead of generic NotImplementedError, so users know it's not their fault.

### Result on your M4 + 16 GB

**Before v1.2.0**: 1 of 23 catalog models actually generated (flux2-klein only).
**After v1.2.0**: **15 of 23** actually generate. The remaining 8 are correctly marked roadmap (waiting on mflux to add the inference classes — those releases would auto-light-up via the diagnostic system once installed).

### Notes

- MINOR bump (1.1.x → 1.2.x) — 3 new wired engines, no new Python deps (mflux already installed), no breaking changes.
- Just run `Update` from the Pinokio sidebar; no re-install needed.
- The `Phase 2 currently supports only` error message is gone — this was a stale phrase from when the project was first wired.

---

## [1.1.3] — 2026-05-24

### Fixed

- **Filter chips now announce themselves clearly when active.** v1.1.2's active state was too subtle (22% opacity tint, 1px border) — users couldn't tell which chips were toggled on, and assumed the filter wasn't working when it actually was. Now:
  - Active chips have a **2px bold border** and **45% opacity background** (up from 1px / 22%) — visible at a glance
  - Active chips show a **✓ prefix** before their label so the on-state reads unambiguously even when colors are hard to differentiate
  - Active chips show **white text** + **600 font weight** for clear contrast against the saturated background

### Added

- **Smart empty state** when filters yield 0 results. Instead of a generic "No models match" message, the empty state now:
  - Lists every active filter as a red ✕ chip — click any single chip to remove just that filter
  - Keeps the "✕ Clear all filters" button for the nuclear option
  - This turns "I'm stuck" into "Oh, my MLX-only filter is hiding the FLUX.2 dev I wanted"

### Why

User feedback: "I click the chip but it doesn't get sorted." Filtering math was correct (Showing 13 of 23 was accurate), but the visual feedback was too subtle to register as "I changed something." v1.1.3 makes filter state unmistakable.

### Notes

- PATCH bump — pure UX clarification, no logic changes, no breaking changes.
- Just run `Update` from the Pinokio sidebar; no re-install needed.

---

## [1.1.2] — 2026-05-24

### Added

- **Compact model cards** (collapse-by-default). Cards now show only label + chips (cache / gated / MLX / fit) + repo + size + hardware + capabilities by default. The `best_for` line, use-case bullets, and "Saved at" path are hidden behind a per-card `▾ Show details` toggle. With 23 models in the catalog, this turns the Models tab from a wall of text into a scannable gallery.
- **Bulk expand/collapse** toolbar buttons — `▾ Expand all` and `▴ Collapse all` operate on the currently-filtered list. Useful for quickly surveying all matches after applying a filter.
- **MLX-only filter chip** — `🍎 Apple Silicon (MLX) only` toggle to hide non-MLX entries with one click. The full-precision FLUX checkpoints (klein 4B full, klein 9B full, dev, schnell full) disappear from view, leaving just the pre-quantized MLX variants that load fast on M-series Macs.
- **Fits my Mac filter chip** — `🖥 Fits my Mac (16 GB)` toggle that hides models whose memory floor exceeds your detected RAM. Disabled when hardware detection unavailable. "Tight" models still show — only "risky" (above floor) get filtered, since "tight" might still be acceptable if you close other apps.

### Why

After v1.1.0 added structured use_cases to every catalog entry, model cards became dense walls of text. With 23 models that's overwhelming when you're just trying to pick one. v1.1.2 makes the gallery scannable again while keeping all the detail one click away.

### Notes

- PATCH bump — UX improvement, no breaking changes, no new Python deps, no schema changes.
- Just run `Update` from the Pinokio sidebar; no re-install needed.
- Expand/collapse state survives within a session but resets on page reload (intentional — fresh sessions get the clean compact view).

---

## [1.1.1] — 2026-05-24

### Added

- **Sidebar port display + external-browser escape hatch.** The Pinokio sidebar now shows a `Port 47868 · Open in Browser` item whenever the server is running. Two benefits:
  - **Visibility**: the port number is always readable in the sidebar — if the embedded webview ever caches a black screen, you can read the port and type `localhost:47868` into Chrome / Safari instead of being stranded.
  - **One-click escape**: clicking the item opens the WebUI in your system default browser via `web.open` with `target="_blank"`. Bypasses Pinokio's embedded webview entirely.

### Why

The embedded webview occasionally caches a broken state across restarts. Hard-refresh inside the webview doesn't always help, and without knowing the port the user has no way out. This makes the port permanently visible and provides a one-click escape.

### Files

- New: `open_external.js` (5-line wrapper around `web.open`)
- Modified: `pinokio.js` adds the port display + escape-hatch item to the `running.start` menu branch

### Notes

- PATCH bump — pure UX addition, no breaking changes, no new Python deps.
- Just run `Update` from the Pinokio sidebar; no re-install needed.

---

## [1.1.0] — 2026-05-24

### Added

- **Hardware fit detection** per model card. Detects your Mac's chip + unified memory via sysctl and shows a color-coded chip on each model:
  - 🟢 **fits** — your RAM ≥ 1.5× the model's floor (plenty of headroom)
  - 🟡 **tight** — meets the floor but close other apps before generating
  - 🔴 **may not fit** — below the floor, will swap or OOM
- **"Your Mac" banner** at the top of the Models tab showing detected chip + RAM, so the per-card fit chips have a clear anchor.
- **Structured use cases** per model. Each model card now shows ✅ "good at" / ⚠️ "weak at" / ❌ "avoid" bullet points so you can pick the right model BEFORE you hit Generate, not after a disappointing result.
  - Particularly honest about **MLX 4-bit quantization artifacts** on multi-subject scenes (extra heads / limbs / fused subjects). 4-bit klein/schnell variants now explicitly say "avoid multi-subject scenes" so users aren't surprised.
- **`/api/system`** endpoint exposing the chip + RAM snapshot. Used by the frontend + available for any external tooling.
- **`fit` field** in `/api/catalog` per model — `{state, label, hint, actual_gb, required_gb}`.

### Notes

- No new Python dependencies — `system_info.py` uses stdlib `subprocess` + macOS's built-in `sysctl`.
- Why the bump from 1.0.0 → 1.1.0: per our versioning scheme, a new feature without breaking changes or new Python deps. Just run `Update` from the Pinokio sidebar; no re-install needed.

---

## [1.0.0] — 2026-05-24

First versioned release. Covers all work through Phase D (mlx-community catalog expansion).

### Engines wired (4 families)

FLUX-on-MLX via `mflux`:

- **FLUX.2 klein** (4B / 9B / base 4B / base 9B) — Black Forest Labs' distilled FLUX.2, multiple MLX 4-bit / 8-bit / bf16 quants
- **FLUX.2 dev** — full FLUX.2 dev checkpoint, highest quality
- **FLUX.1 schnell** — original FLUX.1 schnell + MLX 4-bit variant (Apache-2.0, ungated)
- **FLUX.1 dev** — original FLUX.1 dev + MLX 4-bit variant (gated, non-commercial)

### Roadmap families (catalog-only, worker not yet wired)

- **FLUX.1 Kontext** — instruction-edit model (Black Forest Labs)
- **Qwen-Image Edit** — Alibaba's edit model
- **HiDream** — HiDream Labs' open image generation
- **Shuttle** — shuttleai's FLUX-derivative line (Apache-2.0)
- **FLUX.1 lite** — Freepik's distilled FLUX.1 (half params)
- **Qwen-Image (base)** — Qwen-Image txt2img, strong multilingual

Catalog presence lets you queue downloads now; generation routes to a clear "🕓 worker in roadmap" message until the worker ships.

### Architecture

- **Per-family workers** keyed off `model.family` — `_generate_flux2_klein`, etc.
- **3-state diagnostic system** — every engine reports `deps_ok` + `wired` + `ready`. UI shows which engines need install vs which are roadmap.
- **`/api/diagnostics`** endpoint surfaces package health + engine status to the frontend.
- **Aspect-ratio presets** — 8 ratios at ~1MP each (multiples of 16 for FLUX)
- **HF cache + flat-folder import** — both standard HF-cache and ad-hoc downloaded folders are supported

### Generate UX

- **Queue panel** — pending + running jobs visible with per-row cancel buttons
- **History pagination** — 12-per-page image gallery with per-row metadata (model, aspect, steps, guidance)
- **Library filters** — search + family chips + status chips + capability chips + sort
- **Diagnostic panel** — green/yellow/red per engine, with missing-dep details

### Frontend

- Alpine.js SPA (no build step), Alpine loaded locally
- Sticky topbar (z-index 20) + sticky library toolbar (`top: var(--topbar-height)`)
- Live SSE job stream + JS toast system
- NoCacheStaticMiddleware to prevent webview from holding old HTML

### Backend

- FastAPI + uvicorn, port 47868
- `_GEN_LOCK` serializes GPU-bound generations
- Job history persisted to `app/output/.history.json` (survives restarts)

---

## Format reference

```
## [X.Y.Z] — YYYY-MM-DD

### Added
- New engines / models / UI features

### Changed
- Behavior changes to existing features

### Fixed
- Bug fixes

### Removed
- Dropped engines / deprecated UI

### Notes
- Migration steps, breaking-change details, etc.
```
