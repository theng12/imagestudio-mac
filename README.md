# ImageStudio (Mac)

A custom Pinokio app for FLUX image generation on Apple Silicon. Mac-only
(`darwin` + `arm64`), built around [mflux](https://github.com/filipstrand/mflux)
and MLX.

> **Phase 1 status:** model catalog, download manager, and weight-import flows
> are live. Generation (txt2img / img2img / image edit) lands in Phase 2.

## What it does today

- Browse a curated catalog of FLUX models (FLUX.2 klein, FLUX.2 dev,
  FLUX.1 schnell/dev, MLX-quantized variants).
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

## Phase 2 (coming)

- `mflux` and MLX installed into the conda env.
- `/api/generate/{txt2img,img2img,edit}` with streaming progress.
- LoRA picker + chaining with weight sliders.
- Aspect-ratio presets baked into the generate form.

## Patches / known limitations

Nothing patched in `app/` yet — this is greenfield code, not a fork.
