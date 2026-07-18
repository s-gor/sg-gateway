# Ubuntu One-Line Install

Use these commands on Ubuntu when you want to reset the host and install the
current `main` branch from GitHub.

Full uninstall:

```sh
curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/full-uninstall-ubuntu.sh | sudo SG_GATEWAY_CONFIRM_UNINSTALL=YES sh
```

Install:

```sh
curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-ubuntu.sh | sudo SG_GATEWAY_ADMIN_PASSWORD='change-this-password' sh
```

Open after install:

```text
http://SERVER_IP:8080
```

The installer publishes the panel on `0.0.0.0:8080` by default so it can be
opened from another machine. Override with `SG_GATEWAY_BIND_HOST` and
`SG_GATEWAY_PORT` when needed.
