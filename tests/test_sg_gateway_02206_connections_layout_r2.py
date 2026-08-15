from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'app/web/static/sg-preview28-final.css').read_text(encoding='utf-8')


def test_connections_layout_r2_compacts_xray_parameter_rows():
    assert 'Connections layout R2 — CSS only' in CSS
    assert '.xps2-parameter-row:not(.has-xhttp)' in CSS
    assert 'grid-column: 4' in CSS
    assert '.xps2-parameter-row.has-xhttp' in CSS
    assert 'align-items: center' in CSS
    assert 'min-height: 46px' in CSS


def test_connections_layout_r2_stops_awg_stretching():
    assert '.cnv1-engine-pair' in CSS
    assert 'align-items: start' in CSS
    assert '.cnv1-engine-awg .cnv1-engine-form-compact' in CSS
    assert 'flex: 0 0 auto' in CSS


def test_connections_layout_r2_gives_mihomo_readable_listener_grid():
    assert '.cnv1-engine-mihomo .mhv2-listeners-compact' in CSS
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr))' in CSS
    assert '.cnv1-engine-mihomo .mhv2-listener:first-child' in CSS
    assert 'grid-column: 1 / -1' in CSS
    assert 'overflow-wrap: anywhere' in CSS
