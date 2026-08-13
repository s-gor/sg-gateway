# SG-Gateway 0.1.0-022.04 · LIVE FULL R3

Accepted live checkpoint: 2026-08-13.

Machine release BUILD-ID: `RELEASE-02204-LIVE-FULL-R3`  
Machine release SHA256: `a1179fe21a996e799fa96c456e7de75c56166ff7abadabab53ed9767257056db`

The machine R3 artifact is the authoritative frozen live copy. This branch preserves the corresponding source history plus the accepted Low-resolution Desktop patch. It is not a clean-machine installer.

## Accepted in 022.04

- AmneziaWG 2.0 and separate AmneziaWG 3.0 userspace runtime.
- Hysteria 2 Off / Salamander / Gecko; Gecko uses FinalMask Salamander + `packetSize: "512-1200"`.
- Correct Hysteria2 obfs export using `obfs` and `obfs-password`.
- Working inline Xray candidate check with real form action resolution.
- Nine UI channels: Reality TCP, XHTTP Reality, XHTTP TLS, Hysteria2, AWG2, AWG3, Mieru, AnyTLS, TUIC v5.
- Unified protocol order and accepted 3x3 desktop picker.
- Accepted readable client/device card sizing.
- Protected Disable actions; device Disable keeps the warm-brown treatment.
- Device cards open collapsed without the initial visual jump.
- Low-resolution Desktop for 1366x768 / 1280x720 class displays and low-height desktop windows; large desktop and existing mobile behavior stay unchanged.

Low-resolution source: `app/web/static/sg-low-resolution-v1.css`.  
Historical 022.04 application step: `deploy/sg-gateway-02204-low-resolution.sh`.

## Deferred to 0.1.0-022.05

- Native SG subscription: client -> all devices -> all nine profiles.
- Replacement of the legacy four-profile Base64 SUB behavior.
- Safe `Проверить .sgbackup` action without restore.
- AnyTLS/TUIC URI normalization and related SG-Client compatibility work.
- True zero-to-clean-Ubuntu bootstrap installer.

New functional development starts from this checkpoint.
