# Host Helper

`sg-hostd` is the only component that should perform host-level operations for
SG-Gateway.

## Rules

- No arbitrary shell execution.
- No Docker socket mounted into the panel.
- Only allow-listed commands.
- Local-only HTTP listener by default.
- Every future mutating command must validate inputs and return structured
  results.

## MVP Command Contract

```text
GET  /health
GET  /commands
POST /commands/awg.status
POST /commands/xray.status
POST /commands/nftables.status
POST /commands/system.diagnostics
```

The current implementation is intentionally mock-only. Real host operations
will be added command by command.