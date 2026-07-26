from __future__ import annotations

import json
from pathlib import Path

from app.security import tls


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "deploy/configure-panel-access.sh").read_text(encoding="utf-8")
HOSTD_JOBS = (ROOT / "hostd/sg_hostd/operation_jobs.py").read_text(encoding="utf-8")
RUNNER = (ROOT / "hostd/sg_hostd/operation_job_runner.py").read_text(encoding="utf-8")
TLS_SOURCE = (ROOT / "app/security/tls.py").read_text(encoding="utf-8")
TERMINAL = (ROOT / "app/web/templates/operation_job.html").read_text(encoding="utf-8")
SECURITY = (ROOT / "app/web/templates/security.html").read_text(encoding="utf-8")


def test_https_uses_sg_panel_transactional_shell_architecture():
    for marker in (
        "configure-panel-access.sh --mode https",
        "certbot certonly",
        "HTTP-01",
        "create_backup",
        "restore_backup",
        "trap rollback EXIT INT TERM",
        "wait_for_backend",
        "wait_for_https",
        "error_page 497 =308",
        "renewal-hooks/deploy/reload-sg-gateway-nginx.sh",
        "--mode refresh",
        "apply_client_runtime",
        "proxy_cookie_flags ~ secure httponly samesite=lax",
    ):
        assert marker in SCRIPT
    assert "systemctl restart sg-gateway.service" not in SCRIPT
    assert (
        "exec /bin/bash /opt/sg-gateway/deploy/configure-panel-access.sh "
        "--mode refresh"
    ) in SCRIPT
    assert "50-https-local-bind.conf" not in SCRIPT


def test_tls_live_job_runs_shell_script_not_python_tls_runner():
    assert (
        'PANEL_ACCESS_SCRIPT = Path("/opt/sg-gateway/deploy/configure-panel-access.sh")'
        in HOSTD_JOBS
    )
    assert '"--mode",\n            "https"' in HOSTD_JOBS
    assert 'command=(' in HOSTD_JOBS
    assert (
        "export SG_GATEWAY_SECURITY_STATE_DIR=/var/lib/sg-gateway/security"
        in HOSTD_JOBS
    )
    assert 'cd /opt/sg-gateway' in HOSTD_JOBS
    assert 'if sys.argv[1] == "tls_issue"' not in RUNNER
    assert "_SCRIPT_DIR" in RUNNER
    assert "sys.path[:0]" in RUNNER


def test_panel_never_reads_root_only_letsencrypt_files():
    assert "cert_path.is_file()" not in TLS_SOURCE
    assert "openssl\", \"x509" not in TLS_SOURCE
    assert 'state.get("certificate")' in TLS_SOURCE
    assert "_safe_is_file(nginx_conf)" in TLS_SOURCE


def test_https_terminal_redirects_when_old_http_origin_disappears():
    assert "hadSuccessfulPoll" in TERMINAL
    assert "consecutiveFailures >= 3" in TERMINAL
    assert "window.location.replace(targetUrl)" in TERMINAL
    assert "root.dataset.kind === 'tls_issue'" in TERMINAL


def test_security_page_uses_public_and_backend_ports_correctly():
    assert "TCP 80 · TCP {{ tls.public_port }}" in SECURITY
    assert "127.0.0.1:{{ tls.backend_port }}" in SECURITY
    assert "{{ tls.public_url if tls.https_ready else 'Не настроен' }}" in SECURITY
    assert (
        "{{ tls.public_url if tls.https_ready else "
        "'Защищённый вход ещё не включён' }}"
    ) in SECURITY


def test_overview_reads_certificate_metadata_from_state(tmp_path, monkeypatch):
    state_dir = tmp_path / "security"
    state_dir.mkdir()
    (state_dir / "tls-state.json").write_text(
        json.dumps(
            {
                "domain": "panel.example.com",
                "public_port": 63443,
                "backend_port": 18080,
                "https_ready": True,
                "certificate": {
                    "issuer": "Test CA",
                    "not_after": "Dec 31 23:59:59 2026 GMT",
                    "days_left": 100,
                },
                "certificate_path": "/etc/letsencrypt/live/panel.example.com/fullchain.pem",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SG_GATEWAY_SECURITY_STATE_DIR", str(state_dir))
    monkeypatch.setenv("SG_GATEWAY_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SG_GATEWAY_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("SG_GATEWAY_PUBLIC_PORT", "63443")
    monkeypatch.setenv("SG_GATEWAY_PORT", "18080")
    monkeypatch.setattr(tls, "_service_active", lambda name: name == "nginx.service")
    monkeypatch.setattr(tls, "_service_enabled", lambda name: name == "certbot.timer")
    monkeypatch.setattr(tls, "_safe_is_file", lambda path: True)

    result = tls.overview()

    assert result["https_ready"] is True
    assert result["certificate"]["issuer"] == "Test CA"
    assert result["public_url"] == "https://panel.example.com:63443"
    assert result["backend_port"] == 18080


def test_tls_job_wrapper_uses_direct_shell_command_and_runtime_environment(
    tmp_path,
    monkeypatch,
):
    import importlib.util
    from types import SimpleNamespace

    module_path = ROOT / "hostd/sg_hostd/operation_jobs.py"
    spec = importlib.util.spec_from_file_location("sg_gateway_test_operation_jobs", module_path)
    assert spec and spec.loader
    jobs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jobs)

    jobs_dir = tmp_path / "jobs"
    request = tmp_path / "tls-request.json"
    access_script = tmp_path / "configure-panel-access.sh"
    access_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    request.write_text(
        json.dumps({"domain": "panel.example.com", "public_port": 63443}),
        encoding="utf-8",
    )

    monkeypatch.setattr(jobs, "JOB_DIR", jobs_dir)
    monkeypatch.setattr(jobs, "REQUEST", request)
    monkeypatch.setattr(jobs, "PANEL_ACCESS_SCRIPT", access_script)
    monkeypatch.setattr(jobs, "_panel_group", lambda: 0)
    monkeypatch.setattr(jobs.os, "chown", lambda *args: None)

    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(jobs.subprocess, "run", fake_run)

    result = jobs.start_tls_issue_job()

    assert result["target_url"] == "https://panel.example.com:63443/security"
    wrapper = (jobs_dir / f"{result['job_id']}.sh").read_text(encoding="utf-8")
    assert f"/bin/bash {access_script} --mode https" in wrapper
    assert "export SG_GATEWAY_DATA_DIR=/var/lib/sg-gateway" in wrapper
    assert "export SG_GATEWAY_SECURITY_STATE_DIR=/var/lib/sg-gateway/security" in wrapper
    assert "cd /opt/sg-gateway" in wrapper
    assert calls and calls[0][0][0] == "systemd-run"
