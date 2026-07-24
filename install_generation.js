// Heavy install: adds the generation stack to the existing conda_env. Required
// for any generation endpoint to work. Safe to run more than once.
//
// QUALIFIED LOCK: install the complete, checked-in generation lock so every Mac
// receives the same MLX/mflux/Diffusers runtime that passed release testing.
// The lock includes both base and generation packages and is regenerated only
// after the range requirements have been deliberately upgraded and qualified.
//
// VERIFY-THEN-NOTIFY: after installing we import the key modules. A failure
// prints a traceback, the matcher breaks the run, and the success notify never
// fires. The old script fired it unconditionally — telling users it worked even
// on total failure.
//
// Restart flow: stop the server first so its Python re-imports the freshly
// installed packages, then restart whichever server this machine runs (launchd
// service if installed, otherwise start.js).
module.exports = {
  requires: {
    bundle: "ai"
  },
  run: [
    {
      when: "{{running('start.js')}}",
      method: "script.stop",
      params: { uri: "{{path.resolve(cwd, 'start.js')}}" }
    },
    {
      method: "shell.run",
      params: {
        path: "app",
        conda: { "path": "{{path.resolve(cwd, 'conda_env')}}" },
        message: [
          "uv pip install -r requirements-generation.lock.txt"
        ]
      }
    },
    {
      method: "shell.run",
      params: {
        path: "app",
        conda: { "path": "{{path.resolve(cwd, 'conda_env')}}" },
        message: [
          "python -c \"import mflux; print('GEN_VERIFY_OK')\" 2>&1"
        ],
        on: [{ event: "/(ModuleNotFoundError|ImportError|Traceback)/", break: true }]
      }
    },
    {
      // install_service.sh (not restart_service.sh) rewrites the launchd plist to
      // the current on-disk serve script before relaunching — robust to the
      // serve.sh -> <app>-serve.sh rename. Idempotent.
      when: "{{exists('service/.installed')}}",
      method: "shell.run",
      params: { message: [ "bash install_service.sh" ] }
    },
    {
      when: "{{!exists('service/.installed')}}",
      method: "script.start",
      params: { uri: "start.js" }
    },
    {
      method: "notify",
      params: {
        html: "Generation engine installed &amp; verified. Server restarted — ready."
      }
    }
  ]
}
