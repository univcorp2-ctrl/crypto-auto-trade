# CI Status

Attempted to create real GitHub Actions workflow files under `.github/workflows/`.

Workflows requested:

- `.github/workflows/ci.yml`
- `.github/workflows/market-simulation.yml`
- `.github/workflows/realtime-validation.yml`

If GitHub API rejects those paths with `GitHub API 404: Not Found`, the repository automation token does not currently have workflow-file creation/update permission. Normal repository files can still be committed.

Backup workflow definitions are committed under:

- `docs/workflows/ci.yml`
- `docs/workflows/market-simulation.yml`
- `docs/workflows/realtime-validation.yml`

Expected Actions jobs once workflow-path permission works:

1. CI
   - install dependencies
   - ruff
   - pytest
   - validation artifact
   - best-strategy artifact
   - sample 5Y simulation artifact

2. Market Snapshot and 5Y Simulation
   - workflow_dispatch
   - scheduled every 12 hours
   - market snapshot artifact
   - five-year simulation artifact

3. Realtime Validation
   - workflow_dispatch
   - scheduled every 6 hours
   - live OHLCV validation artifacts
