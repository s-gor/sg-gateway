# Security Model

SG-Gateway keeps the web panel away from direct host control.

## Rules

- The panel must not mount `/var/run/docker.sock`.
- The panel must not execute arbitrary shell commands.
- Host operations must go through `sg-hostd`.
- `sg-hostd` must expose only allow-listed actions.
- Config changes must be validated before they become active.
- A last known good configuration must always be available for rollback.

## Recovery Principle

If the panel fails, AmneziaWG and Xray should continue serving existing users.
