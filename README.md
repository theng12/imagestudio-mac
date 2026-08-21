# ImageStudio (Mac)

A custom Pinokio app for FLUX image generation on Apple Silicon. Mac-only
(`darwin` + `arm64`), built around [mflux](https://github.com/filipstrand/mflux)
and MLX.

> **Current status:** model catalog, download manager, weight-import flows, and
> local generation (txt2img / img2img / image edit) are live. Generation
> dependencies remain optional so model browsing and downloads stay lightweight.

## What it does today

- Browse 19 local models across FLUX.2 Klein, FLUX.1 Schnell/Krea/Kontext,
  Qwen-Image, FIBO, Sana, PixArt Sigma, Lumina 2, AuraFlow, SDXL, and a
  **SeedVR2** image upscaler in the Image-to-Image tab.
- **Two local engines.** Most models run on **mflux/MLX** (Apple-native, fast).
  A second **diffusers** engine (PyTorch/MPS) runs models mflux has no class for
  — Sana, PixArt Sigma, Lumina 2, AuraFlow, and the SDXL family. Each model
  declares its `engine`; Diffusers models behave like any other local model in
  the UI but need the `torch`/`diffusers` dependencies from **Install
  Generation**.
- See at a glance which models are cached locally vs. need downloading.
- Confirm-before-download dialog with on-disk size and unified-memory
  recommendations so you don't accidentally fetch 60 GB.
- Resumable downloads — interrupt and re-trigger; partial files continue
  from the last byte offset.
- Generation requests are bounded at the API boundary: prompts up to 10,000
  characters, outputs up to 2,048px per side / 4 MP, inputs up to 20 MiB / 16 MP,
  and 2–100 steps. Invalid images and numeric values are rejected before they
  reach the inference engine.
- Import weights you already have elsewhere into HF cache via symlink
  (no copy, no duplication).
- HTTP API on `127.0.0.1:<port>` — call it from your main Mac over the LAN
  when you set `PINOKIO_SHARE_LOCAL=true` in `ENVIRONMENT`.

## Sidebar

- **Start** — launches the FastAPI server (`uvicorn`) and opens the UI.
- **Open UI / Models / Downloads** — deep-link tabs once the server is running.
- **HF Cache** — Pinokio file browser at `cache/HF_HOME/hub`.
- **Outputs** — generated images (Phase 2).
- **Install/Reinstall Generation** — remains available while the regular server
  is running and in startup-service mode. The installer safely refreshes the
  appropriate server when it finishes.
- **What's New** — always opens the installed release
  changelog, including while another launcher action is in progress.
- The WebUI version area includes **What's New** and opens the same installed
  release history in a modal without leaving Image Studio.
- **Update / Reinstall / Reset** — standard launcher lifecycle.

## Machine-local environment

`ENVIRONMENT.example` is the tracked defaults template. Install, first start,
and startup-service setup copy it to the ignored, machine-local `ENVIRONMENT`
file only when that file is absent.
Existing cache paths, sharing choices, and imported-model paths are preserved
across installs, updates, and rollback. Startup-service setup normalizes only
its three ownership keys. A rollback to a legacy release that tracked this file
may leave the checkout dirty again, but retains the machine file unchanged for
a later migration retry. To adopt a new default later, copy it deliberately
rather than deleting your local settings.

## Importing your existing FLUX.1 schnell / dev

You mentioned you have these downloaded elsewhere. Two ways to wire them in:

### A. One-shot via the Import tab

1. Start the server.
2. Open the UI → **Import** tab.
3. Paste the absolute path to a folder shaped like
   `models--black-forest-labs--FLUX.1-schnell`.
4. Click **Link**. Done — no copy, no duplication.

### B. Auto-scan multiple folders

Edit the `ENVIRONMENT` file and set
`IMAGESTUDIO_EXTRA_MODEL_DIRS=/path/one:/path/two` (colon-separated).
Each path should be either a folder full of `models--*--*` subfolders,
or a parent containing a `hub/` directory with that layout. Restart the
server. The **Import** tab → **Scan candidates** section will list every
HF-cache-style folder it finds, with a one-click **Link** button per row.

## Optional automatic updates

Settings now includes a safe automatic updater. It defaults to **Off** and can
instead notify you or install verified updates on a daily or weekly schedule.
Image Studio always waits for image generations, model downloads, and generation
engine installation to finish. “Update after current work” keeps retrying until
the app is idle. Every attempt verifies the expected GitHub repository, clean
fast-forward history, free disk space, dependencies, imports, health, and the
running version; a failed post-update verification triggers a bounded rollback.
If the local readiness endpoint cannot be reached, installation fails closed
unless launchd and the app port positively confirm that Image Studio is stopped.
Qualified generation environments are restored from the complete pinned
generation lock rather than resolving new ML package versions during an update.

Updater status is available through `GET /api/auto-update/status` and readiness
through `GET /api/auto-update/readiness`. Settings, manual checks, updates, and
retry use the corresponding POST endpoints under `/api/auto-update/`. Logs are
stored under `logs/auto_update/`; turning the feature Off unloads its schedule.

## Local output retention

Generated images are temporary local backups. Automatic cleanup is enabled by
default, keeps completed images for three days, and enforces an 80 GB hard cap
by deleting the oldest completed outputs first. Active jobs and everything
outside `app/output`—including models, LoRAs, uploads, imports, credentials, and
settings—are never touched. The Generate page provides matching Save policy and
Clean now controls.

```text
GET  /api/storage-policy
PUT  /api/storage-policy          # { enabled, retention_days, max_gb }
POST /api/storage-policy/cleanup  # optional { target_bytes }
```

## Model memory management

Fresh installs use **Immediate** and unload model memory after every completed
job so the Mac is ready for another sibling Studio. An explicitly saved
operator choice always wins. **Performance** keeps a model warm for fast repeat
generation, **Balanced** releases after 10 idle minutes, and **Memory Saver**
releases after 2 idle minutes. **Release
Memory / Unload Model** runs the same cleanup manually. No release starts while
generation is queued or running.

The cleanup removes cached model objects, runs Python garbage collection, and
clears available MLX/Metal and PyTorch MPS allocator caches. It does not delete
downloaded models or generated images. Studio Hub can inspect and apply the
same policy using the authenticated fleet API:

```text
GET  /api/memory-policy
PUT  /api/memory-policy   # { "mode": "performance|balanced|memory_saver|immediate" }
POST /api/memory/release
```

After Update and the next normal restart, the backend asks macOS to display it
as **Image Studio Mac** in Activity Monitor. This changes only the process label;
the service still uses Python internally to run the MLX generation libraries.

## GenStudio FLUX.2 Klein readiness

The qualified worker target is
`AITRADER/FLUX2-klein-4B-mlx-4bit` at immutable snapshot
`7fd24828501390b67a92c8b66d2fc5a707d0ba1a`. Image Studio now executes that
snapshot by local commit path, stages and validates one PNG before atomic
publication, and returns model/runtime, worker/machine, dimensions, steps,
resolved seed, media, size, checksum, and runtime evidence.

The protected model inventory reports the cached revision, qualification match,
execution readiness, and pinned upstream Apache-2.0 evidence. Health reports
only aggregate generation availability and queue state—never prompts, job IDs,
or asset paths. The GenStudio minimum tier is 8 GB unified memory, with 16 GB
recommended for stronger operating headroom. The durable benchmark was
recorded on 16 GB; the 8 GB floor is an owner-confirmed fleet operating limit
rather than a rewritten claim about that benchmark host.

`GET /api/catalog` includes a nullable `genstudio_candidate` object for exact
checkpoints with a checked-in model audit. This is candidate evidence, not a
publication flag: it binds the checkpoint revision, approved operation subset,
adapter/runtime, controls, limits, hardware floor, audit status, and contract
hash. Studio Hub applies its separate owner-controlled exposure decision before
advertising a candidate to GenStudio. The same nested object adds a live,
sanitized capacity observation; Image Studio's process-wide MLX lock means one
physical slot, reported as available only while the exact worker route is ready
and idle.

The Group A FLUX.2 Klein audit approves only `image.text_to_image` at the 1K
tier. Image Studio's sibling-only img2img/edit capabilities and experimental 2K
presets remain visible in the general catalog, but are not part of that
sellable candidate contract. Durable evidence lives under
`model-audits/<run-id>/`.

See [the ImageStudio–GenStudio integration record](docs/imagestudio_genstudio_integration.md)
for the capability matrix and cross-repository blockers. Studio Hub remains the
only site-local scheduler; Image Studio only serializes work already assigned
to this worker.

## Versioning

Image Studio KH uses [Semantic Versioning](https://semver.org/) with this project-specific interpretation:

- **MAJOR** (1.x.x → 2.x.x) — breaking change. Re-install required.
- **MINOR** (1.1.x → 1.2.x) — new engine / feature / model family. **Re-run "Install Generation"** to pick up any new Python deps.
- **PATCH** (1.2.0 → 1.2.1) — bugfix / UI tweak / catalog entry within an existing family. **Just run "Update"** from the Pinokio sidebar.

Current version is stored at the project root in [`VERSION`](VERSION). The full release history with what changed in each version lives in [`CHANGELOG.md`](CHANGELOG.md).

Every tracked change is release-gated: it must increase `VERSION` and add a
matching first changelog entry with at least one visible **What's New** detail.
Run `python3 release_metadata_check.py <base-ref>` before publishing; GitHub
also enforces the same rule for pull requests and pushes to `main`.

The WebUI footer shows the running version. The same value is also surfaced at:

- `GET /api/version` → `{"app_version": "1.0.0", "title": "Image Studio KH"}`
- `GET /api/health` → includes `app_version`
- `GET /api/generate/diagnostics` → includes `app_version`

Local generation also has verified memory self-protection. Image Studio retries
one genuine allocator failure after unloading cached engines and preserving the
resolved seed. A second allocator failure requests a supervised restart only
when the startup service is installed; normal validation, network,
cancellation, and disk errors never trigger that path. `/api/health`
and `/api/generate/diagnostics` expose privacy-safe memory and watchdog
restart-rate evidence for Studio Hub alerts.

## Truth audit (for contributors)

The Models tab shows a green "✓ engine ready" chip per model. That chip is driven by the `_WIRED_FAMILIES` set in `app/backend/generation.py`. If a family is in `_WIRED_FAMILIES` but its dispatch branch raises `NotImplementedError`, users see a green chip and then hit a wall when they click Generate.

To prevent that drift, run the truth audit before any release that touches `generation.py`:

```
python3 audit_truth.py            # human-readable report
python3 audit_truth.py --strict   # exits non-zero on drift (for CI)
```

The script reads `app/backend/catalog.py` + `app/backend/generation.py` via AST and reports four kinds of drift:

| Drift | Meaning | Severity |
|---|---|---|
| **Commission lies** | Family in `_WIRED_FAMILIES` but dispatch raises `NotImplementedError` | 🔴 BUG — user hits a wall |
| **Omission lies** | Dispatch handles the family but it's missing from `_WIRED_FAMILIES` | 🟡 False negative — UI underreports |
| **Orphan families** | Family appears in catalog but has no dispatch branch | 🟡 Silent fall-through to default error |
| **Phantom wires** | In `_WIRED_FAMILIES` but no catalog model uses the family | ⚪ Harmless dead config |

No deps beyond stdlib — runs without the venv.

## HTTP API (Phase 1)

```
GET  /api/health
GET  /api/catalog                  # models + families + live cache state
GET  /api/cache/{owner}/{name}     # one repo's cache state
GET  /api/downloads                # list jobs
POST /api/downloads                # { repo, token? }   start a download
DELETE /api/downloads/{id}         # cancel
GET  /api/downloads/stream         # SSE per-second snapshots
GET  /api/imports/scan             # list candidates from EXTRA_MODEL_DIRS
POST /api/imports                  # { source_path, repo? }
```

### Curl examples

```sh
# What models are available + what's already on disk?
curl http://<server>:<port>/api/catalog | jq

# Start a download (no token needed for ungated MLX repos)
curl -X POST http://<server>:<port>/api/downloads \
  -H 'content-type: application/json' \
  -d '{"repo": "AITRADER/FLUX2-klein-4B-mlx-4bit"}'

# Stream progress
curl -N http://<server>:<port>/api/downloads/stream
```

### Calling from your main Mac

1. In Pinokio on the mac mini, edit `ENVIRONMENT` and set
   `PINOKIO_SHARE_LOCAL=true`.
2. Restart the launcher. Pinokio prints a LAN URL alongside the local one.
3. From your main Mac, point requests at that LAN URL.

## Per-model size menu

Every catalog model carries a ready-to-use **`sizes`** array — `[{ aspect_ratio,
label, width, height, tier, default?, fixed? }]` — plus `default_aspect_ratio`
and a `custom` `{ min_px, max_px, step, max_pixels }` range (null for
fixed-output models). Local models get a `/16`-aligned ~1.3 MP ladder with
`tier` of `1K` or `2K`; a fixed-output model gets a single `fixed: true` size.
Clients (Story Studio) drive their aspect-ratio and resolution pickers straight
off it with no pixel math. See `app/backend/sizes.py`.

## Generation API

Local generation is implemented through
`POST /api/generate/{txt2img,img2img,edit}` with polling and SSE progress.
Text-to-image accepts JSON. Image-to-image/edit accept one bounded multipart
`image` plus the same controls; fleet callers can include `model_revision` in
either shape to require an exact cached commit. Poll
`GET /api/generate/jobs/{id}` until terminal, then fetch the single validated
PNG from `GET /api/generate/jobs/{id}/image` only when state is `done`.

Completed job JSON includes a `final_asset` evidence object. A WebUI batch of
up to eight variations is eight independent logical jobs, never previews or
multiple hidden files from one request.

Known GenStudio qualification limits and integration blockers are maintained in
[the ImageStudio–GenStudio integration record](docs/imagestudio_genstudio_integration.md).

## Run as an always-on server (auto-start + self-healing)

By default you start the app by opening Pinokio and clicking **Start**. If instead you want this Mac to behave like a **server** — the API always up, started automatically on boot, and self-healing — use the one-click service.

### Turn it on
In the Pinokio sidebar click **❤️ Install as Startup Service**. It:

- Installs a macOS **launchd LaunchAgent** that runs the server (`serve.sh`) on **port 47868**.
- **Starts automatically** every time you log in (so it comes back after a reboot).
- **Restarts itself if it crashes** (launchd `KeepAlive`).
- Adds a **health watchdog** that pings `/api/health` every 60s and relaunches
  the server only after three consecutive failures. A successful probe resets
  the counter, preventing one transient timeout from interrupting work.

No admin/sudo needed for this step. To remove it later, click **Startup Service: ON — click to remove**. Logs live in `logs/service/`. Reach the API over Tailscale/LAN at `http://<this-mac>:47868`.

> Use the **service OR** Pinokio's **Start** button — not both (they share port 47868).

### One-time Mac settings for full power-cut recovery (why they matter)
The service handles *software* restarts. To survive an actual **power outage** with zero human steps, each Mac also needs three system settings (admin-level, done once — the button does **not** change these):

1. **Power back on automatically when electricity returns**
   ```bash
   sudo pmset -a autorestart 1
   ```
   *Why:* otherwise the Mac stays off after the power drops. This boots it the moment power returns.

2. **Enable Automatic login** — System Settings ▸ Users & Groups ▸ *Automatically log in as …*
   *Why:* the Apple GPU (Metal / MLX) is **only available inside a logged-in session**. A service that starts before login can't use the GPU, so generation would fail or crawl on CPU.

3. **Turn FileVault OFF** — System Settings ▸ Privacy & Security ▸ FileVault
   *Why:* with FileVault on, a reboot stops at the encrypted-disk password screen and never reaches auto-login — so the server never comes back by itself.

With all three set **plus** the startup service: power returns → Mac powers on → auto-logs in → server + watchdog start with GPU access → crashes/hangs auto-recover. Fully hands-off.

### Rolling it out to many Macs
The service files ship inside this launcher, so on each Mac you just click **Install as Startup Service** once. Do the three system settings once per machine. Updates flow through the normal **Update** button.
