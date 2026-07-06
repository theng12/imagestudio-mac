# Generation UI Guide

Image Studio's Generate tab is intentionally progressive: everyday users see
only the inputs needed for a successful result, while model-specific tuning is
kept behind **Fine tune**.

## Source of truth

- `app/backend/catalog.py` owns model capabilities and `generation_profile()`.
- `app/frontend/app.js` applies model defaults and derives readiness.
- `app/frontend/index.html` renders controls only through `supportsControl()`.
- `app/backend/generation_installer.py` installs only
  `app/requirements-generation.txt`; it never accepts arbitrary packages or
  commands from the browser.

## Adding or changing a model

1. Add the model to `CATALOG` and set its real generation `capabilities`.
2. Update `generation_profile()` when the model needs defaults or controls that
   differ from its family or provider.
3. Never expose a control that the worker or cloud provider ignores. The
   supported control keys are `prompt`, `aspect_ratio`, `negative_prompt`,
   `steps`, `guidance`, `seed`, `batch`, `image_strength`,
   `runtime_quantization`, and `loras`.
   If a repository's on-disk conversion cannot be loaded by the current worker,
   set `runtime_compatible=False` and explain the exact blocker in
   `runtime_note`; do not advertise it as ready merely because its family is wired.
4. Keep high-quality, safe defaults in the profile. Changing model selection
   applies them automatically; users can override supported values under
   **Fine tune**.
5. If a new local engine needs packages, add pinned requirements to
   `requirements-generation.txt`, its package probes to `generation.py`, and
   its family dispatch before marking the engine ready.

## Readiness states

- Cloud models depend on provider credentials, not the local generation stack.
- Local models require a cached model, installed engine packages, and a wired
  worker.
- A package-complete family without a worker is **unavailable**, not broken.
- The in-app installer is useful in service mode because the launcher sidebar
  may not be present. In launchd service mode it restarts the service after a
  successful install; normal mode reports that one restart is still required.

## Verification

Run JavaScript syntax checking, Python compilation, `git diff --check`, and
validate every serialized catalog model has `generation_profile`. In the live
UI, test at least one distilled local model, one standard local model, one
fixed-size cloud model, and one keyless cloud model. Confirm the mobile layout
has no horizontal overflow and the browser console has no new errors.
