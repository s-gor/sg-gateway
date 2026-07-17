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
├── app/             Web panel and product modules
├── engines/         Engine adapters for AmneziaWG and Xray
├── hostd/           Limited host helper service
├── deploy/          Install, update, rollback, uninstall assets
├── docker/          Container build files
├── migrations/      Database migrations
├── tests/           Automated tests
└── docs/            Architecture and operator docs
```

## Status

Early project scaffold.
