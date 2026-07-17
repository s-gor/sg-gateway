# Docker

## Local development

```powershell
.\scripts\docker-dev.ps1
```

Open:

```text
http://127.0.0.1:8080
```

## Production-like panel run

```powershell
.\scripts\docker-prod.ps1
```

The panel binds to `127.0.0.1:8080` and is intended to sit behind Nginx.

## Notes

- The panel container runs as a non-root user.
- The production compose keeps the panel filesystem read-only.
- Persistent data is stored in Docker volumes.
- Xray remains a separate service.
- AmneziaWG host operations will later go through `sg-hostd`.