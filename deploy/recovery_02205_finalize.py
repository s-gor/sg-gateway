from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[PASS] {label}")


def patch_installer_identity_and_progress() -> None:
    path = ROOT / "install.sh"
    replace_once(path, 'VERSION="0.1.0-022.02"\n', 'VERSION="0.1.0-022.05"\n', "installer VERSION")
    replace_once(
        path,
        'INSTALLER_BUILD="02202-dual-awg"\n',
        'INSTALLER_BUILD="02205-sgpanel-xmux-warp-updater-r1"\n',
        "installer BUILD identity",
    )
    replace_once(
        path,
        'INSTALL_LOG="/var/log/sg-gateway-installer-02202.log"\n',
        'INSTALL_LOG="/var/log/sg-gateway-installer-02205.log"\n',
        "installer log identity",
    )
    replace_once(
        path,
        'RESUME_FILE="/root/sg-gateway-02202-installer-resume.env"\n',
        'RESUME_FILE="/root/sg-gateway-02205-installer-resume.env"\n',
        "installer resume identity",
    )
    replace_once(
        path,
        '# SG-Gateway 021 vendor bundle. Clean installation does not download these\n',
        '# SG-Gateway 022 vendor bundle. Clean installation does not download these\n',
        "vendor-bundle comment identity",
    )

    old_stage = '''run_stage() {
  local number="$1"
  local label="$2"
  local function_name="$3"
  CURRENT_STAGE="$number"
  CURRENT_LABEL="[${number}/${TOTAL_STAGES}] ${label}"
  run_quiet "$CURRENT_LABEL" "$function_name"
}
'''
    new_stage = '''run_stage() {
  local number="$1"
  local label="$2"
  local function_name="$3"
  CURRENT_STAGE="$number"
  CURRENT_LABEL="Этап ${number}/${TOTAL_STAGES} · ${label}"
  if [[ "$number" == "1" ]]; then
    run_live "$CURRENT_LABEL" "$function_name"
  else
    run_quiet "$CURRENT_LABEL" "$function_name"
  fi
}
'''
    replace_once(path, old_stage, new_stage, "restore SG-Panel installer progress contract")


def patch_clean_install_guidance() -> None:
    path = ROOT / "deploy/install-from-github.sh"
    text = path.read_text(encoding="utf-8")
    marker = "# SG_GATEWAY_02112_INSTALL_UPDATE_SPLIT"
    if marker not in text:
        anchor = "# The clean-install command must never mutate an existing SG-Gateway.\n"
        if text.count(anchor) != 1:
            raise SystemExit("clean-install safety anchor is not unique")
        text = text.replace(anchor, marker + "\n" + anchor, 1)
    old = "  printf '[SG-Gateway] Use the dedicated Update command.\\n'\n"
    new = """  printf '[SG-Gateway] Use the dedicated Update command.\\n'
  printf '[SG-Gateway] Updater: /opt/sg-gateway/deploy/update-from-github.sh\\n'
"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "/opt/sg-gateway/deploy/update-from-github.sh" not in text:
        raise SystemExit("clean-install updater guidance anchor not found")
    path.write_text(text, encoding="utf-8", newline="\n")
    print("[PASS] clean-install/update split remains explicit")


def patch_release_manifest() -> None:
    path = ROOT / "release-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = "0.1.0-022.05"
    manifest["build"] = "DEV-02205-SGPANEL-XMUX-WARP-UPDATER-R1"
    manifest["status"] = "DEVELOPMENT"
    manifest["channel"] = "dev-02205"
    manifest["next_development_line"] = "0.1.0-022.06"

    installer = manifest.setdefault("installer_update", {})
    installer["version"] = "02205-recovery-r1"

    warp = manifest.setdefault("warp", {})
    warp["automatic_on_full_install"] = False
    warp["default_state"] = "preserve-existing-or-absent"
    warp["one_click_create_and_activate"] = True
    warp["manual_creation_location"] = "Outbounds"

    xray = manifest.setdefault("xray", {})
    xray["xmux"] = {
        "client_only": True,
        "internal_modes": ["auto", "reduced", "expert"],
        "standard_max_connections": "2-4",
        "reduced_max_connections": "6",
        "reality_client_mode": "stream-one",
        "reality_server_mode": "auto",
        "tls_server_mode": "auto",
        "positive_max_connections_and_max_concurrency_conflict": True,
    }

    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("[PASS] release manifest synchronized with 022.05 recovery contract")


def main() -> None:
    patch_installer_identity_and_progress()
    patch_clean_install_guidance()
    patch_release_manifest()


if __name__ == "__main__":
    main()
