# Quality Checks

SG-Gateway has a lightweight quality gate for early MVP work.

## Local Check

```powershell
.\scripts\check.ps1
```

It checks:

- Python syntax
- release manifest consistency
- Docker Compose config, when Docker is available
- pytest, when `.venv` exists

## Full Local Test

```powershell
.\scripts\test.ps1
.\scripts\check.ps1
```

## GitHub Actions

The `CI` workflow runs on push and pull requests to `main`.

It checks:

- Python dependencies
- syntax
- release manifest
- Docker Compose config
- panel tests
- hostd tests