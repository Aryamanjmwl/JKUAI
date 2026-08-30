# Contributing

## Local checks

Before opening a pull request, run:

```powershell
ruff check .
ruff format --check .
pytest -q
```

Keep pull requests focused. Changes to retrieval or ranking must include a test and an evaluation note. Never commit API keys, downloaded university documents, model weights, or personal data.

## Commit style

Use short imperative subjects, for example:

- `Add permission filter to vector retrieval`
- `Measure p95 query latency`
- `Fix duplicate document ingestion`
