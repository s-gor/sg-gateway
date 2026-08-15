from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _installer() -> str:
    return (ROOT / 'install.sh').read_text(encoding='utf-8')

def test_installer_smoke_uses_real_production_entrypoint() -> None:
    text = _installer()
    start = text.index('stage_local_application_smoke_test()')
    end = text.index('saved_https_access()', start)
    block = text[start:end]
    assert 'from app.production import app' in block
    assert 'from app.main import create_app' not in block
    assert 'app = create_app()' not in block

def test_installer_generated_panel_unit_uses_production_entrypoint() -> None:
    text = _installer()
    start = text.index('stage_systemd_units()')
    end = text.index('stage_firewall_and_network()', start)
    block = text[start:end]
    assert 'app.production:app' in block
    assert 'app.main:app' not in block

def test_production_entrypoint_registers_subscription_helpers() -> None:
    from app.production import app
    with app.test_request_context('/'):
        ctx = {}
        for processor in app.template_context_processors[None]:
            ctx.update(processor())
    assert callable(ctx.get('sg_subscription_universal_url'))
    assert callable(ctx.get('sg_subscription_native_url'))
