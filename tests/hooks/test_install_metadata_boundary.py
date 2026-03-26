"""Targeted regressions for install-metadata runtime boundary hardening."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from gpd.hooks.install_context import detect_self_owned_install
from gpd.hooks.install_metadata import (
    config_dir_has_complete_install,
    installed_update_command,
    load_install_manifest_runtime_status,
    load_install_manifest_state,
)
from gpd.hooks.runtime_detect import _manifest_runtime_status as runtime_detect_manifest_runtime_status


def _seed_anonymous_install_tree(config_dir: Path, *, hook_filename: str) -> Path:
    """Create an install tree that only carries anonymous legacy ownership hints."""
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "get-physics-done").mkdir(parents=True, exist_ok=True)
    (config_dir / "gpd-file-manifest.json").write_text(
        json.dumps(
            {
                "install_scope": "local",
                "files": {
                    "skills/gpd-help/SKILL.md": "legacy-hint",
                },
            }
        ),
        encoding="utf-8",
    )

    hook_path = config_dir / "hooks" / hook_filename
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text("# hook\n", encoding="utf-8")
    return hook_path


@pytest.mark.parametrize(
    ("manifest_content", "expected_state", "expected_payload"),
    [
        (None, "missing", {}),
        (b"\xff", "corrupt", {}),
        ("[]", "invalid", {}),
        (json.dumps({"install_scope": "local", "runtime": "codex"}), "ok", {"install_scope": "local", "runtime": "codex"}),
    ],
)
def test_load_install_manifest_state_classifies_manifest_payloads(
    tmp_path: Path,
    manifest_content: bytes | str | None,
    expected_state: str,
    expected_payload: dict[str, object],
) -> None:
    config_dir = tmp_path / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config_dir / "gpd-file-manifest.json"
    if manifest_content is not None:
        if isinstance(manifest_content, bytes):
            manifest_path.write_bytes(manifest_content)
        else:
            manifest_path.write_text(manifest_content, encoding="utf-8")

    assert load_install_manifest_state(config_dir) == (expected_state, expected_payload)


@pytest.mark.parametrize(
    ("manifest_content", "expected_state", "expected_runtime"),
    [
        (None, "missing", None),
        (b"\xff", "corrupt", None),
        ("[]", "invalid", None),
        (json.dumps({"install_scope": "local"}), "missing_runtime", None),
        (json.dumps({"install_scope": "local", "runtime": 123}), "malformed_runtime", None),
        (json.dumps({"install_scope": "local", "runtime": "codex"}), "ok", "codex"),
    ],
)
def test_install_manifest_runtime_status_is_shared_across_surfaces(
    tmp_path: Path,
    manifest_content: bytes | str | None,
    expected_state: str,
    expected_runtime: str | None,
) -> None:
    config_dir = tmp_path / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config_dir / "gpd-file-manifest.json"
    if manifest_content is not None:
        if isinstance(manifest_content, bytes):
            manifest_path.write_bytes(manifest_content)
        else:
            manifest_path.write_text(manifest_content, encoding="utf-8")

    metadata_state, metadata_payload, metadata_runtime = load_install_manifest_runtime_status(config_dir)
    detect_state, detect_runtime = runtime_detect_manifest_runtime_status(config_dir)

    assert metadata_state == expected_state
    assert metadata_runtime == expected_runtime
    assert detect_state == expected_state
    assert detect_runtime == expected_runtime
    if expected_state in {"ok", "missing_runtime", "malformed_runtime"}:
        assert metadata_payload == json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        assert metadata_payload == {}


def test_runtime_less_manifest_tree_is_rejected_by_install_metadata(tmp_path: Path) -> None:
    config_dir = tmp_path / ".codex"
    _seed_anonymous_install_tree(config_dir, hook_filename="install_metadata.py")

    assert config_dir_has_complete_install(config_dir) is False
    assert installed_update_command(config_dir) is None


def test_non_utf8_manifest_tree_is_rejected_by_install_metadata(tmp_path: Path) -> None:
    config_dir = tmp_path / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "get-physics-done").mkdir(parents=True, exist_ok=True)
    (config_dir / "gpd-file-manifest.json").write_bytes(b"\xff")

    assert config_dir_has_complete_install(config_dir) is False
    assert installed_update_command(config_dir) is None


@pytest.mark.parametrize(
    ("hook_filename",),
    [
        ("check_update.py",),
        ("statusline.py",),
        ("notify.py",),
    ],
)
def test_hook_self_detection_rejects_runtime_less_manifest_tree(tmp_path: Path, hook_filename: str) -> None:
    config_dir = tmp_path / ".codex"
    hook_path = _seed_anonymous_install_tree(config_dir, hook_filename=hook_filename)

    assert detect_self_owned_install(hook_path) is None


@pytest.mark.parametrize(
    ("hook_filename",),
    [
        ("check_update.py",),
        ("statusline.py",),
        ("notify.py",),
    ],
)
def test_hook_self_detection_rejects_non_utf8_manifest_tree(tmp_path: Path, hook_filename: str) -> None:
    config_dir = tmp_path / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "get-physics-done").mkdir(parents=True, exist_ok=True)
    (config_dir / "gpd-file-manifest.json").write_bytes(b"\xff")
    hook_path = config_dir / "hooks" / hook_filename
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text("# hook\n", encoding="utf-8")

    assert detect_self_owned_install(hook_path) is None


def test_runtime_detect_uses_shared_manifest_scope_helper() -> None:
    import gpd.hooks.runtime_detect as runtime_detect

    source = inspect.getsource(runtime_detect)

    assert "install_scope_from_manifest" in source
    assert "_manifest_install_scope" not in source


def test_runtime_cli_uses_shared_manifest_runtime_helper() -> None:
    import gpd.runtime_cli as runtime_cli

    source = inspect.getsource(runtime_cli)

    assert "load_install_manifest_runtime_status" in source
    assert "def _manifest_runtime_status" not in source
