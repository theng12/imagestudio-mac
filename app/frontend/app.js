/* global Alpine */

function studio() {
  return {
    // ──────── state ────────
    tab: "generate",
    health: { ok: false },
    showWhatsNew: false,
    releaseNotesCurrent: "",
    releaseNotes: [],
    // Hardware snapshot from /api/system — populated once on init().
    // Used by the Models tab to render per-card fit chips that compare each
    // model's memory floor against the user's actual RAM.
    system: { chip: null, chip_tier: null, unified_memory_gb: null },
    // ──────── RAM slider (Models tab hardware planner) ────────
    // Effective unified-memory budget used to score every model's fit chip
    // LIVE on the client. Defaults to detected RAM; the user can drag/type
    // it to preview a different machine (e.g. plan a 512 GB Mac before
    // buying it). Seeded in _initRamPlanner() after /api/system.
    ramGb: null,
    ramIsDetected: true,          // false once the user overrides the slider
    ramTiers: [8, 16, 24, 32, 48, 64, 128, 256, 512],
    families: {},
    models: [],
    jobs: [],
    candidates: [],
    loras: [],
    pendingDownload: null,
    confirmDialog: null,           // in-app confirm modal (webview-safe replacement for confirm())
    downloadToken: "",
    importForm: { source_path: "", repo: "" },
    importMessage: "",
    importMessageKind: "error",   // "success" | "error" — drives styling of the inline message
    importResult: null,            // last successful result, kept on screen with target path until next submit
    _streamHandle: null,
    _genStreamHandle: null,
    _refreshHandle: null,
    _tickHandle: null,
    _lastRandomPromptIndex: -1,
    _nowSec: Math.floor(Date.now() / 1000),   // reactive "now" for live duration display

    // ──────── generate sub-state ────────
    gen: {
      available: false,
      error: null,
      presets: [],
      mode: "txt2img",
      repo: "",
      prompt: "",
      negativePrompt: "",
      aspect: "1:1",
      width: 1024,
      height: 1024,
      steps: 4,
      guidance: 3.5,
      seed: -1,
      quantize: null,
      batchCount: 1,
      // img2img extras
      inputImageFile: null,        // the File / Blob from drop / picker / clipboard
      inputImageUrl: "",           // object URL for the preview
      inputImageName: "",          // display name
      imageStrength: 0.6,
      dragOver: false,             // UI flag for the drop zone hover state
      loraNames: [],
      loraWeights: {},
      advancedOpen: false,
      _profileRepo: "",
      // `busy` reflects "a job is running or queued" — used by the output area
      //   to show "Generating… N/M" progress text. NOT used by the Generate
      //   button anymore (would block queueing — see v1.2.3).
      busy: false,
      busyLabel: "Generating…",
      // `submitting` is transient — true ONLY during the POST. Used by the
      //   Generate button to prevent double-clicks. Always cleared on a 300ms
      //   timer so the user can submit again immediately (which queues the
      //   next job; backend _GEN_LOCK serializes execution).
      submitting: false,
      clearArmed: false,           // two-click confirm for Clear (webview-safe)
      deleteArmed: null,           // job.id currently armed for a two-click single delete
      pruneArmed: null,            // prune mode currently armed for a two-click confirm
      jobs: [],          // mirror of /api/generate/jobs (latest first)
      currentJob: null,
    },

    // ──────── diagnostics (dependency checklist) ────────
    diag: {
      device: null,
      packages: [],
      engines: [],
      any_missing: false,
      ready_count: 0,
      total_engines: 0,
      _lastFetched: 0,
    },

    generationInstall: {
      state: "idle",
      message: "",
      restart_required: false,
      log_tail: [],
      busy: false,
    },

    // Toast notifications (auto-dismiss after 5s)
    toasts: [],
    _toastSeq: 0,
    _jobStatePrev: {},   // map jobId → previous state, used to detect transitions for toasts

    // ──────── Models-tab library filters ────────
    // Models tab is split into two scopes: local (download + run on this Mac)
    // and cloud (hosted API). The toggle picks which set of models — and which
    // toolbar controls — are shown. Persisted across sessions.
    modelScope: "local",          // "local" | "cloud"

    modelFilters: {
      search: "",
      families: new Set(),
      statuses: new Set(),
      capabilities: new Set(),
      // Advanced filters stay opt-in so the full family catalog is visible.
      mlxOnly: false,           // pre-quantized MLX weights only
      fitsMyMac: false,         // when true, hide entries where fit.state === 'risky'
      // segmented RAM-fit filter, scored against the RAM slider:
      // "all" | "ok" (green) | "tight" (yellow) | "over" (red)
      fitLevel: "all",
      sortBy: "default",
      advancedOpen: false,
      openFamilies: new Set(),
      // Per-repo "show full details" toggle. Cards default to compact —
      // use_cases + best_for + saved-loc are hidden until the user expands.
      // Backed by a Set so toggling one card doesn't re-render every card.
      expandedRepos: new Set(),
    },

    // ──────── settings ────────
    settings: {
      hf_token_set: false,
      hf_token_masked: "",
      tokenInput: "",
      showToken: false,
      busy: false,
      message: "",
      messageKind: "info",   // "success" | "error" | "info"
    },
    autoUpdate: {
      loaded:false, busy:false, message:"", messageKind:"info", state:"idle",
      installed_version:"", latest_version:null, last_checked:null, next_check:null,
      last_update_result:null, defer_reason:null, rollback:null, details:[],
      update_available:false, scheduler:{installed:false}, release_notes_url:"",
      settings:{mode:"off",frequency:"daily",maintenance_hour:4,idle_only:true},
      draft:{mode:"off",frequency:"daily",maintenance_hour:4,idle_only:true},
      dirty:false,
    },
    memoryPolicy: {
      loaded:false, busy:false, mode:"performance", draftMode:"performance",
      default_mode:"performance", idle_seconds:null, options:[], active_jobs:0,
      last_activity_at:null, next_release_at:null, last_release_at:null,
      last_release_reason:null, last_release_details:null, last_error:null,
      release_count:0, process_title:"Image Studio Mac", dirty:false,
      message:"", messageKind:"info",
    },

    // ──────── cloud provider API keys (Settings tab) ────────
    // Backing state for the keyed cloud providers (Cloudflare, Together).
    // Pollinations needs no key, so it isn't represented here.
    cloudKeys: {
      cloudflare_account_id_set: false, cloudflare_account_id_masked: "",
      cloudflare_api_token_set: false,  cloudflare_api_token_masked: "",
      together_api_key_set: false,      together_api_key_masked: "",
      gemini_api_key_set: false,        gemini_api_key_masked: "",
      nebius_api_key_set: false,        nebius_api_key_masked: "",
      cfAccount: "", cfToken: "", together: "", gemini: "", nebius: "",   // input fields (cleared after save)
      showCfToken: false, showTogether: false, showGemini: false, showNebius: false,
      busy: false, message: "", messageKind: "info",
    },
    focusedCloudProvider: "cloudflare",

    // ──────── network/connectivity (where the API can be reached) ────────
    conn: {
      listen_port: null,
      bind_port: 47868,        // the true uvicorn --port from start.js;
                                // refreshed from /api/connectivity on load
      bind_host: "0.0.0.0",
      request_port: null,
      scheme: "http",
      client_url: "",
      addresses: [],
      share_local_enabled: false,
      share_local_port_fixed: null,
      share_passcode_set: false,
      pinokio_ui_port: 42000,
    },

    // ──────── lifecycle ────────
    /** Measure the actual height of .topbar and expose it as a CSS variable
     *  so sticky elements below (e.g. .library-toolbar) can offset themselves
     *  correctly even when the topbar wraps to multiple rows on narrow widths. */
    _syncTopbarHeight() {
      const el = document.querySelector('.topbar');
      if (!el) return;
      const h = Math.ceil(el.getBoundingClientRect().height);
      document.documentElement.style.setProperty('--topbar-height', h + 'px');
    },

        async init() {
      await this.refreshReleaseNotes();
      await this.refreshHealth();
      await this.refreshSystem();
      // Seed the RAM-slider budget from detected RAM (or a saved override).
      this._initRamPlanner();
      this._syncTopbarHeight();
      window.addEventListener('resize', () => this._syncTopbarHeight());
      // Also re-measure on next animation frame in case fonts/layout settle late.
      requestAnimationFrame(() => this._syncTopbarHeight());
      await this.refreshCatalog();
      this._initFilterPreferences();
      this._initFamilyLibrary();
      await this.refreshGenAvailability();
      await this.refreshDiagnostics();
      await this.refreshGenerationInstall();
      await this.refreshLoras();
      await this.refreshSettings();
      await this.refreshMemoryPolicy(true, true);
      await this.refreshAutoUpdate(true);
      this.startJobStream();
      this.startGenStream();
      this.refreshOutputStats();
      this.refreshStoragePolicy();
      // The catalog needs to reflect cache state changes during downloads,
      // so we re-poll it on a slower cadence than the per-job stream.
      this._refreshHandle = setInterval(() => this.refreshCatalog(), 4000);
      // 1Hz tick so live elapsed-time displays update without per-component timers.
      this._tickHandle = setInterval(() => { this._nowSec = Math.floor(Date.now() / 1000); }, 1000);
      setInterval(() => {
        if (this.tab === "settings" || ["checking","updating","restarting","deferred"].includes(this.autoUpdate.state)) this.refreshAutoUpdate(true);
        if (this.tab === "settings") this.refreshMemoryPolicy(true);
      }, 5000);
      // Route via hash so the sidebar buttons in pinokio.js can deep-link.
      const applyHash = () => {
        const h = (location.hash || "").replace(/^#\/?/, "");
        if (["generate", "models", "downloads", "imports", "api", "settings"].includes(h)) this.tab = h;
        if (h === "imports") this.scanImports();
        if (h === "settings") { this.refreshSettings(); this.refreshMemoryPolicy(true); this.refreshAutoUpdate(true); }
      };
      window.addEventListener("hashchange", applyHash);
      applyHash();

      // ── Keyboard shortcuts ──
      // Cmd/Ctrl+Enter from anywhere on the Generate tab submits.
      // (The textarea already has its own @keydown.cmd.enter; this global
      // handler covers focus on other controls.)
      document.addEventListener("keydown", (e) => {
        const isMeta = e.metaKey || e.ctrlKey;
        if (isMeta && e.key === "Enter" && this.tab === "generate") {
          e.preventDefault();
          this.submitGenerate();
        } else if (e.key === "Escape") {
          if (this.showWhatsNew) this.showWhatsNew = false;
          else if (this.pendingDownload) this.pendingDownload = null;
        }
      });

      // ── Clipboard paste → input image (img2img only) ──
      // Listens app-wide; only consumes the paste if the user is on the
      // Generate tab in img2img mode, so we don't steal pastes from textareas
      // / other inputs.
      document.addEventListener("paste", (e) => {
        if (this.tab !== "generate" || this.gen.mode !== "img2img") return;
        const items = e.clipboardData?.items || [];
        for (const it of items) {
          if (it.kind === "file" && it.type.startsWith("image/")) {
            const blob = it.getAsFile();
            if (blob) {
              e.preventDefault();
              this.setInputImage(blob, blob.name || "pasted-image.png");
              return;
            }
          }
        }
      });
    },

    // ──────── derived ────────
    get modelsByFamily() {
      const out = {};
      for (const m of this.models) {
        (out[m.family] ||= []).push(m);
      }
      return out;
    },

    // ─── RAM slider + client-side hardware fit ────────────────────────
    /** Effective RAM budget (GB) for fit scoring: slider value, else
     *  detected RAM, else a neutral 16 GB. */
    get effectiveRam() {
      return this.ramGb || this.system.unified_memory_gb || 16;
    },
    /** Client-side fit verdict for a model's memory floor vs effectiveRam.
     *  Mirrors backend system_info.fit_for() (1.5× comfortable / 1.0× tight /
     *  below = over budget) so the RAM slider re-scores every card instantly. */
    fitFor(minGb) {
      const actual = this.effectiveRam;
      const floor = Math.max(Number(minGb) || 0, 1);
      const headroom = actual / floor;
      let state;
      if (headroom >= 1.5)      state = "ok";
      else if (headroom >= 1.0) state = "tight";
      else                      state = "risky";
      const hint = headroom >= 1.5
        ? `${actual} GB is ≥1.5× this model's ${minGb} GB floor — comfortable headroom.`
        : headroom >= 1.0
          ? `${actual} GB just clears the ${minGb} GB floor — close other apps before loading.`
          : `${actual} GB is below the ${minGb} GB floor — it would swap heavily or fail to load.`;
      return { state, actual_gb: actual, required_gb: Number(minGb) || 0, hint };
    },
    setRam(gb) {
      const v = Math.max(1, Math.min(1024, Math.round(Number(gb) || 0)));
      this.ramGb = v;
      this.ramIsDetected = (v === this.system.unified_memory_gb);
      this._persistFilterPref("ramGb", v);
    },
    resetRamToDetected() {
      const d = this.system.unified_memory_gb;
      if (d) this.setRam(d);
    },
    /** Seed the RAM slider from a saved override or the detected RAM. */
    _initRamPlanner() {
      try {
        const saved = localStorage.getItem("imagestudio.modelFilters.ramGb");
        if (saved !== null && !isNaN(+saved)) {
          this.ramGb = +saved;
          this.ramIsDetected = (+saved === this.system.unified_memory_gb);
          return;
        }
      } catch {}
      this.ramGb = this.system.unified_memory_gb || 16;
      this.ramIsDetected = !!this.system.unified_memory_gb;
    },
    /** "✨ Best for your RAM" — recommendations that fit the current budget
     *  (fit ≠ risky). Image models barely differ by capability (almost all do
     *  txt2img + img2img + edit), so the lanes differentiate by what users
     *  actually trade off: top quality (heaviest), fastest (lightest), and
     *  best dedicated editing model. Re-computes live as the slider moves. */
    get bestPicks() {
      const fits  = (m) => this.fitFor(m.min_unified_memory_gb).state !== "risky";
      const heavy = (m) => (Number(m.min_unified_memory_gb) || 0) * 1000
                         + (Number(m.size_gb) || 0) * 10
                         + (/recommended/i.test(m.label || "") ? 5 : 0);
      const pickHeavy = (predicate) => {
        const c = (this.models || []).filter(m => !m.is_cloud && fits(m) && predicate(m));
        return c.length ? c.slice().sort((a, b) => heavy(b) - heavy(a))[0] : null;
      };
      const pickLight = (predicate) => {
        const c = (this.models || []).filter(m => !m.is_cloud && fits(m) && predicate(m));
        // Lightest on-disk model = fastest to load / iterate with.
        return c.length ? c.slice().sort((a, b) => (Number(a.size_gb) || 0) - (Number(b.size_gb) || 0))[0] : null;
      };
      const hasCap = (m, cap) => (m.capabilities || []).includes(cap);
      const buckets = [
        { id: "quality", label: "Best quality",     icon: "🏆", model: pickHeavy(() => true) },
        // Lightest LOCAL generator (exclude 0-size cloud entries so this lane
        // recommends a real download you can iterate on, not a hosted API).
        { id: "fast",    label: "Fastest / lightest", icon: "⚡", model: pickLight(m => hasCap(m, "txt2img") && (Number(m.size_gb) || 0) > 0) },
        { id: "edit",    label: "Best for editing",  icon: "🎨", model: pickHeavy(m => hasCap(m, "edit") && (Number(m.size_gb) || 0) > 0) },
      ];
      const seen = new Set();
      return buckets.filter(b => {
        if (!b.model || seen.has(b.model.repo)) return false;
        seen.add(b.model.repo);
        return true;
      });
    },

    // ─── Library filters (Models tab) ─────────────────────────────────
    get filteredModelsByFamily() {
      const f = this.modelFilters;
      const q = (f.search || "").trim().toLowerCase();
      const matches = (m) => {
        // Local/Cloud scope split (the Models tab toggle).
        if (this.modelScope === "cloud" && !m.is_cloud) return false;
        if (this.modelScope === "local" && m.is_cloud) return false;
        if (f.families.size > 0 && !f.families.has(m.family)) return false;
        if (f.statuses.size > 0) {
          const state = m.cache?.state || "absent";
          const isReady = this.isModelReady ? this.isModelReady(m.repo) : (state === "cached");
          const matchesState = f.statuses.has(state) || (f.statuses.has("engine-ready") && isReady);
          if (!matchesState) return false;
        }
        if (f.capabilities.size > 0) {
          const caps = new Set(m.capabilities || []);
          for (const wanted of f.capabilities) {
            if (!caps.has(wanted)) return false;
          }
        }
        // Hardware filters below only apply to LOCAL models (cloud models have
        // no MLX/RAM-fit concept). Guarding by scope also prevents a persisted
        // mlxOnly=true from wiping out the cloud tab.
        if (this.modelScope === "local") {
          // Apple Silicon (MLX) filter — only show pre-quantized MLX entries.
          if (f.mlxOnly && !m.apple_optimized) return false;
          // Fits my Mac filter — hide entries that would OOM/swap heavily.
          // We exclude only "risky" (below floor); "tight" still shows since the
          // user might consciously accept that trade-off. "unknown" also shows
          // since we don't have evidence either way.
          if (f.fitLevel && f.fitLevel !== "all") {
            const st = this.fitFor(m.min_unified_memory_gb).state;
            if (f.fitLevel === "ok"    && st !== "ok")    return false;
            if (f.fitLevel === "tight" && st !== "tight") return false;
            if (f.fitLevel === "over"  && st !== "risky") return false;
          }
          if (f.fitsMyMac && this.fitFor(m.min_unified_memory_gb).state === "risky") return false;
        }
        if (q) {
          const hay = ((m.label || "") + " " + (m.family_label || "") + " "
            + (m.repo || "") + " " + (m.best_for || "")).toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      };
      const out = {};
      for (const m of this.models) {
        if (!matches(m)) continue;
        (out[m.family] ||= []).push(m);
      }
      const cmp = (() => {
        switch (f.sortBy) {
          case "name":      return (a, b) => (a.label || "").localeCompare(b.label || "");
          case "size-asc":  return (a, b) => (a.size_gb || 0) - (b.size_gb || 0);
          case "size-desc": return (a, b) => (b.size_gb || 0) - (a.size_gb || 0);
          default:          return (a, b) => (a.size_gb || 0) - (b.size_gb || 0);
        }
      })();
      for (const fam of Object.keys(out)) out[fam].sort(cmp);
      return out;
    },
    /** True when a model belongs to the currently-selected scope tab. */
    inScope(m) {
      return this.modelScope === "cloud" ? !!m.is_cloud : !m.is_cloud;
    },
    get localModelCount() { return this.models.filter(m => !m.is_cloud).length; },
    get cloudModelCount() { return this.models.filter(m => m.is_cloud).length; },
    /** Total models in the current scope (the "of N" denominator). */
    get scopedModelCount() { return this.models.filter(m => this.inScope(m)).length; },
    get availableCapabilities() {
      const set = new Set();
      for (const m of this.models) {
        if (!this.inScope(m)) continue;
        for (const c of (m.capabilities || [])) set.add(c);
      }
      const order = { txt2img: 0, img2img: 1, edit: 2 };
      return Array.from(set).sort((a, b) => (order[a] ?? 99) - (order[b] ?? 99) || a.localeCompare(b));
    },
    get availableFamilies() {
      const seen = new Set();
      const out = [];
      for (const m of this.models) {
        if (!this.inScope(m)) continue;
        if (seen.has(m.family)) continue;
        seen.add(m.family);
        out.push({ id: m.family, label: m.family_label || this.families?.[m.family]?.label || m.family });
      }
      return out.sort((a, b) => a.label.localeCompare(b.label));
    },
    /** Family-first view model. Cached families come first, followed by those
     *  with a variant that fits the selected RAM budget, then alphabetically. */
    get visibleFamilies() {
      const families = Object.values(this.families || {})
        .map(f => ({ ...f, models: this.filteredModelsByFamily[f.id] || [] }))
        .filter(f => f.models.length > 0);
      const rank = (f) => {
        const cached = f.models.some(m => m.cache?.state === "cached") ? 0 : 1;
        const fits = this.modelScope === "cloud"
          || f.models.some(m => this.fitFor(m.min_unified_memory_gb).state !== "risky") ? 0 : 1;
        return cached * 100 + fits * 10;
      };
      return families.sort((a, b) => rank(a) - rank(b) || a.label.localeCompare(b.label));
    },
    familyCapabilities(family) {
      const caps = new Set();
      for (const m of (family.models || [])) {
        for (const cap of (m.capabilities || [])) caps.add(cap);
      }
      return Array.from(caps);
    },
    familyRuntimeLabel(family) {
      if (this.modelScope === "cloud") return "Hosted API";
      const engines = new Set((family.models || []).map(m => m.engine));
      if (engines.has("mflux") && engines.has("diffusers")) return "MLX + MPS";
      if (engines.has("diffusers")) return "PyTorch / MPS";
      return "Apple MLX";
    },
    familyMemoryLabel(family) {
      if (this.modelScope === "cloud") return "No download";
      const floors = (family.models || []).map(m => Number(m.min_unified_memory_gb) || 0);
      return floors.length ? `from ${Math.min(...floors)} GB RAM` : "RAM varies";
    },
    familyCachedCount(family) {
      return (family.models || []).filter(m => m.cache?.state === "cached").length;
    },
    isRecommendedFamily(family) {
      return this.modelScope === "local" && !!this.bestPicks[0]
        && (family.models || []).some(m => m.repo === this.bestPicks[0].model.repo);
    },
    familyTone(family) {
      const caps = this.familyCapabilities(family);
      if (caps.includes("edit") && !caps.includes("txt2img")) return "tone-edit";
      if (caps.includes("img2img") && !caps.includes("txt2img")) return "tone-upscale";
      if (this.modelScope === "cloud") return "tone-cloud";
      if ((family.models || []).some(m => m.engine === "diffusers")) return "tone-mps";
      return "tone-mlx";
    },
    modelVariantLabel(model) {
      const family = this.families?.[model.family];
      const familyLabel = family?.label || model.family_label || "";
      let label = model.label || model.repo;
      if (familyLabel && label.toLowerCase().startsWith(familyLabel.toLowerCase())) {
        label = label.slice(familyLabel.length).replace(/^\s*(?:[-—:]+)\s*/, "");
      }
      return label || "Standard";
    },
    modelRuntimeLabel(model) {
      if (model.is_cloud) return model.cloud_provider_label || "Cloud";
      return model.engine === "diffusers" ? "PyTorch / MPS" : "Apple MLX";
    },
    modelFormatLabel(model) {
      if (model.is_cloud) return "Hosted";
      if (model.quantization === "mlx-2bit") return "Pre-quantized 2-bit";
      if (model.quantization === "mlx-4bit") return "Pre-quantized 4-bit";
      if (model.quantization === "mlx-8bit") return "Pre-quantized 8-bit";
      if (model.engine === "diffusers") return "Diffusers weights";
      return "Full weights";
    },
    modelRoleLabel(model) {
      if (/recommended/i.test(model.label || "")) return "Recommended";
      if (model.quantization === "mlx-2bit") return "Smallest";
      if (model.quantization === "mlx-4bit") return "Fastest loads";
      if (model.quantization === "mlx-8bit") return "Balanced";
      if (/full/i.test(model.label || "")) return "Full fidelity";
      if ((model.capabilities || []).length === 1 && model.capabilities[0] === "edit") return "Editing";
      if ((model.capabilities || []).length === 1 && model.capabilities[0] === "img2img") return "Upscaling";
      return "";
    },
    get filteredModelTotalCount() {
      return Object.values(this.filteredModelsByFamily).reduce((s, list) => s + list.length, 0);
    },
    get hasActiveFilters() {
      const f = this.modelFilters;
      return !!(f.search.trim() || f.families.size || f.statuses.size || f.capabilities.size
                || f.mlxOnly || f.fitsMyMac || (f.fitLevel && f.fitLevel !== "all"));
    },
    /** Human-readable breakdown of every active filter — used by the empty
     *  state so users can SEE what cut their results and tap any single
     *  filter off without losing the others. Returns array of:
     *    { label, removeFn }  ← removeFn unsets just that one filter
     */
    activeFilterSummary() {
      const f = this.modelFilters;
      const out = [];
      if (f.search.trim()) {
        out.push({ label: `search: "${f.search.trim()}"`, removeFn: () => this.modelFilters.search = "" });
      }
      for (const fam of f.families) {
        const famLabel = this.availableFamilies.find(x => x.id === fam)?.label || fam;
        out.push({ label: `family: ${famLabel}`, removeFn: () => this.toggleFamilyFilter(fam) });
      }
      for (const status of f.statuses) {
        out.push({ label: `status: ${status}`, removeFn: () => this.toggleStatusFilter(status) });
      }
      for (const cap of f.capabilities) {
        out.push({ label: `capability: ${cap}`, removeFn: () => this.toggleCapabilityFilter(cap) });
      }
      if (f.mlxOnly) {
        out.push({ label: "🍎 MLX only", removeFn: () => this.toggleMlxFilter() });
      }
      if (f.fitsMyMac) {
        out.push({ label: "🖥 Fits my Mac", removeFn: () => this.toggleFitsMyMacFilter() });
      }
      if (f.fitLevel && f.fitLevel !== "all") {
        const lbl = { ok: "✓ Fits", tight: "⚠ Tight", over: "✗ Over budget" }[f.fitLevel] || f.fitLevel;
        out.push({ label: `RAM fit: ${lbl}`, removeFn: () => this.modelFilters.fitLevel = "all" });
      }
      return out;
    },
    toggleFamilyFilter(familyId) {
      const s = this.modelFilters.families;
      if (s.has(familyId)) s.delete(familyId); else s.add(familyId);
      this.modelFilters.families = new Set(s);
    },
    toggleStatusFilter(status) {
      const s = this.modelFilters.statuses;
      if (s.has(status)) s.delete(status); else s.add(status);
      this.modelFilters.statuses = new Set(s);
    },
    toggleCapabilityFilter(cap) {
      const s = this.modelFilters.capabilities;
      if (s.has(cap)) s.delete(cap); else s.add(cap);
      this.modelFilters.capabilities = new Set(s);
    },
    /** Opt-in filter for weights already converted to MLX quantization. */
    toggleMlxFilter() {
      this.modelFilters.mlxOnly = !this.modelFilters.mlxOnly;
    },
    /** Toggle "Fits my Mac" — hides entries that would OOM/swap on this hardware. */
    toggleFitsMyMacFilter() {
      this.modelFilters.fitsMyMac = !this.modelFilters.fitsMyMac;
    },
    /** Helper: write a filter preference to localStorage. App-namespaced
     *  ("imagestudio.…") so the 3 apps don't collide if ever served same-origin.
     *  Silently no-ops if localStorage is unavailable (private mode etc.). */
    _persistFilterPref(name, value) {
      try {
        localStorage.setItem(`imagestudio.modelFilters.${name}`, String(value));
      } catch {}
    },
    /** Restore durable scope/RAM preferences. Format filters intentionally do
     *  not persist: opening Models should never hide most of the catalog. */
    _initFilterPreferences() {
      try {
        this.modelFilters.mlxOnly = false;
        this.modelFilters.fitsMyMac = false;
        localStorage.removeItem("imagestudio.modelFilters.mlxOnly");
        localStorage.removeItem("imagestudio.modelFilters.fitsMyMac");
        const savedScope = localStorage.getItem("imagestudio.modelFilters.modelScope");
        if (savedScope === "local" || savedScope === "cloud") {
          this.modelScope = savedScope;
        }
      } catch {}
    },
    _initFamilyLibrary() {
      if (this.modelFilters.openFamilies.size > 0) return;
      this._openBestFamilyForScope();
    },
    _openBestFamilyForScope() {
      const inScope = (this.models || []).filter(m => this.inScope(m));
      const cached = inScope.find(m => m.cache?.state === "cached");
      const fitting = inScope.find(m => this.modelScope === "cloud"
        || this.fitFor(m.min_unified_memory_gb).state !== "risky");
      const first = cached || fitting || inScope[0];
      this.modelFilters.openFamilies = new Set(first ? [first.family] : []);
    },
    /** Switch the Models tab between Local and Cloud. Filters are scope-specific
     *  (families/statuses/etc. only exist in one scope), so reset them on switch
     *  to avoid landing on an accidentally-empty list. Search + sort persist. */
    setModelScope(scope) {
      if (scope !== "local" && scope !== "cloud") return;
      if (this.modelScope === scope) return;
      this.modelScope = scope;
      this.modelFilters.families = new Set();
      this.modelFilters.statuses = new Set();
      this.modelFilters.capabilities = new Set();
      this.modelFilters.mlxOnly = false;
      this.modelFilters.fitLevel = "all";
      this._persistFilterPref("modelScope", scope);
      this._openBestFamilyForScope();
    },
    /** Per-card expand/collapse. Default state is collapsed (compact card);
     *  the user clicks "Show details" to reveal best_for + use_cases + saved-loc. */
    isModelExpanded(repo) {
      return this.modelFilters.expandedRepos.has(repo);
    },
    toggleModelExpanded(repo) {
      const s = this.modelFilters.expandedRepos;
      if (s.has(repo)) s.delete(repo); else s.add(repo);
      this.modelFilters.expandedRepos = new Set(s);
    },
    /** Bulk "expand all visible" / "collapse all visible" — operates on the
     *  currently-filtered model list, so users can rapidly survey only the
     *  cards they're looking at. */
    expandAllVisible() {
      const s = new Set(this.modelFilters.expandedRepos);
      for (const list of Object.values(this.filteredModelsByFamily)) {
        for (const m of list) s.add(m.repo);
      }
      this.modelFilters.expandedRepos = s;
    },
    collapseAllVisible() {
      // Reset entirely — simpler and consistent with "make all cards compact again"
      this.modelFilters.expandedRepos = new Set();
    },
    toggleFamilyOpen(familyId) {
      const s = this.modelFilters.openFamilies;
      if (s.has(familyId)) s.delete(familyId); else s.add(familyId);
      this.modelFilters.openFamilies = new Set(s);
    },
    isFamilyFiltered(familyId)   { return this.modelFilters.families.has(familyId); },
    isStatusFiltered(status)     { return this.modelFilters.statuses.has(status); },
    isCapFiltered(cap)           { return this.modelFilters.capabilities.has(cap); },
    isFamilyOpen(familyId) {
      return this.modelFilters.openFamilies.has(familyId)
        || !!this.modelFilters.search.trim()
        || this.modelFilters.families.has(familyId);
    },
    clearAllFilters() {
      this.modelFilters.search = "";
      this.modelFilters.families = new Set();
      this.modelFilters.statuses = new Set();
      this.modelFilters.capabilities = new Set();
      this.modelFilters.mlxOnly = false;
      this.modelFilters.fitsMyMac = false;
      this.modelFilters.fitLevel = "all";
      this.modelFilters.sortBy = "default";
      // ramGb intentionally NOT reset — it's a hardware setting, not a filter.
      // NOTE: intentionally NOT resetting expandedRepos — that's a separate
      // user concern (collapseAllVisible has its own dedicated button).
    },

    get activeDownloadCount() {
      return this.jobs.filter(j => ["queued", "running", "cancelling"].includes(j.state)).length;
    },

    get finishedDownloadCount() {
      return this.jobs.filter(j => ["done", "error", "cancelled"].includes(j.state)).length;
    },

    // ──────── generate-tab derived ────────
    get cachedModels() {
      return this.models.filter(m => m.cache?.state === "cached");
    },

    get modeCompatibleModels() {
      // Show only cached models that declare support for the current Generate
      // subtab. Keeps the dropdown short and prevents picking an edit-incapable
      // model on the Edit subtab.
      const mode = this.gen.mode || "txt2img";
      return this.cachedModels.filter(m => (m.capabilities || []).includes(mode));
    },

    get selectedModel() {
      return this.cachedModels.find(m => m.repo === this.gen.repo) || null;
    },

    get selectedProfile() {
      return this.selectedModel?.generation_profile || { controls: {}, defaults: {}, summary: "" };
    },

    supportsControl(name) {
      return this.selectedProfile?.controls?.[name] !== false;
    },

    get selectedReadiness() {
      const m = this.selectedModel;
      if (!m) return { state: "empty", label: "Choose a model", detail: "Download a model or choose a cloud option to begin." };
      if (m.is_cloud) {
        if (m.fit?.state === "needs_billing") return { state: "blocked", label: "Billing required", detail: m.fit.hint };
        if (m.cloud_credentials_ok === false) return { state: "blocked", label: "API key required", detail: m.fit?.hint || "Add this provider in Settings." };
        return { state: "ready", label: "Cloud ready", detail: "No local engine or model download is required." };
      }
      if (m.runtime_compatible === false) {
        return { state: "blocked", label: "Conversion format unsupported", detail: m.runtime_note || "This model needs a compatible local loader." };
      }
      const engine = this.modelEngine(m.repo);
      if (!this.gen.available || (engine && !engine.deps_ok)) {
        return { state: "install", label: "Engine needs installation", detail: "Install the local generation engines once on this server." };
      }
      if (engine && !engine.wired) {
        return { state: "blocked", label: "Model worker unavailable", detail: "Its packages are installed, but this model does not have a generation worker yet." };
      }
      if (engine && !engine.ready) {
        return { state: "install", label: "Engine needs repair", detail: "One or more required packages are missing." };
      }
      return { state: "ready", label: "Ready on this Mac", detail: `${m.engine === "diffusers" ? "PyTorch / MPS" : "Apple MLX"} engine is installed.` };
    },

    /** Whether the Generate button can be clicked right now.
     *  Intentionally does NOT include `gen.busy` — a running job is fine to
     *  queue behind. Backend's _GEN_LOCK serializes execution. */
    get canSubmit() {
      if (!this.selectedModel) return false;
      if (!this.selectedModel.is_cloud && !this.gen.available) return false;
      if (this.supportsControl("prompt") && !this.gen.prompt.trim()) return false;
      if (this.gen.submitting) return false;
      if (this.gen.repo && !this.isModelReady(this.gen.repo)) return false;
      // img2img/edit need an input image too
      if ((this.gen.mode === "img2img" || this.gen.mode === "edit") && !this.gen.inputImageFile) {
        return false;
      }
      return true;
    },

    // ─── Queue UX (Level 1: surface pending/running jobs) ─────────────
    get pendingJobs() {
      return (this.gen.jobs || [])
        .filter(j => j.state === "queued" || j.state === "running")
        .sort((a, b) => (a.started_at || 0) - (b.started_at || 0));
    },
    get queuedCount() {
      return (this.gen.jobs || []).filter(j => j.state === "queued").length;
    },
    get runningJob() {
      return (this.gen.jobs || []).find(j => j.state === "running") || null;
    },
    get hasPending() {
      return this.pendingJobs.length > 0;
    },
    get outputSizeLabel() {
      return humanBytes(this.outputStats.bytes || 0);
    },
    async cancelPending(job) {
      if (!job || !job.id) return;
      // Capture the state BEFORE the request — backend may have flipped it by
      // the time the response comes back. Used to decide which toast to show.
      const wasRunning = job.state === "running";
      try {
        const r = await fetch("/api/generate/jobs/" + encodeURIComponent(job.id), { method: "DELETE" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          this.pushToast({ kind: "warn", icon: "⚠", title: "Couldn't cancel",
            body: (err && err.detail) || ("HTTP " + r.status) });
          return;
        }
        if (wasRunning) {
          // Running jobs can't be stopped mid-mflux. Tell the user honestly.
          this.pushToast({
            kind: "info", icon: "⏸",
            title: "Cancel signal sent",
            body: "Running jobs can't stop mid-generation (mflux doesn't honor cancellation). " +
                  "The result will be discarded when generation finishes.",
          });
        } else {
          this.pushToast({ kind: "info", icon: "✓", title: "Cancelled", body: "Queued job removed." });
        }
      } catch (e) {
        this.pushToast({ kind: "error", icon: "✗", title: "Cancel failed", body: String(e) });
      }
    },
    truncateText(s, n = 80) {
      if (!s) return "";
      return s.length > n ? s.slice(0, n) + "…" : s;
    },

    // ─── History pagination + richer metadata ─────────────────────────
    historyPage: 0,
    historyPageSize: 12,   // 4 cols × 3 rows in the image grid feels right
    get historyJobs() {
      // ALL finished results, newest-first — including the one currently shown
      // in the main view. (Previously this sliced off the newest, which made it
      // unreachable once you clicked an older tile.) The grid highlights whichever
      // one is currently open and badges the newest.
      return (this.gen.jobs || [])
        .filter(j => j.state === "done" || j.state === "error" || j.state === "cancelled");
    },
    /** Newest finished result (history is newest-first). */
    get newestJob() {
      return (this.historyJobs || [])[0] || null;
    },
    /** True when the main view is showing the newest result (or a still-running
     *  job, or nothing) — i.e. there's nothing newer to jump back to. */
    get isViewingNewest() {
      const cur = this.gen.currentJob;
      if (!cur) return true;
      if (!["done", "error", "cancelled"].includes(cur.state)) return true; // running/queued
      return !this.newestJob || cur.id === this.newestJob.id;
    },
    /** Jump the main view back to the latest result. */
    backToLatest() {
      const n = this.newestJob || (this.gen.jobs || [])[0];
      if (n) { this.gen.currentJob = n; this.historyPage = 0; }
    },
    /** Open a specific job in the main view (and page the grid to it). */
    viewJob(job) {
      if (job) this.gen.currentJob = job;
    },
    copyPrompt(job) {
      const p = job?.params?.prompt || "";
      if (!p) return;
      this.copyText(p);
      this.pushToast({ kind: "success", icon: "📋", title: "Prompt copied", body: "" });
    },
    /** Relative "finished N ago" label for a job. */
    jobTimeLabel(job) {
      const t = job?.finished_at || job?.started_at;
      if (!t) return "";
      const diff = (Date.now() / 1000) - t;
      if (diff < 45) return "just now";
      if (diff < 3600) return Math.floor(diff / 60) + "m ago";
      if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
      return Math.floor(diff / 86400) + "d ago";
    },
    /** Provider label for a cloud job, else the local engine label. */
    jobProviderLabel(job) {
      const repo = job?.params?.repo;
      const m = (this.models || []).find(x => x.repo === repo);
      if (m && m.runtime_compatible === false) return false;
      if (m?.is_cloud) return m.cloud_provider_label || "cloud";
      return null;
    },
    get historyPageCount() {
      return Math.max(1, Math.ceil(this.historyJobs.length / this.historyPageSize));
    },
    get pagedHistoryJobs() {
      const last = Math.max(0, this.historyPageCount - 1);
      if (this.historyPage > last) this.historyPage = last;
      const start = this.historyPage * this.historyPageSize;
      return this.historyJobs.slice(start, start + this.historyPageSize);
    },
    historyNextPage() { if (this.historyPage < this.historyPageCount - 1) this.historyPage += 1; },
    historyPrevPage() { if (this.historyPage > 0) this.historyPage -= 1; },
    historyModelLabel(job) {
      const repo = job?.params?.repo;
      if (!repo) return "(unknown model)";
      const m = (this.models || []).find(x => x.repo === repo);
      return m?.label || repo;
    },
    /** Image-side params summary: aspect/dim + steps + guidance. */
    historyParamsLabel(job) {
      const p = job?.params || {};
      const parts = [];
      if (p.aspect) parts.push(p.aspect);
      else if (p.width && p.height) parts.push(p.width + "×" + p.height);
      if (typeof p.steps === "number") parts.push(p.steps + " steps");
      if (typeof p.guidance === "number") parts.push("guidance " + p.guidance);
      if (typeof p.image_strength === "number") parts.push("strength " + p.image_strength);
      return parts.join(" · ");
    },

    // ──────── per-model dependency lookup (wired to diagnostics) ────────
    modelEngine(repo) {
      const m = (this.models || []).find(x => x.repo === repo);
      if (!m) return null;
      return (this.diag.engines || []).find(e => e.family === m.family) || null;
    },
    isModelReady(repo) {
      if (!repo) return false;
      // Cloud models have no local engine — readiness = required credential set.
      // The backend reports cloud_credentials_ok (false for Cloudflare/Together
      // when their key/token is missing; always true for Pollinations + local).
      const m = (this.models || []).find(x => x.repo === repo);
      // Cloud: needs the credential set AND (for billing-gated models like Gemini)
      // billing enabled — which surfaces as fit.state === 'needs_billing'.
      if (m && m.is_cloud) return m.cloud_credentials_ok !== false && m.fit?.state !== 'needs_billing';
      const e = this.modelEngine(repo);
      if (!e) return true;   // unknown engine → assume ready; API will 503 if not
      return !!e.ready;
    },
    modelMissingDeps(repo) {
      const e = this.modelEngine(repo);
      return e ? (e.missing || []) : [];
    },
    modelDepsOk(repo) {
      // Packages are importable — the family just might not have a worker wired up yet.
      const e = this.modelEngine(repo);
      if (!e) return true;
      if (typeof e.deps_ok === "boolean") return e.deps_ok;
      return !!e.ready;
    },
    modelOptionLabel(m) {
      if (m.runtime_compatible === false) return `◌ ${m.label} — format support pending`;
      const e = (this.diag.engines || []).find(x => x.family === m.family);
      if (!e || e.ready) return m.label;
      // Distinguish "missing packages" (fixable by user) from "worker in roadmap"
      // (not the user's fault — just hasn't shipped yet).
      if (e.deps_ok === true && e.wired === false) {
        return `🕓 ${m.label} — worker in roadmap`;
      }
      return `⚠ ${m.label} — needs ${(e.missing || []).join(", ")}`;
    },

    get canRuntimeQuant() {
      // Only full checkpoints accept runtime quantization. Pre-quantized MLX
      // variants are already at their final precision.
      const m = this.selectedModel;
      return !!m && !m.apple_optimized;
    },

    get outputFrameStyle() {
      // Match the frame to the image being shown (the current job's dimensions),
      // falling back to the form's size for the empty/placeholder state.
      const p = this.gen.currentJob?.params;
      const w = (p && p.width) || this.gen.width || 1024;
      const h = (p && p.height) || this.gen.height || 1024;
      return `aspect-ratio: ${w} / ${h};`;
    },

    // FLUX text encoders (T5-XXL for FLUX.1, similar for FLUX.2) typically take
    // ~512 tokens. Tokens ≠ characters, but for English ~3-4 chars per token is
    // a reasonable rule of thumb. 1500 chars ≈ 400–500 tokens, so we warn near
    // there. This is intentionally a soft limit — we don't block submission.
    get promptSoftLimit() {
      // Future hook: vary per model. For now FLUX-family models all share roughly
      // the same encoder ceiling.
      return 1500;
    },

    // ──────── API tab derived ────────
    get apiBase() {
      return window.location.origin;
    },

    get curlExample() {
      const base = this.apiBase;
      const repo = this.gen.repo || "AITRADER/FLUX2-klein-4B-mlx-4bit";
      const body = JSON.stringify({
        repo,
        prompt: "a sun-drenched cafe in Lisbon at golden hour",
        width: 1024, height: 1024, steps: 4, guidance: 3.5, seed: -1,
      });
      return [
        "# 1. Start generation — returns a job id immediately",
        "curl -s -X POST " + base + "/api/generate/txt2img \\",
        "  -H 'content-type: application/json' \\",
        "  -d '" + body + "'",
        "# → returns: {\"job\": {\"id\": \"abc123\", \"state\": \"queued\", ...}}",
        "",
        "# 2. Poll the job until state == done",
        "curl -s " + base + "/api/generate/jobs/abc123",
        "",
        "# 3. Save the PNG to disk",
        "curl -s -o out.png " + base + "/api/generate/jobs/abc123/image",
      ].join("\n");
    },

    get jsExample() {
      const base = this.apiBase;
      const repo = this.gen.repo || "AITRADER/FLUX2-klein-4B-mlx-4bit";
      const lines = [
        "const SERVER = " + JSON.stringify(base) + ";",
        "",
        "// 1. Kick off generation",
        "const start = await fetch(SERVER + '/api/generate/txt2img', {",
        "  method: 'POST',",
        "  headers: { 'content-type': 'application/json' },",
        "  body: JSON.stringify({",
        "    repo: " + JSON.stringify(repo) + ",",
        "    prompt: 'a sun-drenched cafe in Lisbon at golden hour',",
        "    width: 1024, height: 1024, steps: 4, guidance: 3.5, seed: -1,",
        "  }),",
        "}).then(r => r.json());",
        "",
        "// 2. Poll once per second until done",
        "let job = start.job;",
        "while (job.state !== 'done' && job.state !== 'error') {",
        "  await new Promise(r => setTimeout(r, 1000));",
        "  job = (await fetch(SERVER + '/api/generate/jobs/' + job.id).then(r => r.json())).job;",
        "}",
        "if (job.state === 'error') throw new Error(job.error);",
        "",
        "// 3. job.output_url is a relative path — fetch and use as a Blob",
        "const blob = await fetch(SERVER + job.output_url).then(r => r.blob());",
        "const url  = URL.createObjectURL(blob);   // use in <img src> or <a download>",
      ];
      return lines.join("\n");
    },

    get reDownloadExample() {
      const base = this.apiBase;
      const sampleId = this.gen.jobs.find(j => j.state === "done")?.id || "abc123def456";
      return [
        "# Inspect job metadata (params, seed, output_url, duration, state)",
        "curl -s " + base + "/api/generate/jobs/" + sampleId + " | jq",
        "",
        "# Re-download the PNG",
        "curl -s -o image.png " + base + "/api/generate/jobs/" + sampleId + "/image",
        "",
        "# Python equivalent",
        "import requests",
        "r = requests.get(" + JSON.stringify(base + "/api/generate/jobs/" + sampleId) + ").json()",
        "print('seed used:', r['job']['resolved_seed'])",
        "print('prompt:', r['job']['params']['prompt'])",
        "img = requests.get(" + JSON.stringify(base + "/api/generate/jobs/" + sampleId + "/image") + ").content",
        "open('image.png', 'wb').write(img)",
      ].join("\n");
    },

    get listJobsExample() {
      const base = this.apiBase;
      return [
        "# Returns ALL persisted jobs (last 200), latest first",
        "curl -s " + base + "/api/generate/jobs | jq",
        "",
        "# Just the ids + prompts, for quick browsing",
        "curl -s " + base + "/api/generate/jobs | \\",
        "  jq -r '.jobs[] | \"\\(.id)  \\(.state)  \\(.params.prompt // \"(no prompt)\")\"'",
        "",
        "# Find a job by prompt fragment",
        "curl -s " + base + "/api/generate/jobs | \\",
        "  jq '.jobs[] | select(.params.prompt | test(\"sunset\"; \"i\"))'",
      ].join("\n");
    },

    get pythonExample() {
      const base = this.apiBase;
      const repo = this.gen.repo || "AITRADER/FLUX2-klein-4B-mlx-4bit";
      const lines = [
        "import time, requests",
        "",
        "SERVER = " + JSON.stringify(base),
        "",
        "# 1. Kick off generation",
        "r = requests.post(f'{SERVER}/api/generate/txt2img', json={",
        "    'repo': " + JSON.stringify(repo) + ",",
        "    'prompt': 'a sun-drenched cafe in Lisbon at golden hour',",
        "    'width': 1024, 'height': 1024,",
        "    'steps': 4, 'guidance': 3.5, 'seed': -1,",
        "})",
        "r.raise_for_status()",
        "job_id = r.json()['job']['id']",
        "",
        "# 2. Poll until done",
        "while True:",
        "    job = requests.get(f'{SERVER}/api/generate/jobs/{job_id}').json()['job']",
        "    if job['state'] == 'done':",
        "        break",
        "    if job['state'] == 'error':",
        "        raise RuntimeError(job['error'])",
        "    time.sleep(1)",
        "",
        "# 3. Save the PNG",
        "img = requests.get(f'{SERVER}/api/generate/jobs/{job_id}/image').content",
        "with open('out.png', 'wb') as f:",
        "    f.write(img)",
        "print(f\"saved out.png ({len(img)//1024} KB), seed={job['resolved_seed']}, \"",
        "      f\"duration={job['duration_seconds']:.1f}s\")",
      ];
      return lines.join("\n");
    },

    // ──────── fetch helpers ────────
    /** Fetch the host's chip + RAM snapshot. Used once at init — hardware
     *  doesn't change while the app is running, so no need to re-poll. */
    async refreshSystem() {
      try {
        const r = await fetch("/api/system");
        this.system = await r.json();
      } catch {
        // Leave the default {chip:null, ...} — fit chips will render as
        // "unknown" and the "Your Mac" banner won't show. Better than crashing.
      }
    },
    async refreshHealth() {
      try {
        const r = await fetch("/api/health");
        this.health = await r.json();
      } catch {
        this.health = { ok: false };
      }
    },

    async refreshReleaseNotes() {
      try {
        const r = await fetch("/api/release-notes", { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        this.releaseNotesCurrent = data.current_version || this.health.app_version || "unknown";
        this.releaseNotes = Array.isArray(data.releases) ? data.releases : [];
      } catch {
        this.releaseNotes = [];
      }
    },

    async refreshCatalog() {
      try {
        const r = await fetch("/api/catalog");
        const data = await r.json();
        this.families = data.families;
        this.models = data.models;
        this._reconcileSelectedModel();
      } catch {
        /* keep last good state */
      }
    },

    _reconcileSelectedModel() {
      // The <select> visually displays the first option even when gen.repo is
      // empty, but Alpine's x-model only updates on user change events. Without
      // this, submitGenerate() trips its "pick a cached model" guard even
      // though the UI looks like one is selected. So we pick the first
      // mode-compatible cached model on load, and re-pick if the user's choice
      // drops out of cache or stops being compatible with the current mode.
      const compatible = this.modeCompatibleModels;
      const stillValid = compatible.some(m => m.repo === this.gen.repo);
      if (!stillValid) {
        const ready = compatible.find(m => this.isModelReady(m.repo));
        this.gen.repo = ready?.repo || compatible[0]?.repo || (this.cachedModels[0]?.repo || "");
      }
      this.applySelectedModelDefaults();
    },

    selectGenerationModel(repo) {
      this.gen.repo = repo;
      this.applySelectedModelDefaults(true);
    },

    applySelectedModelDefaults(force = false) {
      const m = this.selectedModel;
      if (!m || (!force && this.gen._profileRepo === m.repo)) return;
      const d = m.generation_profile?.defaults || {};
      if (typeof d.steps === "number") this.gen.steps = d.steps;
      if (typeof d.guidance === "number") this.gen.guidance = d.guidance;
      if (typeof d.image_strength === "number") this.gen.imageStrength = d.image_strength;
      this.gen.quantize = null;
      this.gen._profileRepo = m.repo;
      const sizes = m.sizes || [];
      const preferred = sizes.find(s => s.default) || sizes.find(s => s.tier === "balanced") || sizes[0];
      if (preferred && m.supports_custom_dimensions !== false) {
        this.pickAspect({ ratio: preferred.aspect_ratio, width: preferred.width, height: preferred.height });
      }
    },

    setMode(mode) {
      // Mode switch: update the selected model to one compatible with the new
      // mode so the picker isn't stuck on something that can't run.
      this.gen.mode = mode;
      this._reconcileSelectedModel();
      // Sensible defaults per mode
      if (mode === "edit") {
        // Edit usually wants to preserve more of the input than img2img
        if (this.gen.imageStrength < 0.7) this.gen.imageStrength = 0.85;
        // klein-edit is distilled — guidance pinned to 1.0 internally
        if (this.gen.guidance > 1.5) this.gen.guidance = 1.0;
      }
      this.applySelectedModelDefaults(true);
    },

    startJobStream() {
      if (this._streamHandle) this._streamHandle.close();
      const es = new EventSource("/api/downloads/stream");
      es.addEventListener("snapshot", e => {
        try {
          const payload = JSON.parse(e.data);
          this.jobs = payload.jobs || [];
        } catch { /* swallow */ }
      });
      es.onerror = () => {
        // Browser will auto-reconnect; just trace once for debugging.
        // console.debug("SSE disconnected, will reconnect");
      };
      this._streamHandle = es;
    },

    // ──────── download flow ────────
    confirmDownload(model) {
      this.pendingDownload = model;
      this.downloadToken = "";
    },

    async startDownload() {
      if (!this.pendingDownload) return;
      const body = {
        repo: this.pendingDownload.repo,
        token: this.downloadToken || null,
      };
      this.pendingDownload = null;
      try {
        await fetch("/api/downloads", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body),
        });
        await this.refreshCatalog();
      } catch (e) {
        alert("Failed to start download: " + e);
      }
    },

    async cancelDownload(jobId) {
      try {
        await fetch("/api/downloads/" + encodeURIComponent(jobId), { method: "DELETE" });
      } catch { /* surfaced via stream on next tick */ }
    },

    // ──────── settings ────────
    async refreshSettings() {
      try {
        const r = await fetch("/api/settings");
        const data = await r.json();
        this.settings.hf_token_set = !!data.hf_token_set;
        this.settings.hf_token_masked = data.hf_token_masked || "";
        // Cloud provider key statuses (masked; never the raw values).
        for (const k of ["cloudflare_account_id", "cloudflare_api_token", "together_api_key", "gemini_api_key", "nebius_api_key"]) {
          this.cloudKeys[k + "_set"] = !!data[k + "_set"];
          this.cloudKeys[k + "_masked"] = data[k + "_masked"] || "";
        }
      } catch { /* keep last */ }
      // Connectivity panel is on the same tab — refresh it at the same time.
      await this.refreshConnectivity();
    },

    async refreshMemoryPolicy(silent=false, forceDraft=false) {
      try {
        const r = await fetch("/api/memory-policy", {cache:"no-store"});
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        this.applyMemoryPolicy(data, forceDraft);
      } catch (e) {
        if (!silent) {
          this.memoryPolicy.message = String(e.message || e);
          this.memoryPolicy.messageKind = "error";
        }
      }
    },
    applyMemoryPolicy(data, forceDraft=false) {
      const keepDraft = this.memoryPolicy.dirty && !forceDraft;
      const draft = this.memoryPolicy.draftMode;
      Object.assign(this.memoryPolicy, data, {loaded:true});
      this.memoryPolicy.draftMode = keepDraft ? draft : data.mode;
      if (!keepDraft) this.memoryPolicy.dirty = false;
    },
    markMemoryPolicyDirty() {
      this.memoryPolicy.dirty = this.memoryPolicy.draftMode !== this.memoryPolicy.mode;
      this.memoryPolicy.message = "";
      this.memoryPolicy.messageKind = "info";
    },
    memoryPolicyTime(value) {
      if (!value) return "Not yet";
      const date = new Date(Number(value) * 1000);
      return Number.isNaN(date.getTime()) ? "Not yet" : date.toLocaleString();
    },
    async saveMemoryPolicy() {
      this.memoryPolicy.busy = true;
      this.memoryPolicy.message = "Saving memory mode…";
      this.memoryPolicy.messageKind = "info";
      try {
        const r = await fetch("/api/memory-policy", {
          method:"PUT", headers:{"content-type":"application/json"},
          body:JSON.stringify({mode:this.memoryPolicy.draftMode}),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        this.applyMemoryPolicy(data, true);
        this.memoryPolicy.message = data.mode === "performance"
          ? "Performance mode saved. Models stay warm for the fastest next generation."
          : "Memory mode saved. Automatic release will wait for generation to be idle.";
        this.memoryPolicy.messageKind = "success";
      } catch (e) {
        this.memoryPolicy.message = String(e.message || e);
        this.memoryPolicy.messageKind = "error";
      } finally {
        this.memoryPolicy.busy = false;
      }
    },
    async releaseMemoryNow() {
      this.memoryPolicy.busy = true;
      this.memoryPolicy.message = "Releasing model and accelerator memory…";
      this.memoryPolicy.messageKind = "info";
      try {
        const r = await fetch("/api/memory/release", {method:"POST"});
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        this.applyMemoryPolicy(data);
        this.memoryPolicy.message = "Memory released. The next local generation may take longer while its model reloads.";
        this.memoryPolicy.messageKind = "success";
      } catch (e) {
        this.memoryPolicy.message = String(e.message || e);
        this.memoryPolicy.messageKind = "error";
      } finally {
        this.memoryPolicy.busy = false;
      }
    },

    async refreshAutoUpdate(silent=false) {
      try {
        const r = await fetch("/api/auto-update/status", {cache:"no-store"});
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        this.applyAutoUpdateStatus(data);
      } catch (e) {
        if (!silent) { this.autoUpdate.message=String(e.message||e); this.autoUpdate.messageKind="error"; }
      }
    },
    applyAutoUpdateStatus(data, forceDraft=false) {
      const savedSettings = data.settings ? {...data.settings} : null;
      Object.assign(this.autoUpdate, data, {loaded:true});
      // Status refreshes every five seconds while Settings is open. Keep an
      // in-progress form draft intact instead of replacing it with the last
      // saved server settings (the old behavior made controls snap back).
      if (savedSettings && (forceDraft || !this.autoUpdate.dirty)) {
        this.autoUpdate.draft = savedSettings;
        this.autoUpdate.dirty = false;
      }
    },
    markAutoUpdateDirty() {
      this.autoUpdate.dirty = true;
      this.autoUpdate.message = "";
      this.autoUpdate.messageKind = "info";
    },
    autoUpdateTime(value) {
      if (!value) return "Not yet";
      const date=new Date(value); return Number.isNaN(date.getTime()) ? "Not yet" : date.toLocaleString();
    },
    async saveAutoUpdate() {
      this.autoUpdate.busy=true; this.autoUpdate.message="Saving and validating the schedule…"; this.autoUpdate.messageKind="info";
      try {
        const r=await fetch("/api/auto-update/settings",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(this.autoUpdate.draft)});
        const data=await r.json(); if(!r.ok) throw new Error(data.detail||`HTTP ${r.status}`);
        this.applyAutoUpdateStatus(data, true);
        this.autoUpdate.message=data.settings.mode==="off"?"Saved. Automatic updates are off and the schedule is unloaded.":"Saved. The updater schedule is installed and verified.";
        this.autoUpdate.messageKind="success";
      } catch(e) { this.autoUpdate.message=String(e.message||e); this.autoUpdate.messageKind="error"; }
      finally { this.autoUpdate.busy=false; }
    },
    async autoUpdateAction(action,body={}) {
      this.autoUpdate.busy=true; this.autoUpdate.message=action==="check"?"Checking safely…":"Starting the update helper…"; this.autoUpdate.messageKind="info";
      try {
        const r=await fetch(`/api/auto-update/${action}`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});
        const data=await r.json(); if(!r.ok) throw new Error(data.detail||`HTTP ${r.status}`);
        this.applyAutoUpdateStatus(data);
        this.autoUpdate.message=body.after_current?"Queued. The updater will retry when Image Studio is idle.":(action==="check"?"Check started. Status refreshes automatically.":"Update started. This page may reconnect during restart.");
        this.autoUpdate.messageKind="success";
      } catch(e) { this.autoUpdate.message=String(e.message||e); this.autoUpdate.messageKind="error"; }
      finally { this.autoUpdate.busy=false; }
    },

    async saveCloudKeys() {
      const body = {};
      const cf = (this.cloudKeys.cfAccount || "").trim();
      const cft = (this.cloudKeys.cfToken || "").trim();
      const tg = (this.cloudKeys.together || "").trim();
      const gm = (this.cloudKeys.gemini || "").trim();
      const nb = (this.cloudKeys.nebius || "").trim();
      if (cf)  body.cloudflare_account_id = cf;
      if (cft) body.cloudflare_api_token = cft;
      if (tg)  body.together_api_key = tg;
      if (gm)  body.gemini_api_key = gm;
      if (nb)  body.nebius_api_key = nb;
      if (Object.keys(body).length === 0) {
        this.cloudKeys.message = "Enter at least one key to save.";
        this.cloudKeys.messageKind = "error";
        return;
      }
      this.cloudKeys.busy = true;
      this.cloudKeys.message = "";
      try {
        const r = await fetch("/api/settings", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
        for (const k of ["cloudflare_account_id", "cloudflare_api_token", "together_api_key", "gemini_api_key", "nebius_api_key"]) {
          this.cloudKeys[k + "_set"] = !!data[k + "_set"];
          this.cloudKeys[k + "_masked"] = data[k + "_masked"] || "";
        }
        this.cloudKeys.cfAccount = ""; this.cloudKeys.cfToken = ""; this.cloudKeys.together = "";
        this.cloudKeys.gemini = ""; this.cloudKeys.nebius = "";
        this.cloudKeys.showCfToken = false; this.cloudKeys.showTogether = false;
        this.cloudKeys.showGemini = false; this.cloudKeys.showNebius = false;
        this.cloudKeys.message = "Saved. Cloud models using these providers can now generate.";
        this.cloudKeys.messageKind = "success";
        this.pushToast({ kind: "success", icon: "✓", title: "Cloud keys saved", body: "" });
      } catch (e) {
        this.cloudKeys.message = String(e.message || e);
        this.cloudKeys.messageKind = "error";
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't save cloud keys",
          body: this.cloudKeys.message });
      } finally {
        this.cloudKeys.busy = false;
      }
    },

    async clearCloudKeys() {
      this.cloudKeys.busy = true;
      this.cloudKeys.message = "";
      try {
        const r = await fetch("/api/settings", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ cloudflare_account_id: "", cloudflare_api_token: "", together_api_key: "", gemini_api_key: "", nebius_api_key: "" }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
        for (const k of ["cloudflare_account_id", "cloudflare_api_token", "together_api_key", "gemini_api_key", "nebius_api_key"]) {
          this.cloudKeys[k + "_set"] = !!data[k + "_set"];
          this.cloudKeys[k + "_masked"] = data[k + "_masked"] || "";
        }
        this.cloudKeys.message = "Cleared all cloud provider keys.";
        this.cloudKeys.messageKind = "info";
      } catch (e) {
        this.cloudKeys.message = String(e.message || e);
        this.cloudKeys.messageKind = "error";
      } finally {
        this.cloudKeys.busy = false;
      }
    },

    async refreshConnectivity() {
      try {
        const r = await fetch("/api/connectivity");
        const data = await r.json();
        Object.assign(this.conn, data);
      } catch { /* keep last */ }
    },

    async saveSettings() {
      const token = (this.settings.tokenInput || "").trim();
      if (!token) {
        this.settings.message = "Paste a token first (it should start with hf_…).";
        this.settings.messageKind = "error";
        return;
      }
      this.settings.busy = true;
      this.settings.message = "";
      try {
        const r = await fetch("/api/settings", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ hf_token: token }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
        this.settings.hf_token_set = !!data.hf_token_set;
        this.settings.hf_token_masked = data.hf_token_masked || "";
        this.settings.tokenInput = "";       // clear the input after save
        this.settings.showToken = false;
        this.settings.message = `Saved. Future downloads will use this token automatically.`;
        this.settings.messageKind = "success";
        this.pushToast({ kind: "success", icon: "✓", title: "HF token saved",
          body: this.settings.hf_token_masked });
      } catch (e) {
        this.settings.message = String(e.message || e);
        this.settings.messageKind = "error";
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't save token",
          body: this.settings.message });
      } finally {
        this.settings.busy = false;
      }
    },

    async testToken() {
      // Test the input field if non-empty; otherwise test the saved token.
      const candidate = (this.settings.tokenInput || "").trim();
      this.settings.busy = true;
      this.settings.message = "Testing…";
      this.settings.messageKind = "info";
      try {
        const r = await fetch("/api/settings/test-hf-token", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(candidate ? { hf_token: candidate } : {}),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || ("HTTP " + r.status));
        const who = data.name || "your account";
        this.settings.message = `✓ Valid. Logged in as ${who}${data.type ? " (" + data.type + ")" : ""}.`;
        this.settings.messageKind = "success";
        this.pushToast({ kind: "success", icon: "✓", title: "Token valid",
          body: `Hi ${who}` });
      } catch (e) {
        this.settings.message = `✗ ${e.message || e}`;
        this.settings.messageKind = "error";
        this.pushToast({ kind: "error", icon: "✗", title: "Token invalid",
          body: this.settings.message });
      } finally {
        this.settings.busy = false;
      }
    },

    async clearToken() {
      if (!await this.askConfirm("Remove saved token?", "Downloads will fall back to anonymous mode — lower rate limits and no gated repos.", "Remove token")) return;
      this.settings.busy = true;
      this.settings.message = "";
      try {
        const r = await fetch("/api/settings", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ hf_token: "" }),
        });
        const data = await r.json();
        this.settings.hf_token_set = !!data.hf_token_set;
        this.settings.hf_token_masked = data.hf_token_masked || "";
        this.settings.message = "Token cleared.";
        this.settings.messageKind = "info";
        this.pushToast({ kind: "info", icon: "🧹", title: "HF token cleared" });
      } catch (e) {
        this.settings.message = String(e.message || e);
        this.settings.messageKind = "error";
      } finally {
        this.settings.busy = false;
      }
    },

    async clearFinishedDownloads() {
      try {
        const r = await fetch("/api/downloads", { method: "DELETE" });
        const data = await r.json().catch(() => ({}));
        // Stream will refresh the list on next tick; do an optimistic prune too
        // so the UI feels snappy.
        this.jobs = this.jobs.filter(j => !["done", "error", "cancelled"].includes(j.state));
        this.pushToast({ kind: "info", icon: "🧹", title: `Cleared ${data.cleared ?? 0} finished` });
      } catch (e) {
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't clear downloads", body: String(e) });
      }
    },

    // ──────── imports flow ────────
    async scanImports() {
      try {
        const r = await fetch("/api/imports/scan");
        const data = await r.json();
        this.candidates = data.candidates || [];
      } catch { /* keep last */ }
    },

    async submitImport(mode = "link") {
      this.importMessage = "";
      this.importResult = null;
      if (mode === "move") {
        const sp = this.importForm.source_path || "(empty)";
        if (!await this.askConfirm(
          "Move into HF cache?",
          `${sp}\n\nThis physically relocates the folder — the source path will be gone afterwards.`,
          "Move"
        )) {
          return;
        }
      }
      try {
        const r = await fetch("/api/imports", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ ...this.importForm, mode }),
        });
        const data = await r.json();
        if (!r.ok) {
          this.importMessage = data.detail || "Import failed.";
          this.importMessageKind = "error";
          this.pushToast({ kind: "error", icon: "✗", title: "Import failed",
            body: data.detail || "(see network tab)" });
          return;
        }
        const verb = data.mode === "move" ? "Moved" : "Linked";
        this.importMessage = `${verb} ${data.repo}`;
        this.importMessageKind = "success";
        this.importResult = data;
        this.pushToast({
          kind: "success", icon: "✓",
          title: `${verb} ${data.repo}`,
          body: `→ ${data.target}`,
        });
        this.importForm = { source_path: "", repo: "" };
        await this.refreshCatalog();
      } catch (e) {
        this.importMessage = String(e);
        this.importMessageKind = "error";
        this.pushToast({ kind: "error", icon: "✗", title: "Import failed", body: String(e) });
      }
    },

    async linkCandidate(c) {
      this.importForm.source_path = c.source_path;
      this.importForm.repo = c.repo;
      await this.submitImport("link");
      await this.scanImports();
    },

    async moveCandidate(c) {
      this.importForm.source_path = c.source_path;
      this.importForm.repo = c.repo;
      await this.submitImport("move");
      await this.scanImports();
    },

    // ──────── generate flow ────────
    async refreshDiagnostics() {
      try {
        const r = await fetch("/api/generate/diagnostics");
        if (!r.ok) return;
        const data = await r.json();
        this.diag.device = data.device || null;
        this.diag.packages = data.packages || [];
        this.diag.engines = data.engines || [];
        this.diag.any_missing = !!data.any_missing;
        this.diag.ready_count = data.ready_count || 0;
        this.diag.total_engines = data.total_engines || 0;
        this.diag._lastFetched = Date.now();
      } catch { /* keep last */ }
    },

    async refreshGenerationInstall() {
      try {
        const r = await fetch("/api/generate/install/status");
        if (!r.ok) return;
        const data = await r.json();
        this.generationInstall = { ...this.generationInstall, ...data, busy: data.state === "installing" || data.state === "restarting" };
        if (this.generationInstall.busy) {
          setTimeout(() => this.refreshGenerationInstall(), 1500);
        } else if (data.state === "done") {
          await this.refreshGenAvailability();
          await this.refreshDiagnostics();
        }
      } catch {
        if (this.generationInstall.busy) setTimeout(() => this.refreshGenerationInstall(), 2000);
      }
    },

    async installGeneration() {
      if (this.generationInstall.busy) return;
      this.generationInstall.busy = true;
      this.generationInstall.state = "installing";
      this.generationInstall.message = "Starting the generation engine installer...";
      try {
        const r = await fetch("/api/generate/install", { method: "POST" });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        this.generationInstall = { ...this.generationInstall, ...data, busy: true };
        setTimeout(() => this.refreshGenerationInstall(), 1000);
      } catch (e) {
        this.generationInstall.state = "error";
        this.generationInstall.message = String(e.message || e);
        this.generationInstall.busy = false;
      }
    },

    async refreshGenAvailability() {
      try {
        const r = await fetch("/api/generate/availability");
        const data = await r.json();
        this.gen.available = !!data.available;
        this.gen.error = data.error;
        this.gen.presets = data.presets || [];
        if (this.gen.presets.length && !this.gen.presets.find(p => p.ratio === this.gen.aspect)) {
          this.pickAspect(this.gen.presets[0]);
        } else if (this.gen.presets.length) {
          const cur = this.gen.presets.find(p => p.ratio === this.gen.aspect);
          if (cur) { this.gen.width = cur.width; this.gen.height = cur.height; }
        }
      } catch {
        this.gen.available = false;
      }
    },

    async refreshLoras() {
      try {
        const r = await fetch("/api/loras");
        const data = await r.json();
        this.loras = data.loras || [];
      } catch { /* keep last */ }
    },

    startGenStream() {
      if (this._genStreamHandle) this._genStreamHandle.close();
      const es = new EventSource("/api/generate/stream");
      es.addEventListener("snapshot", e => {
        try {
          const payload = JSON.parse(e.data);
          const incoming = (payload.jobs || []).slice().sort((a, b) => (b.started_at || 0) - (a.started_at || 0));

          // Detect state transitions running/queued → done/error/cancelled, fire a toast.
          for (const j of incoming) {
            const prev = this._jobStatePrev[j.id];
            const terminal = ["done", "error", "cancelled"];
            if (prev && prev !== j.state && terminal.includes(j.state) && !terminal.includes(prev)) {
              this._notifyJobFinished(j);
            }
            this._jobStatePrev[j.id] = j.state;
          }

          this.gen.jobs = incoming;
          // Keep the currentJob reference fresh so progress updates flow.
          if (this.gen.currentJob) {
            const updated = this.gen.jobs.find(j => j.id === this.gen.currentJob.id);
            if (updated) this.gen.currentJob = updated;
          }
          // If we have no current job but there's a running/done one, surface it.
          if (!this.gen.currentJob && this.gen.jobs.length) {
            this.gen.currentJob = this.gen.jobs[0];
          }
          // Manage the busy flag.
          const running = this.gen.jobs.find(j => j.state === "running" || j.state === "queued");
          this.gen.busy = !!running;
          if (running) {
            // Use the real fields the job actually has: `progress` (0..1) and
            // `started_at`. The old label read current_step/total_steps, which
            // aren't updated during a run → "Generating… undefined/undefined".
            const pct = Math.round((running.progress || 0) * 100);
            const elapsed = running.started_at
              ? Math.max(0, Math.floor(Date.now() / 1000) - Math.floor(running.started_at)) : 0;
            this.gen.busyLabel = "Generating…"
              + (pct > 0 ? ` ${pct}%` : "")
              + (elapsed ? ` · ${elapsed}s` : "");
          }
        } catch { /* swallow */ }
      });
      es.onerror = () => { /* auto-reconnects */ };
      this._genStreamHandle = es;
    },

    _notifyJobFinished(job) {
      if (job.state === "done") {
        this.pushToast({
          kind: "success",
          icon: "✓",
          title: "Generation done",
          body: this.formatDuration(job.duration_seconds) + (job.params?.prompt ? ` · "${job.params.prompt.slice(0, 50)}"` : ""),
        });
        this._tryNativeNotification("ImageStudio · done", job.params?.prompt?.slice(0, 80) || "");
        this._flashTabTitle("✓ Done");
        this.refreshOutputStats();               // a new image landed — refresh the disk figure
      } else if (job.state === "error") {
        this.pushToast({
          kind: "error",
          icon: "✗",
          title: "Generation error",
          body: job.error || "(see server terminal)",
        });
        this._tryNativeNotification("ImageStudio · error", job.error || "");
        this._flashTabTitle("✗ Error");
      } else if (job.state === "cancelled") {
        this.pushToast({ kind: "warn", icon: "⏹", title: "Generation cancelled" });
      }
    },

    pickAspect(p) {
      this.gen.aspect = p.ratio;
      this.gen.width = p.width;
      this.gen.height = p.height;
    },

    aspectShape(p) {
      // Build a small rectangle whose proportions reflect the aspect ratio,
      // capped to a tile-sized box so the grid stays orderly.
      const max = 28;
      const ratio = p.width / p.height;
      const w = ratio >= 1 ? max : Math.round(max * ratio);
      const h = ratio >= 1 ? Math.round(max / ratio) : max;
      return `width:${w}px;height:${h}px;`;
    },

    magicPrompt() {
      // Lightweight no-LLM enhancer: appends quality + style tags if not present.
      const tags = "masterpiece, best quality, highly detailed, sharp focus, cinematic lighting";
      const existing = this.gen.prompt.trim();
      if (!existing) return;
      if (existing.toLowerCase().includes("masterpiece")) return;
      this.gen.prompt = existing + (existing.endsWith(",") ? " " : ", ") + tags;
    },

    randomPrompt() {
      const pool = window.SAMPLE_PROMPTS || [];
      if (pool.length === 0) {
        alert("No sample prompts loaded.");
        return;
      }
      // Pick uniformly at random, but never the same as the previous pick.
      let idx;
      if (pool.length === 1) {
        idx = 0;
      } else {
        do { idx = Math.floor(Math.random() * pool.length); }
        while (idx === this._lastRandomPromptIndex);
      }
      this._lastRandomPromptIndex = idx;
      this.gen.prompt = pool[idx];
    },

    toggleLora(name, on) {
      if (on) {
        if (!this.gen.loraNames.includes(name)) this.gen.loraNames.push(name);
        if (this.gen.loraWeights[name] === undefined) this.gen.loraWeights[name] = 1.0;
      } else {
        this.gen.loraNames = this.gen.loraNames.filter(n => n !== name);
        delete this.gen.loraWeights[name];
      }
    },

    // ──────── input image helpers (img2img) ────────
    setInputImage(blobOrFile, name) {
      // Clear any previous object URL so we don't leak memory.
      if (this.gen.inputImageUrl) {
        try { URL.revokeObjectURL(this.gen.inputImageUrl); } catch {}
      }
      this.gen.inputImageFile = blobOrFile;
      this.gen.inputImageUrl = URL.createObjectURL(blobOrFile);
      this.gen.inputImageName = name || blobOrFile.name || "image";
      // If we're not already in img2img mode, switch — the user clearly wants it.
      if (this.gen.mode !== "img2img") this.gen.mode = "img2img";
    },

    clearInputImage() {
      if (this.gen.inputImageUrl) {
        try { URL.revokeObjectURL(this.gen.inputImageUrl); } catch {}
      }
      this.gen.inputImageFile = null;
      this.gen.inputImageUrl = "";
      this.gen.inputImageName = "";
    },

    handleImageDrop(e) {
      const file = e.dataTransfer?.files?.[0];
      if (file && file.type.startsWith("image/")) {
        this.setInputImage(file, file.name);
      } else {
        this.pushToast({ kind: "warn", icon: "⚠", title: "Not an image",
          body: "Drop a PNG, JPG, or WEBP file." });
      }
    },

    handleImageFileInput(e) {
      const file = e.target.files?.[0];
      if (file) this.setInputImage(file, file.name);
      e.target.value = "";   // reset so picking the same file twice fires change
    },

    async submitGenerate() {
      if (!this.selectedModel?.is_cloud && !this.gen.available) {
        this.pushToast({ kind: "warn", icon: "⚠", title: "Engine not installed",
          body: "Use Install engines in the readiness card." });
        return;
      }
      if (!this.selectedModel) {
        this.pushToast({ kind: "warn", icon: "⚠", title: "Pick a cached model first",
          body: "Open the Models tab and download one." });
        return;
      }
      if (this.supportsControl("prompt") && !this.gen.prompt.trim()) return;
      if ((this.gen.mode === "img2img" || this.gen.mode === "edit") && !this.gen.inputImageFile) {
        this.pushToast({ kind: "warn", icon: "⚠", title: "Input image required",
          body: this.gen.mode === "edit"
            ? "Drop, paste, or pick an image to edit."
            : "Drop, paste, or pick an image for img2img." });
        return;
      }

      const count = Math.max(1, Math.min(8, this.gen.batchCount | 0));
      const baseSeed = this.gen.seed;
      const usingRandomSeed = baseSeed == null || baseSeed < 0;

      this._requestNotificationPermission();
      // Transient lock to prevent double-click while the POST is in flight.
      // Cleared on a 300ms tail so the user can immediately submit again
      // (which queues the next job; backend _GEN_LOCK serializes execution).
      this.gen.submitting = true;

      let lastJob = null;
      for (let i = 0; i < count; i++) {
        const seedForThis = usingRandomSeed ? -1 : (baseSeed + i);
        try {
          let r;
          if (this.gen.mode === "img2img" || this.gen.mode === "edit") {
            // Multipart form-data: file + flat scalar fields. Edit and img2img
            // use the same shape; backend routes to the right pipeline.
            const fd = new FormData();
            fd.append("image", this.gen.inputImageFile, this.gen.inputImageName || "input.png");
            fd.append("repo", this.gen.repo);
            fd.append("prompt", this.gen.prompt.trim());
            // Edit endpoint doesn't accept negative_prompt; only send for img2img
            if (this.gen.mode === "img2img") {
              fd.append("negative_prompt", this.gen.negativePrompt.trim());
            }
            fd.append("width", String(this.gen.width));
            fd.append("height", String(this.gen.height));
            fd.append("steps", String(this.gen.steps));
            fd.append("guidance", String(this.gen.guidance));
            fd.append("seed", String(seedForThis));
            fd.append("image_strength", String(this.gen.imageStrength));
            if (this.canRuntimeQuant && this.gen.quantize != null) {
              fd.append("quantize", String(this.gen.quantize));
            }
            fd.append("lora_names", this.gen.loraNames.join(","));
            fd.append("lora_scales", this.gen.loraNames.map(n => this.gen.loraWeights[n] ?? 1.0).join(","));
            const endpoint = this.gen.mode === "edit"
              ? "/api/generate/edit"
              : "/api/generate/img2img";
            r = await fetch(endpoint, { method: "POST", body: fd });
          } else {
            const body = {
              repo: this.gen.repo,
              prompt: this.gen.prompt.trim(),
              negative_prompt: this.gen.negativePrompt.trim(),
              width: this.gen.width,
              height: this.gen.height,
              steps: this.gen.steps,
              guidance: this.gen.guidance,
              seed: seedForThis,
              quantize: this.canRuntimeQuant ? this.gen.quantize : null,
              lora_names: this.gen.loraNames,
              lora_scales: this.gen.loraNames.map(n => this.gen.loraWeights[n] ?? 1.0),
            };
            r = await fetch("/api/generate/txt2img", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify(body),
            });
          }
          if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            this.pushToast({ kind: "error", icon: "✗", title: "Submit failed",
              body: err.detail || ("HTTP " + r.status) });
            break;
          }
          const { job } = await r.json();
          lastJob = job;
        } catch (e) {
          this.pushToast({ kind: "error", icon: "✗", title: "Submit failed",
            body: String(e) });
          break;
        }
      }
      if (lastJob) {
        this.gen.currentJob = lastJob;
        this.gen.busy = true;
        if (count > 1) {
          this.pushToast({ kind: "info", icon: "▶", title: `Queued ${count} images`,
            body: "They'll generate one after another. Cancel any from the queue panel." });
        }
      }
      // Tail timer so the user can submit again immediately. The SSE stream
      // handles busy-state updates as jobs progress; this flag is purely for
      // double-click protection.
      setTimeout(() => { this.gen.submitting = false; }, 300);
    },

    async cancelGenerate(jobId) {
      try {
        await fetch("/api/generate/jobs/" + encodeURIComponent(jobId), { method: "DELETE" });
      } catch { /* surfaces via stream */ }
    },

    async clearHistory() {
      // Two-click confirm instead of native confirm() — Pinokio's embedded webview
      // can silently block window.confirm() (it returns false), making this button
      // appear to do nothing. First click arms; a second click within 3s clears.
      if (!this.gen.clearArmed) {
        this.gen.clearArmed = true;
        clearTimeout(this._clearArmTimer);
        this._clearArmTimer = setTimeout(() => { this.gen.clearArmed = false; }, 3000);
        return;
      }
      clearTimeout(this._clearArmTimer);
      this.gen.clearArmed = false;
      try {
        const r = await fetch("/api/generate/jobs", { method: "DELETE" });
        if (!r.ok) throw new Error("HTTP " + r.status);
        this.gen.currentJob = null;
        this.gen.jobs = (this.gen.jobs || []).filter(j => ["queued", "running", "cancelling"].includes(j.state));
        this._jobStatePrev = {};
        this.pushToast({ kind: "info", icon: "🧹", title: "History cleared", body: "The images stay in your outputs folder." });
      } catch (e) {
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't clear history", body: String(e) });
      }
    },

    /** Open the outputs folder (where every generated file lands) in Finder.
     *  Derived from any output's absolute path — needs no extra endpoint. */
    openOutputsFolder() {
      const withPath = (this.gen.jobs || []).find(j => j.output_path);
      if (withPath && withPath.output_path) {
        this.revealInFolder(withPath.output_path.replace(/[/\\][^/\\]+$/, ""));
      } else {
        this.pushToast({ kind: "info", icon: "📂", title: "No generations yet",
          body: "Generate something first — then this opens the folder with all your images." });
      }
    },

    /** Delete one finished generation (removes it from history AND deletes the
     *  image). Two-click confirm — first click arms this tile, second deletes. */
    deleteGeneration(job) {
      if (this.gen.deleteArmed !== job.id) {
        this.gen.deleteArmed = job.id;
        clearTimeout(this._deleteArmTimer);
        this._deleteArmTimer = setTimeout(() => { this.gen.deleteArmed = null; }, 3000);
        return;
      }
      clearTimeout(this._deleteArmTimer);
      this.gen.deleteArmed = null;
      this._doDeleteGeneration(job);
    },
    async _doDeleteGeneration(job) {
      try {
        const r = await fetch("/api/generate/history/" + encodeURIComponent(job.id), { method: "DELETE" });
        if (!r.ok) throw new Error("HTTP " + r.status);
        this.gen.jobs = (this.gen.jobs || []).filter(j => j.id !== job.id);
        if (this.gen.currentJob && this.gen.currentJob.id === job.id) {
          this.gen.currentJob = this.newestJob || (this.gen.jobs || [])[0] || null;
        }
        this.refreshOutputStats();
        this.pushToast({ kind: "info", icon: "🗑", title: "Generation deleted" });
      } catch (e) {
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't delete",
          body: "This needs the latest backend — run Update once from the Pinokio sidebar." });
      }
    },

    // ──────── outputs folder disk usage ────────
    outputStats: { bytes: 0, count: 0, loaded: false },
    storagePolicy: {
      enabled: true, retention_days: 3, max_gb: 80, used_bytes: 0,
      over_limit: false, loaded: false, busy: false, message: "",
    },
    async refreshOutputStats() {
      try {
        const r = await fetch("/api/output/stats");
        if (!r.ok) return;                         // endpoint not live until next Update
        const d = await r.json();
        this.outputStats = { bytes: d.bytes || 0, count: d.count || 0, loaded: true };
      } catch { /* keep last */ }
    },
    async refreshStoragePolicy() {
      try {
        const r = await fetch("/api/storage-policy");
        if (!r.ok) return;
        const d = await r.json();
        this.storagePolicy = { ...this.storagePolicy, ...d, loaded: true, busy: false };
      } catch { /* keep last */ }
    },
    async saveStoragePolicy() {
      this.storagePolicy.busy = true;
      this.storagePolicy.message = "Saving policy…";
      try {
        const r = await fetch("/api/storage-policy", {
          method: "PUT", headers: { "content-type": "application/json" },
          body: JSON.stringify({
            enabled: !!this.storagePolicy.enabled,
            retention_days: Number(this.storagePolicy.retention_days),
            max_gb: Number(this.storagePolicy.max_gb),
          }),
        });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        const d = await r.json();
        this.storagePolicy = { ...this.storagePolicy, ...d, loaded: true, busy: false,
          message: "Saved. This Mac will enforce the policy automatically." };
        this.pushToast({ kind: "info", icon: "✓", title: "Storage policy saved",
          body: `${d.retention_days} days · ${d.max_gb} GB hard cap` });
      } catch (e) {
        this.storagePolicy.busy = false;
        this.storagePolicy.message = String(e);
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't save storage policy", body: String(e) });
      }
    },
    async cleanStoragePolicyNow() {
      this.storagePolicy.busy = true;
      this.storagePolicy.message = "Checking completed outputs…";
      try {
        const r = await fetch("/api/storage-policy/cleanup", {
          method: "POST", headers: { "content-type": "application/json" }, body: "{}",
        });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        const d = await r.json();
        this.storagePolicy = { ...this.storagePolicy, ...d, loaded: true, busy: false,
          message: `Cleanup complete · ${d.deleted || 0} removed · ${humanBytes(d.freed_bytes || 0)} freed.` };
        await this.refreshOutputStats();
        this.pushToast({ kind: "info", icon: "🧹", title: "Cleanup complete",
          body: `${d.deleted || 0} image${d.deleted === 1 ? "" : "s"} removed · ${humanBytes(d.freed_bytes || 0)} freed` });
      } catch (e) {
        this.storagePolicy.busy = false;
        this.storagePolicy.message = String(e);
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't clean outputs", body: String(e) });
      }
    },
    /** mode: "keep50" keeps the newest 50; "old30" deletes files older than 30 days. */
    async pruneOutputs(mode) {
      const body = mode === "old30" ? { older_than_days: 30 } : { keep_last: 50 };
      const label = mode === "old30" ? "older than 30 days" : "all but the newest 50";
      if (this.gen.pruneArmed !== mode) {
        this.gen.pruneArmed = mode;
        clearTimeout(this._pruneArmTimer);
        this._pruneArmTimer = setTimeout(() => { this.gen.pruneArmed = null; }, 3000);
        return;
      }
      clearTimeout(this._pruneArmTimer);
      this.gen.pruneArmed = null;
      try {
        const r = await fetch("/api/output/prune", {
          method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error("HTTP " + r.status);
        const d = await r.json();
        await this.refreshOutputStats();
        this.pushToast({ kind: "info", icon: "🧹", title: "Outputs pruned",
          body: `Deleted ${d.deleted} image${d.deleted === 1 ? "" : "s"} (${humanBytes(d.freed_bytes || 0)}) — kept ${label === "older than 30 days" ? "recent" : "the newest 50"}.` });
      } catch (e) {
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't prune",
          body: "This needs the latest backend — run Update once from the Pinokio sidebar." });
      }
    },

    // ──────── in-app confirm (webview-safe) ────────
    // Native window.confirm() is silently blocked by Pinokio's embedded webview
    // (returns false), so destructive actions using it appeared to do nothing.
    // askConfirm() opens an in-app modal and resolves true/false when the user
    // chooses. Usage: `if (!await this.askConfirm("Title", "body")) return;`
    askConfirm(title, body, confirmLabel = "Confirm") {
      return new Promise((resolve) => {
        this.confirmDialog = { title, body, confirmLabel, resolve };
      });
    },
    _resolveConfirm(value) {
      if (this.confirmDialog) {
        const r = this.confirmDialog.resolve;
        this.confirmDialog = null;
        r(value);
      }
    },

    // ──────── toasts / native notification / tab title ────────

    pushToast(t) {
      const id = ++this._toastSeq;
      this.toasts.push({ id, ...t });
      const ttl = t.kind === "error" ? 8000 : 4500;
      setTimeout(() => this.dismissToast(id), ttl);
    },

    dismissToast(id) {
      this.toasts = this.toasts.filter(t => t.id !== id);
    },

    _requestNotificationPermission() {
      // Only ask once per session. User must accept once; thereafter it's
      // remembered by the browser. Failing silently is fine.
      if (typeof Notification === "undefined") return;
      if (Notification.permission === "default") {
        try { Notification.requestPermission(); } catch { /* ignore */ }
      }
    },

    _tryNativeNotification(title, body) {
      if (typeof Notification === "undefined") return;
      if (Notification.permission !== "granted") return;
      // Don't pop a notification if the page is currently visible — toasts cover that case.
      if (document.visibilityState === "visible") return;
      try {
        const n = new Notification(title, { body, silent: false });
        setTimeout(() => n.close(), 6000);
      } catch { /* some browsers/contexts restrict this; ignore */ }
    },

    _flashTabTitle(label) {
      // Briefly mutate document.title to grab attention in a background tab,
      // then restore the original after 6s OR on tab focus.
      const original = "ImageStudio (Mac)";
      document.title = `${label} · ${original}`;
      const restore = () => {
        document.title = original;
        document.removeEventListener("visibilitychange", restore);
      };
      document.addEventListener("visibilitychange", restore);
      setTimeout(restore, 6000);
    },

    genStateChipClass(state) {
      if (!state) return "";
      if (state === "done") return "ok";
      if (state === "error") return "bad";
      if (["cancelled", "cancelling"].includes(state)) return "warn";
      return "";
    },

    genProgressLabel() {
      const j = this.gen.currentJob;
      if (!j) return "";
      if (j.total_steps > 0) return `step ${j.current_step} / ${j.total_steps}`;
      return "warming up…";
    },

    elapsedFor(job) {
      // Backend computes duration_seconds when finished; for running jobs we
      // tick locally so the display updates without depending on the SSE cadence.
      if (!job || !job.started_at) return 0;
      if (job.state === "running" || job.state === "queued") {
        return Math.max(0, this._nowSec - job.started_at);
      }
      return job.duration_seconds ?? 0;
    },

    formatDuration(sec) {
      if (sec == null || isNaN(sec)) return "—";
      sec = Math.round(sec);
      if (sec < 60) return `${sec}s`;
      if (sec < 3600) {
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m}m ${s.toString().padStart(2, "0")}s`;
      }
      // Download ETAs on a slow/throttled connection can legitimately reach
      // hour/day scale — "734m 12s" is as unreadable as the settle-guard bug.
      if (sec < 86400) {
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        return `${h}h ${m.toString().padStart(2, "0")}m`;
      }
      const d = Math.floor(sec / 86400);
      const h = Math.floor((sec % 86400) / 3600);
      return `${d}d ${h.toString().padStart(2, "0")}h`;
    },

    downloadFilename(job) {
      if (!job) return "image.png";
      const prompt = (job.params?.prompt || "image")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 40) || "image";
      const seed = job.resolved_seed ?? "seed";
      return `${prompt}-${seed}-${job.id}.png`;
    },

    reuseParams(job) {
      const p = job?.params;
      if (!p) return;
      this.tab = "generate";
      if (p.repo) {
        // Only set if the model is still cached; otherwise reconcile will pick a valid one.
        const stillCached = this.cachedModels.some(m => m.repo === p.repo);
        if (stillCached) this.gen.repo = p.repo;
      }
      this.gen.prompt = p.prompt || "";
      this.gen.negativePrompt = p.negative_prompt || "";
      if (p.width)  this.gen.width  = p.width;
      if (p.height) this.gen.height = p.height;
      // Match an aspect preset if dimensions line up; otherwise leave as custom.
      const match = this.gen.presets.find(pr => pr.width === p.width && pr.height === p.height);
      if (match) this.gen.aspect = match.ratio;
      if (typeof p.steps === "number")     this.gen.steps = p.steps;
      if (typeof p.guidance === "number")  this.gen.guidance = p.guidance;
      // Reuse the resolved seed so it's truly reproducible (unless user clicks Random)
      const reuseSeed = job.resolved_seed ?? p.seed;
      if (typeof reuseSeed === "number") this.gen.seed = reuseSeed;
      if (p.quantize !== undefined)      this.gen.quantize = p.quantize;
      this.gen.loraNames   = [...(p.lora_names || [])];
      this.gen.loraWeights = {};
      (p.lora_names || []).forEach((n, i) => {
        this.gen.loraWeights[n] = p.lora_scales?.[i] ?? 1.0;
      });
    },

    async copyImageUrl(job) {
      if (!job?.output_url) return;
      const full = window.location.origin + job.output_url;
      await this.copyText(full);
    },

    async revealInFolder(path) {
      if (!path) return;
      try {
        const r = await fetch("/api/reveal", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ path }),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          this.pushToast({ kind: "error", icon: "✗", title: "Couldn't open in Finder",
            body: err.detail || ("HTTP " + r.status) });
        }
      } catch (e) {
        this.pushToast({ kind: "error", icon: "✗", title: "Couldn't open in Finder", body: String(e) });
      }
    },

    async copyText(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        // Fallback for non-secure contexts
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); } catch {}
        ta.remove();
      }
    },

    recentTileTitle(j) {
      if (!j) return "";
      const prompt = j.params?.prompt ? `"${j.params.prompt.slice(0, 60)}"` : "(no prompt)";
      const dur = j.duration_seconds != null ? this.formatDuration(j.duration_seconds) : j.state;
      const seed = j.resolved_seed != null ? ` · seed ${j.resolved_seed}` : "";
      return `${prompt} · ${dur}${seed}`;
    },

    // ──────── formatters ────────
    formatGb(gb) {
      // Decimal (×1000) to match humanBytes + HF's GB convention (size_gb is a
      // decimal-GB catalog value, so a sub-1GB model is N×1000 MB, not ×1024).
      if (gb < 1) return Math.round(gb * 1000) + " MB";
      return gb.toFixed(1) + " GB";
    },

    cardClass(m) {
      return m.cache.state;
    },

    cacheChipLabel(state) {
      return { cached: "cached", partial: "partial", absent: "not downloaded" }[state] || state;
    },

    cacheChipClass(state) {
      return { cached: "ok", partial: "warn", absent: "" }[state] || "";
    },

    /** Short label for the hardware-fit chip on a model card. Mirrors the
     *  backend's `fit.state` enum: ok / tight / risky / unknown. */
    fitChipLabel(fit) {
      if (!fit) return "";
      const map = {
        ok:      "✓ fits",
        tight:   "⚠ tight",
        risky:   "✗ may not fit",
        unknown: "? fit unknown",
        needs_key: "🔑 needs key",   // cloud model whose API credential isn't set
        needs_billing: "💳 needs billing",  // cloud model needing a paid account (Gemini)
      };
      return map[fit.state] || "";
    },

    /** Bullet glyph for each use_case kind. Keeps the index.html template
     *  free of inline conditional logic. */
    useCaseIcon(kind) {
      const map = { good: "✅", weak: "⚠️", avoid: "❌" };
      return map[kind] || "•";
    },

    chipExplain(state) {
      return {
        cached:  "All files for this model are on disk and ready to generate from.",
        partial: "Some files have downloaded; the model isn't usable yet. Clicking Download resumes from where it left off.",
        absent:  "No files for this model on disk. Click Download to fetch them.",
      }[state] || "";
    },

    capabilityLabel(c) {
      return {
        txt2img: "text → image",
        img2img: "image → image",
        edit:    "instruction edit",
      }[c] || c;
    },

    capabilityHint(c) {
      return {
        txt2img: "Generate a brand-new image from a text prompt alone.",
        img2img: "Start from an input image and regenerate it biased toward your prompt. Composition can drift; great for stylistic variations.",
        edit:    "Instruction-based editing — keeps the subject and composition intact, applies the change you describe. Best for 'add sunglasses', 'change the season', 'remove the car'.",
      }[c] || "";
    },

    stateChipClass(state) {
      if (state === "done") return "ok";
      if (state === "error") return "bad";
      if (state === "cancelled" || state === "cancelling") return "warn";
      return "";
    },

    downloadCaption(j) {
      const done = humanBytes(j.bytes_observed || 0);
      let line = done;
      if (j.bytes_total > 0) {
        const total = humanBytes(j.bytes_total);
        const pct = j.percent != null ? j.percent.toFixed(1) + "%" : "";
        line = `${done} / ${total}  ${pct}`;
      }
      // Surface the live byte-rate so users can tell at a glance whether the
      // download is actually progressing vs. wedged.
      if (j.state === "running" && j.speed_bps > 0) {
        line += ` · ${humanBytes(j.speed_bps)}/s`;
        if (j.eta_seconds != null && isFinite(j.eta_seconds)) {
          line += ` · ETA ${this.formatDuration(j.eta_seconds)}`;
        }
      } else if (j.state === "running") {
        // No measured speed yet (just started). Still tell the user it's alive.
        line += " · measuring…";
      }
      return line;
    },
  };
}

function humanBytes(n) {
  // DECIMAL (÷1000) to match how Hugging Face reports file sizes and how the
  // backend logs the same download total (downloads.py: total_bytes / 1e9).
  // Using binary (÷1024) here made the progress line show e.g. "4.30 GB" for a
  // download HF/the backend both call "4.62 GB" — same bytes, different number.
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1000 && i < units.length - 1) { n /= 1000; i++; }
  return n.toFixed(n < 10 ? 2 : 1) + " " + units[i];
}
