// One-click Update — correct in EVERY run mode (launchd service, start.js, or
// stopped). Replaces the old split of "Update" vs "Update & Restart": one button
// pulls the latest code, refreshes deps, and restarts whichever server this
// machine actually runs. Dependencies converge through the repository-owned
// bridge; an existing generation environment remains installed-only.
module.exports = {
  run: [
    {
      // start.js mode: stop it so its Python exits and re-imports after install.
      // Service mode: start.js isn't running (skips) — the service keeps serving
      // through pull+install and only blips at the final kickstart. Stopped: no-op.
      when: "{{running('start.js')}}",
      method: "script.stop",
      params: { uri: "{{path.resolve(cwd, 'start.js')}}" }
    },
    {
      method: "shell.run",
      params: { message: "git pull" }
    },
    {
      // Base dependencies always converge; generation follows only when mflux
      // is already installed in this active environment.
      when: "{{exists('conda_env')}}",
      method: "shell.run",
      params: {
        path: "app",
        conda: { "path": "{{path.resolve(cwd, 'conda_env')}}" },
        message: ["python -m backend.dependency_convergence all-installed"]
      }
    },
    {
      // Restart the REAL server for this machine's mode — mutually exclusive so a
      // second server never fights the service for the fixed port. Use
      // install_service.sh (NOT restart_service.sh): it REWRITES the launchd plist
      // to match the current on-disk scripts before relaunching, so a git pull that
      // renamed the serve script (serve.sh -> <app>-serve.sh) can't leave the plist
      // kickstarting a deleted path. Idempotent + safe to run every update.
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
      params: { html: "Updated &amp; restarted — you're on the latest version." }
    }
  ]
}
