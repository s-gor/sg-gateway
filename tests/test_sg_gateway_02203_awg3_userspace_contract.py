from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_awg3_is_userspace_and_does_not_reuse_awg2_service_runtime():
    service = text("deploy/sg-gateway-awg3.service")
    helper = text("deploy/sg-gateway-awg3-userspace.sh")
    runtime = text("hostd/sg_hostd/awg3_runtime.py")

    assert "/opt/sg-gateway/deploy/sg-gateway-awg3-userspace.sh up" in service
    assert "/usr/bin/awg-quick" not in service
    assert "/opt/sg-gateway/awg3/bin/amneziawg-go" in service

    assert 'AWG3_ROOT="/opt/sg-gateway/awg3"' in helper
    assert 'AWG_GO="$AWG3_ROOT/bin/amneziawg-go"' in helper
    assert 'AWG="$AWG3_ROOT/bin/awg"' in helper
    assert 'AWG_QUICK="$AWG3_ROOT/bin/awg-quick"' in helper

    assert 'AWG3_ROOT = Path("/opt/sg-gateway/awg3")' in runtime
    assert 'AWG3_AWG = AWG3_ROOT / "bin/awg"' in runtime
    assert 'AWG3_AWG_QUICK = AWG3_ROOT / "bin/awg-quick"' in runtime
    assert 'AWG3_PORT = 586' in runtime


def test_awg3_header_protection_contract():
    runtime = text("hostd/sg_hostd/awg3_runtime.py")
    exports = text("app/clients/exports.py")

    assert '"s4": 12' in runtime
    assert "S1-S4 должны быть не меньше 12" in runtime
    assert "HeaderProtectionKey =" in exports
    assert "ContentPaddingAddition =" in exports
    assert "RekeyAfterTime =" in exports
    assert "MaxHandshakeAttempts =" in exports
    assert '"25-35"' in runtime


def test_awg2_and_awg3_have_separate_identity_and_addresses():
    runtime = text("hostd/sg_hostd/awg3_runtime.py")
    provisioning = text("app/engines/provisioning.py")

    assert 'AWG3_SUBNET = "10.67.0.0/16"' in runtime
    assert "SG_GATEWAY_AWG3_PRIVATE_KEY" in runtime
    assert "SG_GATEWAY_AWG3_PUBLIC_KEY" in runtime
    assert "SG_GATEWAY_AWG3_HEADER_PROTECTION_KEY" in runtime
    assert 'if engine == "amneziawg3"' in provisioning
    assert '"generation": 3' in provisioning
