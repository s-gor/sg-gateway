# Security

- The panel runs as an unprivileged service account.
- Privileged actions are delegated to the allow-listed host helper.
- Runtime configuration is validated before application.
- Risky changes use backup and rollback.
- Installer logs are mode `0600` and redact connection links, subscriptions,
  PEM blocks, private keys, tokens and long generated credentials.
- `.env`, local databases, logs and generated release artifacts are ignored by
  Git. Only the clean seed database is tracked.
- Recovery and certificate operations must not expose private material in the
  normal interface or diagnostics.
