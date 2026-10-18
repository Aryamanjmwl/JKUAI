# Contributing

See [local development](docs/local-development.md) for setup. From the repository root,
with the Python environment active, run:

```sh
ruff check .
ruff format --check .
pytest -q
```

From `frontend`, run:

```sh
npm ci
npm test
npm run build
```

CI also exercises real search services and browser flows. See the development guide
for running those checks locally. Provider contract tests use simulated responses;
never commit a provider credential to make a test pass.

Keep changes focused. Explain retrieval/ranking changes and include relevant regression
coverage. Keep the README simple; put implementation details in `docs/`.
Do not commit keys, downloaded PDFs, model weights, generated reports, or personal data.
Use short commit subjects such as `Fix PDF table extraction`.

The optional `.pre-commit-config.yaml` runs Ruff before commits when pre-commit is installed.
