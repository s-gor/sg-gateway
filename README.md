# SG-Gateway

SG-Gateway is a native Ubuntu control panel for one independent VPN/proxy server.
It is a separate project and does not use Controller, SG-Node or Cascade.

**Current GitHub baseline:** `0.1.0-021`

## What 021 contains

- native Ubuntu and systemd deployment, without Docker;
- one client catalogue with independent device accesses;
- AmneziaWG on fixed UDP port `585`;
- Xray VLESS Reality TCP, VLESS XHTTP Reality, VLESS XHTTP TLS and Hysteria 2;
- Hysteria 2 Salamander FinalMask support;
- Mieru, AnyTLS and TUIC through the managed Mihomo runtime;
- WARP outbound with automatic creation during clean installation;
- Routing and GeoFiles management;
- QR codes, technical links and SG Client subscriptions;
- diagnostics, backups, recovery and security pages;
- secret redaction in installer output and permanent logs.

## Production layout

```text
/opt/sg-gateway       application
/etc/sg-gateway       configuration
/var/lib/sg-gateway   database and runtime state
/var/log/sg-gateway   logs
```

Main services include the panel, host helper, Xray, AmneziaWG, Mihomo,
sing-box and Nginx. Existing user traffic is designed to continue if the web
panel is temporarily unavailable.

## Install from the checked-out source

Use a fresh supported Ubuntu EC2/VPS and run:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer performs candidate checks, creates backups before risky changes,
validates runtime configuration and redacts private credentials from its log.

## Full uninstall

```bash
chmod +x deploy/full-uninstall-ubuntu.sh
sudo ./deploy/full-uninstall-ubuntu.sh
```

The uninstaller requires an explicit confirmation before removing application
files and data.

## Local development on Windows

```powershell
.\scripts\run-dev.ps1
.\scripts\test.ps1
.\scripts\check.ps1
```

## Build the self-contained 021 installer

```bash
chmod +x build-run.sh
./build-run.sh
```

The builder excludes Git metadata, virtual environments, caches and generated
artifacts from the embedded source payload. The resulting `.run` supports:

```bash
./SG-Gateway-021-FULL-CLEAN-EC2-REBUILT.run --verify-only
./SG-Gateway-021-FULL-CLEAN-EC2-REBUILT.run --extract-only ./SG-Gateway-021-SOURCE
```

## Repository rules

- `main` is the only active development branch at this stage.
- SG-Gateway must not be mixed with SG-Panel or SG-AWG-Panel sources.
- Working runtime behaviour is changed only after a confirmed defect or an
  explicitly approved feature.
- Generated installers, ZIP files, patches, local databases and secrets are not
  committed. The clean seed database `data/sg-gateway.sqlite` is the only SQLite
  file intentionally tracked.
