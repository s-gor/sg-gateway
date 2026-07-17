# Deployment

This folder will contain the installer, updater, rollback script, and uninstall
flow for SG-Gateway.

The target deployment model is Docker-first, with a limited host helper for
operations that cannot safely run inside the web container.
