# SG-Gateway 022.03 — isolated AmneziaWG 3.0 userspace

Status: **working live validation** on 2026-08-12.

## Baseline

- Frozen SG-Gateway `0.1.0-021.12` / `MAIN-02112`.
- AWG2 remains the original 021.12 kernel/runtime path and is not replaced.
- AWG3 is added independently.

## Architecture

### AWG2

- Existing 021.12 runtime.
- Network: `10.66.0.0/16`.
- Existing AWG2 configuration and service are preserved byte-for-byte by the cumulative installer verification.

### AWG3

- Separate network: `10.67.0.0/16`.
- Separate client/server credentials and obfuscation namespace.
- Separate AmneziaWG 3 tools under `/opt/sg-gateway/awg3/bin`.
- Separate `amneziawg-go` userspace interface `awg3`.
- Separate systemd service `sg-gateway-awg3.service`.
- AWG3 configuration supports `S3/S4`, `HeaderProtectionKey`, content padding, rekey/reject/keepalive/handshake ranges and ranged persistent keepalive.

## Live validation

The isolated userspace design connected successfully and passed traffic tests on the same clean EC2 test host.

- AWG3: about **353.98 Mbps download / 293.12 Mbps upload**, ping **56 ms**.
- AWG2: about **345.84 Mbps download / 302.13 Mbps upload**, ping **58 ms**.

The observed difference is within normal test variation. Most importantly, AWG2 remained functional while AWG3 used its independent userspace runtime.

## Installer

Use `deploy/SG-Gateway-02203-AWG3-USERSPACE-CUMULATIVE.run` only on a clean installed 021.12 baseline.

The installer:

1. validates exact 021.12 baseline and records AWG2 hashes/state;
2. downloads the pinned 022.03 source snapshot;
3. builds private AWG3 tools;
4. builds pinned `amneziawg-go`;
5. installs only the AWG3 project additions;
6. creates the isolated AWG3 service;
7. migrates AWG3 credentials using the production database path;
8. verifies AWG2 is unchanged and AWG3 is active.

On failure it rolls the AWG3 changes back and keeps the detailed failing stage in the technical log.
