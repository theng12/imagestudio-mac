# ImageStudio–GenStudio integration

This living record covers the ImageStudio–GenStudio integration. Add future
model/runtime qualifications and cross-repository integration changes here.

## FLUX.2 Klein worker qualification

Audit date: 2026-07-20

This record covers Image Studio's worker boundary only. It does not activate a
customer product, add a public worker API, or move scheduling out of Studio Hub.
No live generation was started during this audit because fleet work had recently
completed on this worker; existing output and non-generative runtime inspection
were used instead.

## Immutable runtime identity

- Runtime repository: `AITRADER/FLUX2-klein-4B-mlx-4bit`
- Qualified snapshot: `7fd24828501390b67a92c8b66d2fc5a707d0ba1a`
- Upstream base model: `black-forest-labs/FLUX.2-klein-4B`
- Installed inference runtime observed during audit: `mflux 0.17.5`, `mlx 0.31.2`
- Worker release before these fixes: Image Studio `1.22.1`

New jobs resolve the requested commit to its local snapshot directory and pass
that immutable path to mflux. They no longer execute through the moving
repository alias. Final jobs report the actual Image Studio, mflux, and MLX
release tuple as `runtime_revision`.

## Internal license evidence

The MLX repackage's immutable model card identifies
`black-forest-labs/FLUX.2-klein-4B` as its base model. The repackage snapshot
does not contain a `LICENSE` file or a license card field; that absence is
recorded rather than hidden.

The upstream base-model evidence is pinned internally as:

- SPDX: `Apache-2.0`
- Upstream revision: `e7b7dc27f91deacad38e78976d1f2b499d76a294`
- License file SHA-256:
  `ca02bc51900ab07789d1b70283329e7137f5af98f5161c23a1c81fc38a4af1fe`
- Immutable evidence URL:
  `https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/blob/e7b7dc27f91deacad38e78976d1f2b499d76a294/LICENSE.md`

This preserves the upstream license evidence. It does not prove that the
third-party repackage preserved every redistribution notice or provide a
cryptographic mapping from its quantized tensors to that exact upstream
checkpoint. That provenance/notice gap remains a launch blocker.

## Capability matrix

| Capability | Image Studio worker | Current GenStudio envelope |
|---|---|---|
| Text to image | Implemented | Implemented |
| Image to image | Implemented with one uploaded image and `image_strength` | Not yet exposed by GenStudio's image product request |
| Instruction edit | Implemented with one uploaded image; mflux also supports multiple references internally | Not exposed |
| Aspect ratios | Catalog: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9; custom dimensions are also accepted | 1:1, 16:9, 9:16, 4:3, 3:4 |
| Dimensions | Catalog-safe range: 512–1536 per side, multiples of 16, at most 1.4 MP. Raw worker API accepts 512–2048, multiples of 8, at most 4 MP; the wider range is not GenStudio-qualified | 1024×1024, 1344×768, 768×1344, 1152×864, 864×1152 |
| Steps | Worker validation: 2–100; distilled default/recommendation: 4 | 2–8, default 4 |
| Seed | `null` or `-1` resolves to a random unsigned 32-bit seed; explicit 0–4,294,967,295 is preserved and returned | `null` random, or explicit 0–2,147,483,647 |
| Image count | Exactly one final image per logical worker request. The WebUI's 1–8 batch control creates separate logical jobs | Exactly one item/request |
| Input | One PNG, JPEG, or WebP; at most 20 MiB and 16,000,000 decoded pixels | No image input yet |
| Output | One validated PNG (`image/png`) | PNG only |
| Unified memory | 16 GB is the lowest tier with evidence in this audit and is the current minimum/recommended GenStudio tier | Must not schedule below 16 GB until an 8 GB qualification passes |

## Final asset and failure contract

Inference writes to `app/output/.working/<job>.png`. Image Studio decodes and
verifies that staged PNG, reads its actual dimensions and bytes, calculates
SHA-256, then atomically renames it to `app/output/<job>.png`. Only after that
rename does the job become `done` or receive an output URL. Cancellation,
invalid bytes, decode failure, or any inference exception removes staged/final
files and cannot publish success.

Every newly completed worker job returns:

- model and runtime revision;
- worker and machine identity;
- actual width and height;
- steps and resolved seed;
- image count, media type, format, byte size, and SHA-256;
- stable runtime duration.

Uploaded reference images are removed after terminal completion. Health reports
only aggregate availability/busy/queue state and runtime revision. Protected
inventory reports cache/readiness, immutable revision, qualification match, and
license evidence; neither response includes prompts, job IDs, input paths, or
output paths.

## Scheduler boundary and remaining blockers

Image Studio has only a process-local inference mutex to serialize requests
already assigned to it. It does not select a machine, acquire global work,
claim customer jobs, retry across sites, or schedule fleet capacity. Studio Hub
remains the sole site-local scheduler; GenStudio remains the global job and
business authority.

Remaining qualification blockers outside this worker-only change:

1. GenStudio's image module pins the correct runtime repository and revision,
   but it does not yet persist image-model license fields in its internal model
   record/third-party notice set.
2. Studio Hub currently omits image width, height, steps, resolved seed,
   `runtime_revision`, worker ID, and machine ID from its `terminal_result`
   envelope. Image Studio now supplies the worker evidence, but Hub/GenStudio
   must relay and retain it before end-to-end qualification is complete.
3. GenStudio availability currently checks cache and runtime compatibility but
   not the worker's `qualified_revision_match`/`execution_ready` fields.
4. The AITRADER repackage does not include an Apache license copy or exact
   upstream tensor provenance. Legal/provenance review must close that gap.
5. An idle, non-customer 8 GB Apple Silicon qualification run is required before
   lowering the advertised GenStudio memory floor below 16 GB.
6. Image-to-image remains a worker capability, not a GenStudio product operation.
