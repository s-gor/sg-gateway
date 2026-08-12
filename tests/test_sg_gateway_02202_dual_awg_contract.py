from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def function_block(body: str, name: str, next_name: str) -> str:
    start = body.index(f"def {name}")
    end = body.index(f"def {next_name}", start)
    return body[start:end]


def test_dual_awg_contract():
    repository = text("app/clients/repository.py")
    provisioning = text("app/engines/provisioning.py")
    access = text("app/clients/access.py")
    exports = text("app/clients/exports.py")
    runtime = text("hostd/sg_hostd/client_runtime.py")
    awg3_runtime = text("hostd/sg_hostd/awg3_runtime.py")
    unit = text("deploy/sg-gateway-awg3.service")
    helper = text("deploy/sg-gateway-awg3-userspace.sh")
    clients = text("app/web/templates/clients.html")
    manifest = text("vendor/cores/SHA256SUMS")

    assert '"amneziawg3"' in repository
    assert '"amneziawg", "amneziawg3"' in repository
    assert 'engine == "amneziawg3"' in provisioning
    assert '"address": f"10.67.' in provisioning
    assert '"port": 586' in provisioning

    assert 'kind="amneziawg"' in access
    assert 'kind="amneziawg3"' in access
    assert 'title="AmneziaWG 2.0"' in access
    assert 'title="AmneziaWG 3.0"' in access
    assert 'build_awg3_config' in exports
    assert '"amneziawg3": "amneziawg3"' in exports
    assert 'value="amneziawg3"' in clients

    assert 'AWG3_PORT = 586' in awg3_runtime
    assert 'AWG3_ROOT = Path("/opt/sg-gateway/awg3")' in awg3_runtime
    assert '10.67.0.1/16' in awg3_runtime
    assert 'HeaderProtectionKey' in awg3_runtime
    assert 'ContentPaddingAddition' in awg3_runtime
    assert '/etc/systemd/system' not in awg3_runtime
    assert '"enable"' not in awg3_runtime
    assert 'sysctl' not in awg3_runtime.lower()

    awg2_apply = function_block(runtime, "_apply_awg()", "_set_xray_config_permissions")
    assert '"systemctl", "enable"' not in awg2_apply
    assert 'sysctl' not in awg2_apply
    assert 'apply_awg3()' in runtime

    assert '/opt/sg-gateway/deploy/sg-gateway-awg3-userspace.sh up' in unit
    assert '/usr/bin/awg-quick' not in unit
    assert '/opt/sg-gateway/awg3/bin/amneziawg-go' in unit
    assert 'AWG_GO="$AWG3_ROOT/bin/amneziawg-go"' in helper
    assert 'AWG="$AWG3_ROOT/bin/awg"' in helper
    assert 'AWG_QUICK="$AWG3_ROOT/bin/awg-quick"' in helper

    assert '090f9383532822a756d078890b447e00af7f46bd30a10f9f47c46d633d807b19' in manifest
    assert 'c493ab8ac6b4d1b8ccbd0c07a4a43011ccfc976a99ea5ef30cbd9175fb9364d2' in manifest
