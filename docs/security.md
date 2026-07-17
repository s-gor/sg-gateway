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

Public endpoints:

- `/login`
- `/health`
- `/recovery`
- `/maintenance/diagnostics.json`

## Recovery Principle

If the panel fails, AmneziaWG and Xray should continue serving existing users.