from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=(ROOT/'install.sh').read_text(encoding='utf-8')
def test_awg3_vendor_is_required_and_installed():
    assert 'AWG3_GO_VERSION="v3.0.0"' in S
    assert 'AWG3_GO_VENDOR_FILE="amneziawg-go-linux-amd64-v3.0.0"' in S
    assert 'Vendor core set: OK (7/7, linux/amd64)' in S
    b=ROOT/'vendor/cores/amneziawg-go-linux-amd64-v3.0.0'
    assert b.is_file() and b.stat().st_size>1_000_000
    assert 'SG_GATEWAY_02205_AWG3_VENDOR_RUNTIME_FIX1' in S
    assert 'install -m 0755 /usr/bin/awg "$PREFIX/awg3/bin/awg"' in S
    assert 'install -m 0755 /usr/bin/awg-quick "$PREFIX/awg3/bin/awg-quick"' in S
    assert '"$PREFIX/awg3/bin/amneziawg-go"' in S
def test_awg3_runtime_paths_match_installer():
    r=(ROOT/'hostd/sg_hostd/awg3_runtime.py').read_text(encoding='utf-8')
    h=(ROOT/'deploy/sg-gateway-awg3-userspace.sh').read_text(encoding='utf-8')
    assert '/opt/sg-gateway/awg3' in r and '/opt/sg-gateway/awg3' in h
    assert 'bin/amneziawg-go' in h
