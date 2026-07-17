# Deployment

This folder contains early deployment helpers for SG-Gateway.

## Installer

The installer is safe by default:

```sh
./deploy/install.sh
```

It runs in dry-run mode unless explicitly disabled:

```sh
SG_GATEWAY_DRY_RUN=0 ./deploy/install.sh
```

## Update

```sh
./deploy/update.sh
```

## Rollback

Rollback is currently a placeholder until release packaging is added.

## Uninstall

Uninstall is intentionally non-destructive in the MVP.