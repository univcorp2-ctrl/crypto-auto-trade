# CI Status

The repository code, README images, dashboard UI, tests, docs, devcontainer, and backup workflow definitions are committed.

Creating files under `.github/workflows/` failed with:

```text
GitHub API 404: Not Found
```

Only workflow paths failed. Normal repository files committed successfully. This indicates the GitHub automation token used by the Worker does not currently have workflow-file creation/update permission.

Backup workflow definitions are committed here:

- `docs/workflows/ci.yml`
- `docs/workflows/realtime-validation.yml`

When workflow-file permission is available, these should be copied to:

- `.github/workflows/ci.yml`
- `.github/workflows/realtime-validation.yml`

Until then, run locally or in Codespaces:

```bash
pip install -e '.[dev,web,live]'
ruff check .
pytest -q
python -m crypto_auto_trade.cli validate --iterations 200 --trailing-stop-pct 0.05
python -m crypto_auto_trade.web
```
