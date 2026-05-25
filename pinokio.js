module.exports = {
  version: "3.6",
  title: "Image Studio KH",
  description: "Apple Silicon FLUX image studio — model catalog, download manager, weight imports.",
  icon: "icon.png",
  menu: async (kernel, info) => {
    const installed = info.exists("conda_env")
    const generationInstalled = info.exists("conda_env/lib/python3.12/site-packages/mflux")
    const running = {
      install: info.running("install.js"),
      install_generation: info.running("install_generation.js"),
      start: info.running("start.js"),
      update: info.running("update.js"),
      reset: info.running("reset.js")
    }

    if (running.install) {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Installing",
        href: "install.js"
      }]
    }
    if (running.install_generation) {
      return [{
        default: true,
        icon: "fa-solid fa-wand-magic-sparkles",
        text: "Installing Generation",
        href: "install_generation.js"
      }]
    }
    if (running.update) {
      return [{
        default: true,
        icon: "fa-solid fa-rotate",
        text: "Updating",
        href: "update.js"
      }]
    }
    if (running.reset) {
      return [{
        default: true,
        icon: "fa-solid fa-broom",
        text: "Resetting",
        href: "reset.js"
      }]
    }

    if (!installed) {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Install",
        href: "install.js"
      }]
    }

    if (running.start) {
      const local = info.local("start.js")
      if (local && local.url) {
        // Cache-bust so Pinokio's embedded webview can't serve a stale build.
        // menu() re-runs every time the sidebar refreshes, so each click on
        // "Open UI" loads a unique URL the webview hasn't cached.
        const cb = Date.now()
        const bust = `?_cb=${cb}`
        // Browser-friendly URL: replace 0.0.0.0 (server-bind) with localhost
        // (client-reachable) so the external browser can actually connect.
        // Also pluck the port for compact display in the sidebar.
        const browserUrl = local.url.replace("0.0.0.0", "localhost")
        const portMatch = local.url.match(/:(\d+)/)
        const port = portMatch ? portMatch[1] : "?"
        return [
          {
            default: true,
            icon: "fa-solid fa-rocket",
            text: "Open UI",
            href: `${local.url}/${bust}`
          },
          {
            icon: "fa-solid fa-cube",
            text: "Models",
            href: `${local.url}/${bust}#/models`
          },
          {
            icon: "fa-solid fa-download",
            text: "Downloads",
            href: `${local.url}/${bust}#/downloads`
          },
          // ── Escape hatch (v1.1.1) ──
          // If the embedded webview ever caches a broken state and shows a
          // black/blank screen, the user is stranded because Pinokio's
          // refresh buttons hit the same cached webview. These two items
          // make the URL visible + give a one-click way out:
          //   1. The "Port: 47868 (open externally)" item opens the WebUI
          //      in the system default browser via open_external.js.
          //   2. Even without clicking, the port number is always visible in
          //      the sidebar — read it and type into Chrome / Safari if all
          //      else fails.
          {
            icon: "fa-solid fa-arrow-up-right-from-square",
            text: `Port ${port} · Open in Browser`,
            href: "open_external.js",
            params: { url: browserUrl }
          },
          {
            icon: "fa-solid fa-terminal",
            text: "Terminal",
            href: "start.js"
          },
          {
            icon: "fa-solid fa-folder-tree",
            text: "HF Cache",
            href: "cache/HF_HOME/hub?fs=true"
          },
          {
            icon: "fa-solid fa-file-image",
            text: "Outputs",
            href: "app/output?fs=true"
          },
          {
            icon: "fa-solid fa-wand-magic-sparkles",
            text: generationInstalled ? "Reinstall Generation" : "Install Generation",
            href: "install_generation.js"
          }
        ]
      }
      return [{
        default: true,
        icon: "fa-solid fa-terminal",
        text: "Terminal",
        href: "start.js"
      }]
    }

    return [
      {
        default: true,
        icon: "fa-solid fa-power-off",
        text: "Start",
        href: "start.js"
      },
      {
        icon: "fa-solid fa-folder-tree",
        text: "HF Cache",
        href: "cache/HF_HOME/hub?fs=true"
      },
      {
        icon: "fa-solid fa-file-image",
        text: "Outputs",
        href: "app/output?fs=true"
      },
      {
        icon: "fa-solid fa-wand-magic-sparkles",
        text: generationInstalled ? "Reinstall Generation" : "Install Generation",
        href: "install_generation.js"
      },
      {
        icon: "fa-solid fa-rotate",
        text: "Update",
        href: "update.js"
      },
      {
        icon: "fa-solid fa-plug",
        text: "Reinstall",
        href: "install.js"
      },
      {
        icon: "fa-regular fa-circle-xmark",
        text: "Reset",
        href: "reset.js"
      }
    ]
  }
}
