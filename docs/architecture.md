# Architecture

SG-Gateway is built around a simple rule: the panel manages configuration, but
user traffic must continue even if the panel is unavailable.

## Components

- `panel`: web interface, client database, exports, jobs, diagnostics,
  backups, help content and security posture views.
- `xray`: Xray runtime container.
- `amneziawg`: host kernel module and interface controlled through `sg-hostd`.
- `sg-hostd`: limited host helper for allow-listed system operations.

## Panel Navigation

The panel is organized as English operational sections:

- `Dashboard`: compact gateway summary and connection readiness.
- `System`: health checks, runtime details, resource usage and safe links.
- `Clients`: unified client records and generated access artifacts.
- `Connections`: editable AmneziaWG and Xray endpoint settings.
- `Routing`: read-only effective route summary derived from connection settings.
- `Maintenance`: diagnostics, backups, restore actions and operation history.
- `Security`: authentication state, bind address exposure and recovery guidance.
- `Help`: short operator notes for the main workflows.

`Recovery` remains a minimal emergency page outside the primary side menu.

## Configuration Lifecycle

```text
draft
  -> validated
  -> backup
  -> applied
  -> health checked
  -> active
```

On failure, SG-Gateway must restore the last known good configuration.
