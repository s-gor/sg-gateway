# Security Model

SG-Gateway keeps the web panel away from direct host control.

## Rules

- The panel must not mount `/var/run/docker.sock`.
- The panel must not execute arbitrary shell commands.
- Host operations must go through `sg-hostd`.
- `sg-hostd` must expose only allow-listed actions.
- Config changes must be validated before they become active.
- A last known good configuration must always be available for rollback.

## Panel Login

The MVP panel uses a simple password-based session.

Environment variables:

```text
SG_GATEWAY_SECRET_KEY=change-this-secret
SG_GATEWAY_ADMIN_PASSWORD=change-this-password
```

Production deployments must replace both defaults.

The `Security` page summarizes:

- whether panel authentication is enabled;
- whether the admin password is still the default;
- the configured bind host and port;
- whether the panel is bound to a local or network-accessible interface;
- recovery and diagnostic actions available to an authenticated operator.

Public endpoints:

- `/login`
- `/health`
- `/recovery`

Authenticated diagnostic endpoint:

- `/maintenance/diagnostics.json`

Production deployments should expose the panel through a trusted private
network or an HTTPS reverse proxy.

## Recovery Principle

If the panel fails, AmneziaWG and Xray should continue serving existing users.
