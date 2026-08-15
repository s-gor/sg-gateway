from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Apply the already validated R2 patch first.
runpy.run_path(str(ROOT / ".github/scripts/feat-02206-connections-polish-r2.py"), run_name="__main__")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


# This old publication test encoded the former full-width Mihomo choice as a
# permanent requirement. Keep that expectation for old trees, but make the
# new 022.06 feature explicitly expect the restored balanced layout.
publication_path = "tests/test_sg_gateway_021_full_publication_ru.py"
publication = read(publication_path)
if "import json\n" not in publication:
    publication = publication.replace(
        "from __future__ import annotations\n\n",
        "from __future__ import annotations\n\nimport json\n",
        1,
    )
old = '''    assert "compact client-only XMUX preset for Russian networks" in xray_css\n    assert "Mihomo as a separate full-width Connections block" in layout_css\n    assert "grid-template-columns: minmax(0, 1fr) !important" in layout_css\n'''
new = '''    assert "compact client-only XMUX preset for Russian networks" in xray_css\n    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))\n    feature = manifest.get("development_feature", {})\n    if feature.get("id") == "connections-polish-r1":\n        assert "Mihomo as a separate full-width Connections block" not in layout_css\n        assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);" in layout_css\n    else:\n        assert "Mihomo as a separate full-width Connections block" in layout_css\n        assert "grid-template-columns: minmax(0, 1fr) !important" in layout_css\n'''
assert publication.count(old) == 1
write(publication_path, publication.replace(old, new, 1))

# The Xray flow test used the first <details> element as a proxy for the end
# of the profile form. 022.06 legitimately adds an expert <details> inside
# that form, so use the real closing </form> boundary instead.
flow_path = "tests/test_xray_profile_flow_v23.py"
flow = read(flow_path)
old = '''    xray_start = template.index('id="xray-profiles"')\n    xray_end = template.index('<details class="cnv1-advanced', xray_start)\n    xray = template[xray_start:xray_end]\n'''
new = '''    xray_start = template.index('id="xray-profiles"')\n    xray_end = template.index('</form>', xray_start)\n    xray = template[xray_start:xray_end]\n'''
assert flow.count(old) == 1
write(flow_path, flow.replace(old, new, 1))
