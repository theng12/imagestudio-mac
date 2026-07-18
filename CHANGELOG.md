# Changelog — Image Studio KH

All notable changes to Image Studio KH are documented here.

Versioning follows [Semantic Versioning](https://semver.org/) with this project-specific interpretation:

- **MAJOR** (1.x.x → 2.x.x) — breaking change. Re-install required.
- **MINOR** (1.1.x → 1.2.x) — new engine / new feature / new model family. **Re-run "Install Generation"** to pick up new Python deps.
- **PATCH** (1.2.0 → 1.2.1) — bugfix / UI tweak / catalog entry within an existing family. **Just run Update** from the Pinokio sidebar.

---

## [1.21.1] — 2026-07-18

### Fixed — automatic-update settings stay put while editing

- Separated the editable update form from the five-second live status poll.
  Choosing Automatic, changing Daily/Weekly, or selecting a maintenance time
  no longer snaps back to the previously saved value before it can be saved.
- Reworked the update panel into clear mode cards, styled schedule controls,
  one primary save action, and contextual update actions. Unsaved changes are
  now explicit, and unavailable update actions no longer clutter the panel.

### Verification

- Reproduced the original poll overwrite in-browser, then verified mode and
  maintenance-time drafts survive multiple status polls and remain saveable.
- The full Python test suite and JavaScript syntax check pass. The scheduler,
  update engine, launcher, dependency manifests, and active service were left
  unchanged because the failure was isolated to frontend draft state.

---

## [1.21.0] — 2026-07-15

### Added — safe optional automatic updates

- Added Off, Notify only, and Automatic modes in Settings, with daily or weekly
  maintenance schedules, visible status, manual checks, retry, and an
  “Update after current work” option.
- Updates now defer while image generations, model downloads, or generation
  engine installation are active. The updater verifies the fixed GitHub remote,
  clean `main` branch, fast-forward history, disk space, dependencies, imports,
  health, and the exact running version.
- Added a short-lived launchd scheduler, lock protection, retry/backoff,
  rotating redacted logs, desktop notifications, restart recovery, and bounded
  rollback when post-update verification fails. The feature is Off by default.

### Verification

- Added focused updater tests and verified schedule installation/removal,
  readiness reporting, API behavior, launchers, dependencies, and responsive UI.

## [1.20.2] — 2026-07-15

### Fixed — bounded generation inputs and accurate edit controls

- Added backend validation for prompt length, dimensions, pixel count, steps,
  guidance, seeds, quantization, LoRA count/scales, and uploaded image size and
  decodability. This closes the unbounded-input path that could turn a malformed
  or remote request into excessive memory use or an opaque engine failure.
- Rejected the unsupported 1-step mflux request before it reaches the scheduler,
  avoiding the observed `ZeroDivisionError` and returning an actionable 422.
- Fixed FIBO Edit to stop passing `image_strength` to an mflux signature that
  does not accept it. Qwen Edit and FIBO Edit now hide that ignored control.

### Verification

- Verified all 27 Hugging Face-backed catalog repositories currently resolve;
  cloud entries are synthetic provider IDs by design.
- Ran a real seeded FLUX.2 klein 4-bit 512×512 generation on the cached model;
  output was a valid nonblank RGB PNG at the managed output path.
- Added regression tests for input limits and model-aware edit controls. The
  existing launcher, service mode, catalog families, and dispatch audit remain
  unchanged.

---

## [1.20.1] — 2026-07-13

### Fixed — saved fleet credentials apply without restarting Image Studio

- Protected requests now verify against the current owner-only fleet-token file instead of a startup snapshot. Studio Hub credential saves and rotations take effect immediately, and successful browser sessions refresh their authentication cookie.

Verified with a live-rotation middleware regression test plus the full test suite. No launcher, engine, or dependency changes; **Just run Update**.

## [1.20.0] — 2026-07-12

### Added — secure fleet access and capability contract

- Remote API and output access now requires the automatically shared StudioHub fleet token; loopback Pinokio use remains passwordless.
- Browser writes are same-origin protected, authenticated browser sessions use an HttpOnly cookie, and remote Studio pages prompt once per tab when a token is needed.
- Added the normalized `GET /api/capabilities` contract for Hub preflight and rolling-update orchestration.

### Verification

- Python and JavaScript syntax checks pass. Middleware tests cover local access, remote rejection, accepted fleet credentials, cross-origin write rejection, and private token permissions.

## [1.19.1] — 2026-07-12

### Security — protected credentials, safe update banner, patched web dependencies

- Settings files containing Hugging Face and cloud-provider credentials are now
  forced to owner-only (`0600`) permissions when read and after every atomic save.
- The update banner now renders remote version metadata with `textContent`; a crafted
  remote `VERSION` value can no longer inject HTML into the Studio page.
- Raised FastAPI to `>=0.139` and `python-multipart` to `>=0.0.32`, bringing fresh
  installs onto patched Starlette and multipart releases identified by `pip-audit`.

### Verification

- JavaScript and Python syntax checks pass; settings permission behavior was tested
  against a temporary file, and the new dependency lock was audited in an isolated
  environment. The generation truth audit still reports no catalog/dispatch drift.
- The existing `0.0.0.0` LAN/service bind and permissive CORS were reviewed and left
  unchanged because they are part of the documented server-mode contract. LAN API
  authentication is tracked as a fleet feature rather than silently breaking remote use.

## [1.19.0] — 2026-07-10

### Added — Image-generator overhaul: live feedback, per-image actions, disk management

Carries the Voice Studio generator improvements to Image Studio, adapted for images (frontend live on reload; new endpoints activate after one **Update** — no new Python deps):

- **Live feedback** — fixed the "Generating… undefined/undefined" progress label (now real % + elapsed); the queue panel is sticky with a live progress bar on the running job.
- **Per-image actions** — each result tile now has hover **📂 Reveal** and two-click **🗑 Delete** (removes the image and its PNG) alongside Reuse. *(Backend: `DELETE /api/generate/history/{id}`.)*
- **Disk management** — footer showing image count + disk used, with one-click prune ("keep newest 50" / "delete > 30 days"). High-value: outputs accumulate fast. *(Backend: `GET /api/output/stats`, `POST /api/output/prune`.)*
- **Friendlier empty state**.

### Fixed — Two native `confirm()` dialogs replaced with a webview-safe modal
Remove-token and Import-move used `window.confirm()`, which Pinokio's embedded webview silently blocks. Both now use an in-app confirm modal.

### Notes
- MINOR bump (1.18.8 → 1.19.0). Frontend live on reload; endpoints need one **Update** (restart) — UI degrades gracefully until then. No auto-play (images don't play).

---
## [1.18.8] — 2026-07-10

### Added — "Open outputs folder" button (+ Clear-history fix)

- **Open outputs folder** — new button in the history header that reveals the folder holding every generated images file in Finder, via the existing `/api/reveal`.
- **Clear history** used the native `window.confirm()` dialog, which Pinokio's embedded webview can silently block — so it did nothing. Replaced with a webview-safe two-click confirm (arm, then click again).

### Notes
- PATCH bump (1.18.7 → 1.18.8) — frontend only. Live on reload; no restart needed.

---
## [1.18.7] — 2026-07-10

### Added — FLUX.1 Krea dev + Kontext dev as MLX 4-bit (16 GB-runnable)

Two new catalog entries in **existing wired families** (`flux1-krea` → `_generate_flux1` with `ModelConfig.krea_dev()`; `flux1-kontext` → `_generate_kontext`, both `model_path=repo`). No engine code, no new deps, no new env — pure catalog additions that bring models previously **24 GB-only** down to **16 GB Macs**:

- **`filipstrand/FLUX.1-Krea-dev-mflux-4bit`** — photorealism finetune, by the **mflux author**. `flux1-krea`, `mlx-4bit`, ungated, `min 16 GB`.
- **`akx/FLUX.1-Kontext-dev-mflux-4bit`** — instruction image-editing (Image Edit tab). `flux1-kontext`, `mlx-4bit`, ungated, `min 16 GB`.

**Why these two specifically — and how they were vetted.** The catalog notes at the FLUX.1 schnell/dev entries record that the old `madroid/*-mflux-4bit` repos were **removed in v1.2.5** because their pre-0.17 MLX quant format fails on the **T5 text-encoder load** (`dequantize … uint32`). So I verified the actual quant format, not just the file layout: I range-fetched the safetensors headers and confirmed both new repos store the **T5 (`text_encoder_2`) in the current U32 quant format** (mflux 0.10.0 / 0.9.6) — matching the working FLUX.2-klein 4-bit reference (0.15.5). `filipstrand` is the mflux author's own repo — exactly the "maintained 4-bit repo" the removed-madroid notes said to add here.

### Verification honesty
- **Statically verified:** U32-quantized T5 (the exact failure point of the removed repos), mflux-author / maintained provenance, ungated, and that both families are already `wired` with workers that load `model_path=repo`.
- **Not completed:** a live download+generate — HF throttled the 9.6 GB weight shards to a stall even authenticated. If a load ever fails on some Mac, the app's existing handler surfaces a clear, actionable message (and suggests the full checkpoint / a klein 4-bit) — a bad entry can't break anything else.

### Deliberately NOT added (documented so the audit trail is clear)
- **`dhairyashil/FLUX.1-schnell` / `-dev` 4-bit** — mflux **0.6.2**, the same old vintage as the removed `madroid` repos → high T5-load risk; left out.
- **DiffusionKit SD 3.5 large 4-bit** (`argmaxinc/…`) — DiffusionKit pins `mlx==0.17.3`, which would **downgrade and break mflux** (needs 0.31.2). Can't share the env; would require an isolated venv + subprocess engine (deferred).
- **`avlp12/CyberRealistic-Z-Image-Turbo` 4-bit** — a realism/NSFW-leaning finetune; not appropriate for a general fleet catalog.

### Note
- PATCH — catalog entries in existing families, **no new deps**. Just **Update**; download the model from the Models tab to use it.

---

## [1.18.6] — 2026-07-10

### Fixed — download ETA settle-guard, honest catalog sizes, and pruned dominated models

**Absurd download ETA (`downloads.py`).** Same fix shipped across the KH studio suite: the speed EMA's first near-zero sample (taken before real bytes land) produced ETAs like "99679m 03s" seconds after clicking Download. `eta_seconds` is now suppressed until the job has ≥3 s of runtime.

**Unreadable long durations (`app.js`).** `formatDuration()` gained hour/day rollup so long ETAs read as `Xh YYm` / `Xd YYh` instead of `734m 12s`.

**Catalog sizes now reflect the true download size.** These repos download unfiltered (whole repo), so the old `size_gb` values were 2–3× too low. Corrected 21 entries to the real Hugging Face repo sizes — FLUX.2-dev 64→178 GB, FLUX.1-dev/schnell/Krea/Kontext 24→58 GB each, Qwen-Image / Qwen-Image-Edit 20→58, SD3.5-large 20→72, AuraFlow 13→66, SeedVR2 18→60, plus the AITRADER FLUX.2-klein MLX quants (4-bit 2.3→4.6, 8-bit 4.5→8.6, and the 9B variants). Verified against the HF API `blobs=true` listing.

**Removed 4 dominated / oversized entries.** `black-forest-labs/FLUX.2-klein-4B` and `-9B` (raw repos already dominated by their AITRADER MLX quants in the same family — the quants win on Apple Silicon); `Tongyi-MAI/Z-Image-Turbo` (raw, dominated by the andrevp Z-Image-Turbo MLX quants); `briaai/Fibo-Edit-RMBG` (~90 GB for the same edit capability as the 40 GB Fibo-Edit).

**Checked, left unchanged:** memory floors — for diffusion, peak runtime memory is driven by activations/offloading, not download size, so they can't be re-derived from HF metadata and were left as-is. Download *filtering* (to shrink these large downloads) was deferred: it needs per-model load-testing, and a wrong filter would let a model download but fail to load. `py_compile` clean; catalog re-imports to 37 models.

## [1.18.5] — 2026-07-10

### Changed — Cloud credentials now use a compact provider picker

The cloud-key settings were one long vertical form, which made finding a provider
needlessly slow. Settings now presents five compact provider tiles with saved-state
indicators and keeps one provider editor in focus at a time. The app header also gives
the Studio icon and active tab a clearer, more modern treatment.

### Verification

- Checked the Alpine bindings and HTML structure, ran JavaScript syntax validation,
  and verified the responsive two-column provider picker at the mobile breakpoint.
- The underlying credential fields, save/clear actions, local storage behavior, and
  provider API calls are unchanged.

---

## [1.18.4] — 2026-07-10

### Changed — Version now shown as a badge in the top-right header (consistent across all sibling apps)

The app version was displayed inconsistently across the Studio fleet (bottom footer on
some, top-right on Chat, missing on Video). It's now a small `v1.18.4`-style badge in the
top-right of the header on every app, matching Chat Studio — visible at a glance without
scrolling to a footer.

### Notes

- PATCH bump (1.18.3 → 1.18.4) — frontend only (`index.html` + `style.css`). Served with
  no-cache headers, so it appears on the next browser reload without a restart.

---
## [1.18.3] — 2026-07-10

### Fixed — Update reinstalls the service (rewrites the launchd plist) instead of kickstarting a stale one

The service scripts were renamed from generic `serve.sh` / `watchdog.sh` to
`<app>-serve.sh` / `<app>-watchdog.sh`, and the launchd plist's `ProgramArguments`
now points at the renamed script. A machine with the service already installed has
a plist pointing at the OLD `serve.sh` — so a plain **kickstart** (`restart_service.sh`)
would relaunch a plist pointing at a now-deleted path and the service would fail to
come back up after an update.

`update.js` (and `install_generation.js`) now restart the service with
**`install_service.sh`** instead of `restart_service.sh`. `install_service.sh`
regenerates the plist to match the current on-disk scripts *before* relaunching
(bootout → bootstrap → kickstart), so the rename is folded in automatically. It's
idempotent and safe to run on every update.

### Notes

- PATCH bump (1.18.2 → 1.18.3) — launcher scripts only. Applies only where the app
  runs as a launchd service (`service/.installed`); the `start.js` path is unchanged.

---
## [1.18.2] — 2026-07-10

### Added — In-app auto-check banner: tells you when to update instead of failing silently

On load the web UI checks `GET /api/update-status` and shows a dismissible banner when this install needs attention:

- **A newer version is published** — compares this install's VERSION against the repo's published VERSION (fetched from GitHub raw, cached ~6h, in a background thread so it never blocks). Banner: "⬆ Update available (vX → vY)", pointing at the one-click **Update** button in the Pinokio sidebar.
- **The generation engine isn't installed** — detects the missing stack directly. Banner: "⚠ Generation engine not installed — the Generate tab won't work", pointing at **Install Generation** (or **Update**) in the sidebar. This is the exact silent failure that let a broken generation install look fine before.

Detect-in-app, apply-via-sidebar: a sandboxed web page (external browser, Tailscale) can't reliably drive Pinokio's script runner, so the banner points at the sidebar's one-click Update rather than trying to self-update. The banner is self-contained (no framework coupling) and degrades silently if the endpoint isn't live yet (e.g. a running service that hasn't restarted onto the new build).

### Notes

- PATCH bump (1.18.1 → 1.18.2) — backend adds `GET /api/update-status`; frontend adds the banner to `index.html`. No change to existing features.

---
## [1.18.1] — 2026-07-10

### Fixed — One-click Update that actually works, and generation installs that don't silently fail

Overhauled the update/install flow. It was tedious and, worse, quietly broken:

- **One Update button, correct in every run mode.** The old "Update & Restart" was hardwired to stop/start `start.js`, but in production this app runs as an always-on launchd **service** — so it stopped nothing and then launched a *second* server that fought the service for the fixed port. The unified `update.js` now detects the mode and restarts the **real** server (kickstart the service **or** start `start.js` — never both), so updating no longer requires manually stopping production first.
- **Generation deps refresh on the same click.** `update.js` used to install only the base deps; heavy ML deps came from a separate "Reinstall Generation" button, so a release that bumped a model dependency silently didn't apply on Update. Update now refreshes generation deps too (when generation is installed) — no second button to hunt for.
- **Install from source, not a drifted lock.** `install_generation.js` (and Update) now install from `requirements-generation.txt`, the authoritative range file. The generation `.lock.txt` had drifted — on some machines it contained only base packages, so "Install Generation" installed nothing while the UI still reported success. Source-first can't have that failure mode.
- **Verify-then-notify.** After installing, the key modules are imported; a failure breaks the run and withholds the "installed" notification. The old script fired "Generation engine installed" unconditionally — even on total failure.
- **"Update & Restart" folded into "Update"** (kept as a back-compat alias that forwards to `update.js`).

### Notes

- PATCH bump (1.18.0 → 1.18.1) — launcher scripts only (`update.js`, `install_generation.js`, `update_and_restart.js`, `pinokio.js`). No app-code change.
- Verified: all launcher scripts load; the menu renders a single mode-aware "Update"; generation deps import in the env.

---
## [1.18.0] — 2026-07-09

### Added — dependency lockfiles: fresh installs are now reproducible forever

`requirements.txt` / `requirements-generation.txt` use version **floors** (`>=`), so a fresh install months from now would resolve to whatever PyPI serves that day — one breaking release in any dependency (mflux, mlx, huggingface_hub, …) bricks the app on a new machine while existing installs keep working. Same fix Chat Studio shipped in its v1.19.0 and Voice Studio in v1.8.0.

- **`app/requirements.lock.txt`** — the pinned phase-1 set (36 packages, compiled from the floors constrained to the verified env's installed versions).
- **`app/requirements-generation.lock.txt`** — the FULL verified env (88 packages incl. the mflux/MLX generation stack).
- `install.js`, `install_generation.js`, and `update.js` now install from the locks. Upgrade flow (edit floors → verify → regenerate both locks → commit) is documented in each lock's header.

Verified: both locks resolve all-satisfied against the live env (36 pkgs / 13 ms and 88 pkgs / 20 ms); all three launcher scripts pass `node --check`; python was already pinned (`python=3.12`).

### Notes

- MINOR bump (1.17.4 → 1.18.0) — install-pipeline change, no package versions changed (locks pin exactly what's installed and verified).

## [1.17.4] — 2026-07-08

### Fixed — Start now refuses to compete with startup service mode

The startup service already takes over port `47868` when installed, and the service-mode sidebar hides the normal Start button. But `start.js` itself still had no direct guard, so any stale menu, direct script launch, or automation path could still try to start a second Uvicorn server on the same fixed port and fail with "address already in use."

`start.js` now checks for `service/.installed` before launching the server. If service mode is active, it exits immediately with a clear message telling the user to use **Open UI (service)** or uninstall the startup service first. The existing Uvicorn URL capture and `local.set` behavior are unchanged.

**Verified:** `node --check start.js`, direct inspection against the required Pinokio URL-capture pattern (`input.event[1]`), and current logs showing service install already takes over the same port by stopping the previous Pinokio Start process.

### Notes

- PATCH bump (1.17.3 → 1.17.4) — launcher guard only, no app/backend change. **Just run Update**.

## [1.17.3] — 2026-06-29

### Fixed — download sizes shown in binary GB, disagreeing with Hugging Face + the backend (consistency audit)

Byte-formatting sweep (the same audit run on Voice Studio in v1.7.2/1.7.3).

**Root cause:** the frontend's `humanBytes()` divided by **1024** but labeled the result `"GB"/"MB"` — binary math with decimal labels. Meanwhile Hugging Face reports sizes in **decimal** (÷1e9) and the backend's own download logger uses decimal too (`downloads.py`: `total_bytes / 1e9`). So the same download was `4.62 GB` per HF/the backend but rendered as `4.30 GB` in the frontend progress line — a split-brain on the same bytes.

**Fix (minimal):**
- `humanBytes()` — `÷1024 → ÷1000`, so the download progress line (done / total / speed) now reports decimal GB/MB matching HF and the backend. Verified: `humanBytes(4619726847)` → **`4.62 GB`** (was `4.30 GB`); `8569680065` → `8.57 GB` (matches the backend's `÷1e9`).
- `formatGb()` — the sub-1GB branch used `×1024`; changed to `×1000` so a hypothetical <1GB `size_gb` renders decimally (e.g. `0.5 → 500 MB`, not `512 MB`), consistent with `humanBytes`. The `≥1GB` path was already correct (`size_gb` is a decimal-GB value shown as-is).

`humanBytes` is used only in the download-progress line; no other call sites.

### Checked and deliberately left unchanged
- **State colors** — the app has canonical `--ok`/`--warn`/`--bad`. Some chips use hardcoded hexes, but verified against the vars: the greens (`#6ee7b7` vs `--ok #6ee7a8`) and reds (`#f87171` vs `--bad #ef6a6a`) differ by ≤15/255 per channel — imperceptible, a no-op to "fix." The amber (`#fbbf24`) differs more from `--warn #f3b562`, but it's used in distinct components (RAM-fit tier / dep chips) with no proven same-context clash against a `--warn` element, so consolidating would risk altering intentional design with no visible-bug payoff. Left as-is (same call the Voice Studio audit made on the phantom `.btn` class).
- **"Cached" casing** — the Status *filter* shows `✓ Cached` (Title-Case, like its sibling filters "Partial" / "Not downloaded" / "Ready to generate"); the model-card badge shows `✓ cached` (lowercase, matching the raw `cache.state === 'cached'` value + the legend). Each is locally consistent with its own context's convention; not terminology drift.
- **Interaction parity** — downloads have a single entry point (`confirmDownload()` → size/token dialog → `startDownload()`), and `cancelDownload()` is shared identically by the model card and the Downloads tab. There is no per-model "delete" action to be inconsistent. No parity mismatch found.
- **RAM display** — left in GB (it's installed unified-memory capacity from the backend, not a network/file-transfer byte count) — binary/decimal doesn't apply.

### Note
- PATCH — frontend only, no new deps. Just **Update** (hard-refresh the page).

---

## [1.17.2] — 2026-06-29

### Fixed — generated-image preview collapsed to a tiny strip

The Generate-tab output column is a sticky flex column with the result panel + history below the image. After the 1.16 history rework added more content below it, the preview frame (default `flex-shrink: 1`) got squashed to fit — the image rendered as a ~40px-tall sliver.

- `.output-frame` now has `flex-shrink: 0` so it keeps its full aspect-ratio height and fills the column width (with a `max-height: 72vh` bound so tall portraits don't overflow the viewport — the column scrolls past them).
- `outputFrameStyle` now uses the **displayed job's** dimensions (not the form's), so the frame matches the aspect ratio of the image actually on screen.

Verified live: a 1344×768 result now renders at 540×308 (full column width) instead of ~40px tall.

### Note
- PATCH — frontend only, no new deps. Just **Update** (hard-refresh the page).

---

## [1.17.1] — 2026-06-29

### Fixed — "Install/Reinstall Generation" was unreachable once the startup service was installed

The diffusers-engine models (SD3.5, Sana, PixArt-Sigma, Lumina2, AuraFlow) need the `diffusers` + `accelerate` packages, installed via **Install Generation** in the Pinokio sidebar. But that menu item only existed in the normal (non-service) menus — once the **always-on startup service** was installed, the menu switched to "service mode" which omitted it, so there was no way to install those deps (the in-app dep-check just said "Missing: diffusers" with no button to fix it).

- **`pinokio.js`** — the service-mode menu now includes **Install/Reinstall Generation**.
- **`install_generation.js`** is now **service-aware**: in normal mode it stops→installs→starts `start.js` (as before); in service mode it does NOT relaunch `start.js` (that would fight the launchd service for the fixed port) — it installs, then restarts the service (`restart_service.sh`) so the running server reloads Python and picks up the new packages.

Note: this only affects the optional diffusers-engine models. All mflux/MLX models (FLUX.2 klein, FLUX.1 schnell/dev/krea, Qwen-Edit, …) and the cloud models were unaffected and continued to work.

### Note
- PATCH — launcher scripts only, no app/deps change. Just **Update**.

---

## [1.17.0] — 2026-06-29

### Added — per-model `sizes` menu in `GET /api/catalog` (for Story Studio)

Each catalog model now carries a ready-to-use **`sizes`** list so clients drive aspect-ratio + resolution pickers with **zero pixel math** — every entry is an exact accepted `{width, height}`:

```json
"default_aspect_ratio": "16:9",
"custom": { "min_px": 512, "max_px": 2048, "step": 8, "max_pixels": 4194304 },
"sizes": [
  { "aspect_ratio": "16:9", "label": "1080p", "width": 1920, "height": 1080, "tier": "balanced", "default": true },
  { "aspect_ratio": "1:1",  "label": "1024",  "width": 1024, "height": 1024, "tier": "balanced" }
]
```

- **Local models** → a curated `/16`-aligned ladder capped at the local ~1.3 MP budget (8 aspect ratios × up to 3 tiers).
- **Cloud models** → familiar standard resolutions (720p / 1080p / 1440p …), `/8`-aligned, capped at each provider's real max side — **cloud is NOT downscaled to the local cap** (e.g. Cloudflare/Nebius reach 1080p; Together/HF cap at 720p/1536; Pollinations to 1080p).
- **Fixed-output models** (Cloudflare FLUX schnell — measured `1024×1024`; Gemini) → a single size with **`fixed: true`**.
- Every model marks exactly one entry **`default: true`** (the `balanced` tier of `default_aspect_ratio`, or the largest available of that AR). `tier` is `fast | balanced | high | ultra` (smallest→largest) so clients can map **Fast / Balanced / Highest** presets directly.
- `custom: { min_px, max_px, step, max_pixels }` gives the free-sizing range for arbitrary-dimension models (null for fixed).

Backward-compatible: older clients that don't read `sizes` are unaffected; `is_cloud`, `cloud_provider`, `cloud_credentials_ok`, `fit.state`, `cache.state`, `capabilities`, `supports_custom_dimensions`, and `requires_billing` are all unchanged.

### Note
- MINOR — additive catalog fields, **no new deps**. Just **Update**. Implemented in `app/backend/sizes.py`.

---

## [1.16.0] — 2026-06-29

### Changed — reworked the image history / result view

The Generate-tab result + history area was hard to navigate and showed almost nothing. Overhauled:

**Fixed the core navigation bug.** The history grid used to drop the newest result (it assumed the newest was always the one on screen), so once you clicked an older thumbnail there was **no way back to the latest**. The grid now shows **every** finished result (newest included), badges the newest, highlights whichever one is open, and a **"👁 You're viewing an earlier result · ← Back to latest"** bar (plus a "← Latest" link in the history header) jumps you straight back.

**The prompt is now front-and-centre.** The selected result shows its full **prompt** in a dedicated, scrollable block with a **Copy** button (and the negative prompt when present) — instead of being buried in a collapsed JSON blob. A **Copy prompt** action was added to the button row too.

**Much richer detail.** The result header now shows the **model**, a **provider** pill for cloud models, and a relative **timestamp** ("32m ago"); a row of detail chips shows **Size · Seed · Steps · Guidance · Time**. Errors render inline in red.

**Better history thumbnails.** Bigger tiles, each with a gradient overlay showing the **prompt snippet + model + duration**, a **NEWEST** badge, per-tile state badges (e.g. ERROR), an active-highlight, and a hover "reuse" button. Click a tile to open it in the main view.

### Note
- PATCH-level UI rework, **frontend only, no new deps** — just **Update** (static files reload on refresh). Verified live in a browser (desktop): navigation, prompt display, detail chips, and the badged grid all render with no console errors.

---

## [1.15.0] — 2026-06-29

### Added — per-model dimension capability (exposed to Story Studio) + more aspect ratios

- **`supports_custom_dimensions`** (boolean) is now in each `/api/catalog` model. `false` for fixed-output endpoints that ignore width/height — **Cloudflare FLUX schnell** and **Gemini** — and `true` for everything else. The Generate UI hides the aspect-ratio picker and shows a "fixed output size" note for those models, and Story Studio can use it to decide whether to offer ratio options per model.
- **4 more aspect ratios**: `5:4`, `4:5`, `2:1`, `1:2` (now 12 presets total), all ~1 MP and /16-aligned.

### Changed — Gemini marked as "needs billing" (it is no longer free)

Google's free tier now allows **0** `gemini-2.5-flash-image` requests (`429: free_tier_requests, limit: 0`) — image generation requires a **billing-enabled** account. So Gemini was relabelled accordingly and is no longer presented as free:

- New **`requires_billing`** catalog field (true for Gemini); its `fit.state` is now **`needs_billing`** with a hint, so the UI/Story Studio gate it like a credential-missing model (shown but not selectable, with a "💳 needs billing" chip + a Generate-tab banner linking to enable billing).
- The Gemini provider now turns the raw `429` into a clear message: *"Gemini image generation needs billing enabled … the free tier allows 0 image requests."*
- Catalog label, `best_for`, family explainer, and README all updated to say **needs billing (not free)**.

### Clarified — Cloudflare FLUX schnell has a fixed size

It was always sending width/height that the endpoint ignores (hence "no ratio control"). It's now flagged `supports_custom_dimensions: false`, and its `best_for` points users to **SDXL / SDXL-Lightning / Leonardo Lucid/Phoenix** for custom ratios on Cloudflare.

### Note
- The credential-readiness signal (`cloud_credentials_ok` / `fit.state: "needs_key"`) from v1.12.0 is already live and correct — verified on the running service.
- MINOR — new catalog fields + UI, **no new deps**. Just **Update**.

---

## [1.14.1] — 2026-06-29

### Changed — Models tab split into Local / Cloud sub-tabs

The Models tab now has a **Local | Cloud** toggle at the top, each with a live count (e.g. *Local 25 · Cloud 12*). This declutters the page by showing only what's relevant to each kind of model:

- **Local** — the download-and-run-on-this-Mac models, with the full hardware machinery: RAM planner, "✨ Best for your RAM" picks, the beginner primer, and the Status / RAM-fit / MLX filters.
- **Cloud** — the hosted-API models, with a trimmed toolbar (Search + Sort + provider Family + Capability). The RAM planner, best-picks, primer, and download/MLX/RAM-fit filters are hidden — none of them apply to cloud models — and the intro points to *Settings → Cloud provider keys*.

The chosen tab is **remembered across sessions**. Switching tabs resets the scope-specific filters so you never land on an accidentally-empty list. Family chips, the "Showing N of M" count, and capability chips are all scoped to the active tab.

### Fixed
- Model cards now render the **filtered** list (`filteredModelsByFamily`) instead of the unfiltered family list, so the card grid always matches the family-header count and the active filters (previously a family could show a "(2)" header but render all its cards).

### Notes
- PATCH — frontend only, **no new deps**. Just run **Update**.

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
