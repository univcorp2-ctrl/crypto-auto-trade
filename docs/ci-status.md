# CI Status

The repository code, README images, dashboard UI, 100+ strategy variants, Japan exchange registry, tests, docs, devcontainer, and backup workflow definitions are committed.

Creating files under `.github/workflows/` has previously failed with:

```text
GitHub API 404: Not Found
```

If it fails again, only workflow paths are affected. Normal repository files are committed successfully. This indicates the GitHub automation token used by the Worker does not currently have workflow-file creation/update permission.

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
python -m crypto_auto_trade.cli validate --iterations 300 --trailing-stop-pct 0.05
python -m crypto_auto_trade.cli best-strategy --iterations 300 --trailing-stop-pct 0.05
python -m crypto_auto_trade.web
```
