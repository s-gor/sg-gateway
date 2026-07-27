from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mihomo_listener_readiness_waits_before_failure():
    helper = (
        ROOT / "app" / "mihomo" / "helper.py"
    ).read_text(encoding="utf-8")

    assert "import time" in helper
    assert "def _verify_listeners(meta: dict, timeout: float = 30.0)" in helper
    assert "deadline = time.monotonic()" in helper
    assert "time.sleep(0.5)" in helper
    assert '"is-active",' in helper
    assert "После 30 секунд не слушаются" in helper


def test_mihomo_apply_verifies_listener_after_service_start():
    helper = (
        ROOT / "app" / "mihomo" / "helper.py"
    ).read_text(encoding="utf-8")

    apply_start = helper.index("def apply_candidate(")
    apply_end = helper.index("\ndef ", apply_start + 1)
    apply_body = helper[apply_start:apply_end]

    active = (
        '_run(["systemctl", "is-active", "--quiet", '
        '"mihomo.service"])'
    )
    assert active in apply_body
    assert "_verify_listeners(meta)" in apply_body
    assert apply_body.index(active) < apply_body.index(
        "_verify_listeners(meta)"
    )
