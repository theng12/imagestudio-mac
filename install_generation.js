// Heavy install: adds mflux + MLX + supporting deps to the existing conda_env.
// Required for any /api/generate/* endpoint to work. Safe to run more than once.
module.exports = {
  requires: {
    bundle: "ai"
  },
  run: [
    {
      method: "shell.run",
      params: {
        path: "app",
        conda: {
          "path": "{{path.resolve(cwd, 'conda_env')}}"
        },
        message: [
          "uv pip install -r requirements-generation.txt"
        ]
      }
    },
    {
      method: "notify",
      params: {
        html: "Generation engine installed. Restart the server (Stop → Start) to enable the Generate tab."
      }
    }
  ]
}
