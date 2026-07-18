# Deployment

This folder contains early deployment helpers for SG-Gateway.

## Installer

Ubuntu one-line install:

```sh
curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-ubuntu.sh | sudo SG_GATEWAY_ADMIN_PASSWORD='change-this-password' sh
```

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

Ubuntu full uninstall:

```sh
curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/full-uninstall-ubuntu.sh | sudo SG_GATEWAY_CONFIRM_UNINSTALL=YES sh
```
