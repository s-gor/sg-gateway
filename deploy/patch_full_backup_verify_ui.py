from __future__ import annotations

import sys
from pathlib import Path


VERIFY_MARKER = "data-sg-full-verify-button"
VERIFY_ACTION_ATTRS = 'name="backup_action" value="verify"'


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Full Backup verify UI anchor not found: {label}")
    return text.replace(old, new, 1)


def patch_text(text: str) -> str:
    if "'backup.full.verify': 'Проверен полный backup'" not in text:
        text = _replace_once(
            text,
            "  'backup.restore': 'Восстановлена резервная копия',\n",
            "  'backup.restore': 'Восстановлена резервная копия',\n"
            "  'backup.full.verify': 'Проверен полный backup',\n",
            "operation title",
        )

    if VERIFY_MARKER not in text:
        restore_button = """            <button class=\"button mtv2-restore sg-full-restore-button\" type=\"submit\" disabled data-sg-full-restore-button>
              <svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M4 12a8 8 0 1 0 2.3-5.7M4 4v6h6\"/></svg>
              <span>Восстановить сервер</span>
            </button>"""
        verify_and_restore = """            <button class=\"button sg-full-restore-button sg-full-verify-button\" type=\"submit\"
                    name=\"backup_action\" value=\"verify\"
                    disabled data-sg-full-verify-button>
              <svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"m5 12 4 4L19 6\"/></svg>
              <span>Проверить backup</span>
            </button>
""" + restore_button
        text = _replace_once(text, restore_button, verify_and_restore, "restore button")
    else:
        # Migrate the first implementation that posted Verify to a second URL.
        old = """                    formaction=\"{{ url_for('verify_full_backup_route') }}\" formmethod=\"post\"
                    disabled data-sg-full-verify-button>"""
        new = """                    name=\"backup_action\" value=\"verify\"
                    disabled data-sg-full-verify-button>"""
        if old in text:
            text = text.replace(old, new, 1)

    if "const verifyButton = form.querySelector(\"[data-sg-full-verify-button]\");" not in text:
        text = _replace_once(
            text,
            "      const restoreButton = form.querySelector(\"[data-sg-full-restore-button]\");\n"
            "      if (!input || !fileName || !fileMeta || !restoreButton) return;",
            "      const restoreButton = form.querySelector(\"[data-sg-full-restore-button]\");\n"
            "      const verifyButton = form.querySelector(\"[data-sg-full-verify-button]\");\n"
            "      if (!input || !fileName || !fileMeta || !restoreButton || !verifyButton) return;",
            "upload JavaScript selectors",
        )
        text = _replace_once(
            text,
            "        restoreButton.disabled = true;\n        form.classList.remove(\"has-file\");",
            "        restoreButton.disabled = true;\n        verifyButton.disabled = true;\n        form.classList.remove(\"has-file\");",
            "upload reset",
        )
        text = _replace_once(
            text,
            "        fileMeta.textContent = `${formatBytes(file.size)} · готов к восстановлению`;\n"
            "        restoreButton.disabled = false;",
            "        fileMeta.textContent = `${formatBytes(file.size)} · готов к проверке / восстановлению`;\n"
            "        restoreButton.disabled = false;\n"
            "        verifyButton.disabled = false;",
            "upload selected state",
        )

    # The same form owns the destructive Restore action and therefore carries
    # data-sg-confirm. Verification must not show that dialog. Set the shared
    # confirmation bypass immediately on the verify-button click; form submit
    # happens synchronously afterwards and base.html consumes/removes it.
    if "verifyButton.addEventListener(\"click\", () => {" not in text:
        text = _replace_once(
            text,
            "      const reset = () => {\n",
            "      verifyButton.addEventListener(\"click\", () => {\n"
            "        form.dataset.sgConfirmBypass = \"1\";\n"
            "        window.setTimeout(() => {\n"
            "          if (form.dataset.sgConfirmBypass === \"1\") delete form.dataset.sgConfirmBypass;\n"
            "        }, 0);\n"
            "      });\n\n"
            "      const reset = () => {\n",
            "verification confirmation bypass",
        )

    old_note = "Перед восстановлением автоматически создаётся страховочный Full Backup."
    new_note = "Проверка ничего не меняет. Перед восстановлением автоматически создаётся страховочный Full Backup."
    if old_note in text and new_note not in text:
        text = text.replace(old_note, new_note, 1)

    required = (
        VERIFY_MARKER,
        VERIFY_ACTION_ATTRS,
        "готов к проверке / восстановлению",
        "verifyButton.addEventListener(\"click\", () => {",
        "form.dataset.sgConfirmBypass = \"1\"",
        "'backup.full.verify': 'Проверен полный backup'",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError("Full Backup verify UI patch incomplete: " + ", ".join(missing))
    if "verify_full_backup_route" in text:
        raise RuntimeError("Full Backup verify UI still uses the obsolete second upload endpoint")
    return text


def patch_template(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    patched = patch_text(original)
    if patched == original:
        return False
    path.write_text(patched, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("/opt/sg-gateway/app/web/templates/maintenance.html")
    changed = patch_template(path)
    print(f"Full Backup verify UI: {'patched' if changed else 'already present'}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
