# Architecture

SG-Gateway is built around a simple rule: the panel manages configuration, but
user traffic must continue even if the panel is unavailable.

## Components

- `panel`: web interface, client database, exports, jobs, diagnostics.
- `xray`: Xray runtime container.
- `amneziawg`: host kernel module and interface controlled through `sg-hostd`.
- `sg-hostd`: limited host helper for allow-listed system operations.

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
