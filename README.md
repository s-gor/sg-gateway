# SG-Gateway

AmneziaWG and Xray. Simple, stable, and focused.

SG-Gateway is a Docker-first control panel for one server, one client list,
and two connection engines:

- AmneziaWG
- Xray VLESS Reality

The project is intentionally small in scope. It does not include clusters,
nodes, cascades, controllers, remote workers, or multi-server orchestration.

## Product Principles

- One human-friendly client database.
- Panel failure must not stop existing user connections.
- Every config change is validated before apply.
- Every risky operation has backup and rollback.
- Docker is used for application services.
- Host-level operations are delegated to a small, limited host helper.

## Current MVP

- Dashboard
- Unified clients
- Client detail cards
- SQLite storage
- Editable connection settings
- Generated AmneziaWG client payloads
- Generated Xray UUID payloads
- Downloadable access exports
- QR codes for access exports
- Maintenance diagnostics
- Downloadable diagnostic report
- Health checks
- Recovery page
- Database backup and restore
- Operation log
- Docker panel runtime
- sg-hostd allow-listed command contract
- Panel-side sg-hostd client
- Dry-run installer
- Release manifest and version endpoint
- Built-in user help
- Panel login
- Local check script and CI workflow
- Local Windows development scripts

## Local Development on Windows

Run:

```powershell
.\scripts\run-dev.ps1
```

Then open:

```text
http://127.0.0.1:8080
```

Default MVP password:

```text
admin
```

Run tests:

```powershell
.\scripts\test.ps1
```

Run checks:

```powershell
.\scripts\check.ps1
```

Run the same local quality gate used before commits:

```powershell
.\scripts\ci-local.ps1
```

Docker development:

```powershell
.\scripts\docker-dev.ps1
```

## Install Dry Run

```sh
./deploy/install.sh
```

## First Release Scope

- AmneziaWG access
- Xray VLESS Reality access
- Unified clients
- QR codes and export links
- Backup and restore
- Diagnostics
- Safe update and rollback
- Docker Compose deployment

## Repository Layout

```text
sg-gateway/
|-- app/             Web panel and product modules
|-- engines/         Engine adapters for AmneziaWG and Xray
|-- hostd/           Limited host helper service
|-- deploy/          Install, update, rollback, uninstall assets
|-- docker/          Container build files
|-- migrations/      Database migrations
|-- scripts/         Local development helpers
|-- tests/           Automated tests
`-- docs/            Architecture and operator docs
```

## Status

Early MVP scaffold.
