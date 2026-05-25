module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        path: "app",
        conda: {
          "path": "{{path.resolve(cwd, 'conda_env')}}"
        },
        env: {
          "PYTHONUNBUFFERED": "1"
        },
        message: [
          // Binds on every network interface (LAN, Tailscale, loopback) at a
          // fixed port so other devices on your tailnet/LAN can hit the API
          // directly without going through Pinokio's proxy. Change the port
          // here if 47868 clashes with something else on your machine.
          "python -m uvicorn backend.main:app --host 0.0.0.0 --port 47868"
        ],
        on: [{
          event: "/Uvicorn running on (http:\\/\\/[0-9.:]+)/",
          done: true
        }, {
          event: "/error:/i",
          break: false
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    }
  ]
}
