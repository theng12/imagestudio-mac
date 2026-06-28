# ImageStudio (Mac)

A custom Pinokio app for FLUX image generation on Apple Silicon. Mac-only
(`darwin` + `arm64`), built around [mflux](https://github.com/filipstrand/mflux)
and MLX.

> **Phase 1 status:** model catalog, download manager, and weight-import flows
> are live. Generation (txt2img / img2img / image edit) lands in Phase 2.

## What it does today

- Browse a curated catalog of FLUX-family models (FLUX.2 klein, FLUX.2 dev,
  FLUX.1 schnell/dev/**Krea**, Kontext, Qwen-Image, FIBO, Z-Image, and
  MLX-quantized variants), plus a **SeedVR2** image upscaler (in the
  Image-to-Image tab).
- **Two local engines.** Most models run on **mflux/MLX** (Apple-native, fast).
  A second **diffusers** engine (PyTorch/MPS) runs models mflux has no class for
  — **Stable Diffusion 3.5 Large** (gated) and **Sana 1600M** (ungated, the
  easiest to try). Each model declares its `engine`; diffusers models behave like
  any other local model in the UI but need the `torch`/`diffusers` deps (run
  **Install Generation**). Note: **Ideogram 4 can't run on Apple MPS** — its
  weights are fp8/nf4 (fp8 is an unsupported MPS dtype; nf4 needs CUDA-only
  bitsandbytes) — so it's parked until mflux ships native MLX support.
- **Cloud option (free):** alongside the local MLX models, the catalog includes
  **Pollinations FLUX** — a `provider="cloud"` entry that generates on
  Pollinations' free hosted API. No API key, no download, no local GPU; it runs
  on any Mac. Your prompt is sent to a third-party server and output is
  best-effort/rate-limited, so it's a convenience option, not a replacement for
  the local, offline, deterministic MLX models. See
  [Cloud providers](#cloud-providers-free) below.
- See at a glance which models are cached locally vs. need downloading.
- Confirm-before-download dialog with on-disk size and unified-memory
  recommendations so you don't accidentally fetch 60 GB.
- Resumable downloads — interrupt and re-trigger; partial files continue
  from the last byte offset.
- Import weights you already have elsewhere into HF cache via symlink
  (no copy, no duplication).
- HTTP API on `127.0.0.1:<port>` — call it from your main Mac over the LAN
  when you set `PINOKIO_SHARE_LOCAL=true` in `ENVIRONMENT`.

## Sidebar

- **Start** — launches the FastAPI server (`uvicorn`) and opens the UI.
- **Open UI / Models / Downloads** — deep-link tabs once the server is running.
- **HF Cache** — Pinokio file browser at `cache/HF_HOME/hub`.
- **Outputs** — generated images (Phase 2).
- **Update / Reinstall / Reset** — standard launcher lifecycle.

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

## Versioning

Image Studio KH uses [Semantic Versioning](https://semver.org/) with this project-specific interpretation:

- **MAJOR** (1.x.x → 2.x.x) — breaking change. Re-install required.
- **MINOR** (1.1.x → 1.2.x) — new engine / feature / model family. **Re-run "Install Generation"** to pick up any new Python deps.
- **PATCH** (1.2.0 → 1.2.1) — bugfix / UI tweak / catalog entry within an existing family. **Just run "Update"** from the Pinokio sidebar.

Current version is stored at the project root in [`VERSION`](VERSION). The full release history with what changed in each version lives in [`CHANGELOG.md`](CHANGELOG.md).

The WebUI footer shows the running version. The same value is also surfaced at:

- `GET /api/version` → `{"app_version": "1.0.0", "title": "Image Studio KH"}`
- `GET /api/health` → includes `app_version`
- `GET /api/generate/diagnostics` → includes `app_version`

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

## Cloud providers (free)

Most models in Image Studio KH run **locally** on Apple Silicon via mflux/MLX.
A second class of model — catalog entries with `provider: "cloud"` — generates
on a hosted API instead. There are **twelve**, all free or free-trial, spanning
several model families (FLUX, SDXL, SD3, NVIDIA Sana, Leonardo, Gemini):

| Model (`repo`) | Provider | Key needed? | Family / notes |
|---|---|---|---|
| `pollinations/flux` | Pollinations | **None** | **NVIDIA Sana** — zero-setup, no key; anon tier serves Sana |
| `cloudflare/flux-1-schnell` | Cloudflare Workers AI | Account ID + API token | FLUX schnell; free 10k neurons/day; **fixed output size** |
| `cloudflare/leonardo-lucid-origin` | Cloudflare Workers AI | Account ID + API token | **Leonardo Lucid** (non-FLUX/SD); photoreal; honors width/height |
| `cloudflare/leonardo-phoenix` | Cloudflare Workers AI | Account ID + API token | **Leonardo Phoenix** (non-FLUX/SD); strong prompt adherence |
| `cloudflare/sdxl-base` | Cloudflare Workers AI | Account ID + API token | **SDXL 1.0**; free; honors width/height + negative prompt |
| `cloudflare/sdxl-lightning` | Cloudflare Workers AI | Account ID + API token | **SDXL-Lightning**; fastest free CF model (few-step) |
| `cloudflare/dreamshaper-lcm` | Cloudflare Workers AI | Account ID + API token | **DreamShaper 8 LCM** (SD1.5); stylized/illustrative |
| `together/flux-1-schnell-free` | Together AI | API key | FLUX schnell; free endpoint; honors width/height, 4 steps |
| `gemini/gemini-2.5-flash-image` | Google AI Studio | API key **+ billing** | **Gemini Nano Banana** (non-FLUX/SD); **NOT free** — needs billing enabled (free tier = 0 image requests); fixed size + seed ignored |
| `nebius/flux-dev` | Nebius AI Studio | API key | **FLUX dev** quality; free trial credits, no card; honors width/height |
| `huggingface/flux-1-schnell` | Hugging Face | Reuses your **HF token** | FLUX schnell; token needs **Inference Providers** permission |
| `huggingface/sd3-medium` | Hugging Face | Reuses your **HF token** | **Stable Diffusion 3 Medium**; better text/prompt adherence |

Keys for the keyed providers are entered once in **Settings → Cloud provider
keys** (stored in `app/backend/settings.json`, gitignored, sent only to that
provider). Hugging Face is the exception — it reuses the same **Hugging Face
token** you set for downloads (it just needs the *Inference Providers*
permission), so there's no separate field. The examples below use Pollinations
because it needs no key, but the flow is identical for the others once their key
is saved.

Each cloud model's catalog entry also exposes `cloud_credentials_ok` (true only
when the required credential is set), `cloud_provider_label`, and
`cloud_signup_url` so the UI — and downstream consumers — can gate readiness and
link straight to where you get the key.

**How it works**

- No download, no local GPU, no `Install Generation` required — the cloud path
  is a plain HTTPS request, so it works on any Mac.
- In the UI it appears in the **Models** tab as ready (no download button) and
  in the **Generate** tab's model dropdown like any other txt2img model.
- Trade-offs: your prompt is sent to **Pollinations' servers** (don't use it for
  private/sensitive prompts), latency is variable, the service is rate-limited,
  and output is **not deterministic** even with a fixed seed.

**Generate with the cloud model — same endpoint as local models:**

```sh
# Curl — start a job against the cloud model (note: no download step needed)
curl -X POST http://<server>:<port>/api/generate/txt2img \
  -H 'content-type: application/json' \
  -d '{"repo": "pollinations/flux", "prompt": "a red apple on a wooden table", "width": 1024, "height": 1024}'
# → {"job": {"id": "...", "state": "running", ...}}
# Poll GET /api/generate/jobs/{id}; fetch the PNG at /api/generate/jobs/{id}/image
```

```javascript
// JavaScript
const res = await fetch("http://<server>:<port>/api/generate/txt2img", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ repo: "pollinations/flux", prompt: "a neon koi pond at night", width: 1024, height: 1024 }),
});
const { job } = await res.json();
```

```python
# Python
import requests
r = requests.post("http://<server>:<port>/api/generate/txt2img", json={
    "repo": "pollinations/flux", "prompt": "a misty pine forest", "width": 1024, "height": 1024,
})
job = r.json()["job"]
```

**Adding more cloud providers.** Drop a `CloudProvider` subclass into
`app/backend/providers/`, register it in `providers/__init__.py`'s `_REGISTRY`,
then add a catalog `ModelEntry` with `provider="cloud"`, a matching
`cloud_provider` id, and a `cloud_model_id`. Providers that need an API key
should read it from settings/`ENVIRONMENT` (Pollinations needs none). Cloud
entries are intentionally excluded from `audit_truth.py`, which only audits the
local mflux engine wiring.

## Phase 2 (coming)

- `mflux` and MLX installed into the conda env.
- `/api/generate/{txt2img,img2img,edit}` with streaming progress.
- LoRA picker + chaining with weight sliders.
- Aspect-ratio presets baked into the generate form.

## Patches / known limitations

Nothing patched in `app/` yet — this is greenfield code, not a fork.

## Run as an always-on server (auto-start + self-healing)

By default you start the app by opening Pinokio and clicking **Start**. If instead you want this Mac to behave like a **server** — the API always up, started automatically on boot, and self-healing — use the one-click service.

### Turn it on
In the Pinokio sidebar click **❤️ Install as Startup Service**. It:

- Installs a macOS **launchd LaunchAgent** that runs the server (`serve.sh`) on **port 47868**.
- **Starts automatically** every time you log in (so it comes back after a reboot).
- **Restarts itself if it crashes** (launchd `KeepAlive`).
- Adds a **health watchdog** that pings `/api/health` every 60s and relaunches the server if it ever hangs.

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
