# Install

SG-Gateway is Docker-first, with a small host helper.

## Dry Run

```sh
./deploy/install.sh
```

The dry run prints every action without changing the host.

## Real Install

```sh
SG_GATEWAY_DRY_RUN=0 ./deploy/install.sh
```

## Default Paths

```text
/opt/sg-gateway
/var/lib/sg-gateway
/var/log/sg-gateway
```

## Services

- `sg-gateway-panel`: Dockerized web panel.
- `sg-hostd`: local host helper, bound to `127.0.0.1:8090`.
- `sg-gateway-xray`: separate Xray runtime.

## Safety

- The panel does not mount Docker socket.
- The panel does not execute shell commands.
- Host operations must go through allow-listed `sg-hostd` commands.
- Installer dry-run is the default.