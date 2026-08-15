from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "deploy" / "update-from-github.sh"


def _block(body: str, name: str, next_name: str) -> str:
    start = body.index(f"{name}() {{")
    end = body.index(f"\n{next_name}() {{", start)
    return body[start:end]


def test_update_source_is_bound_to_exact_commit_in_both_source_modes() -> None:
    body = UPDATER.read_text(encoding="utf-8")
    light = _block(body, "prepare_source_light", "prepare_source")
    archive = _block(body, "prepare_source_archive", "prepare_source_light")
    resolver = _block(body, "resolve_source_commit", "prepare_source_archive")

    assert 'SOURCE_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD' in light
    assert '[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]' in light
    assert 'archive_url="https://github.com/${REPOSITORY}/archive/${SOURCE_COMMIT}.tar.gz"' in archive
    assert '"$archive_url" -o "$archive"' in archive
    assert 'refs/heads/$BRANCH' in resolver
    assert 'commits/${BRANCH}.atom' in resolver
    assert 'SOURCE_COMMIT="$resolved"' in resolver


def test_successful_update_atomically_binds_panel_state_to_live_tree() -> None:
    body = UPDATER.read_text(encoding="utf-8")
    bind = _block(body, "bind_panel_update_state", "main")

    assert 'SG_GATEWAY_PANEL_UPDATE_STATE="$PANEL_UPDATE_STATE"' in bind
    assert 'from app.maintenance.panel_updates import source_fingerprint' in bind
    assert 'fingerprint = source_fingerprint(root)' in bind
    assert '"commit": commit' in bind
    assert '"channel": channel' in bind
    assert '"source_fingerprint": fingerprint' in bind
    assert 'temporary.write_text' in bind
    assert 'os.chmod(temporary, 0o640)' in bind
    assert 'shutil.chown(temporary, user="root", group="sg-gateway")' in bind
    assert 'os.replace(temporary, state_path)' in bind
    assert 'runuser -u sg-gateway -- test -r "$PANEL_UPDATE_STATE"' in bind


def test_state_binding_happens_only_after_final_live_verification_and_before_success() -> None:
    body = UPDATER.read_text(encoding="utf-8")
    main = body[body.index("main() {"):]
    verify = main.index('run_stage 6 "Проверка HTTPS, Clients, Nginx и runtime" verify_final')
    bind = main.index("bind_panel_update_state", verify)
    finished = main.index("UPDATE_FINISHED=1", bind)
    assert verify < bind < finished


def test_built_in_panel_update_still_delegates_to_verified_shell_updater() -> None:
    runtime = (ROOT / "hostd" / "sg_hostd" / "panel_update_runtime.py").read_text(encoding="utf-8")
    update = runtime[runtime.index("def update_panel() -> dict[str, Any]:"):]
    assert 'deploy" / "update-from-github.sh"' in update
    assert 'env["SG_GATEWAY_GITHUB_BRANCH"] = GITHUB_BRANCH' in update
