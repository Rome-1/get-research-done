from __future__ import annotations

from pathlib import Path

import pytest

from grd import registry
from grd.adapters.runtime_catalog import iter_runtime_descriptors
from grd.cli import _canonical_command_name
from grd.command_labels import (
    canonical_command_label,
    canonical_skill_label,
    command_slug_from_label,
    rewrite_runtime_command_surfaces,
    runtime_command_prefixes,
    runtime_public_command_prefixes,
    validated_public_command_prefix,
)
from grd.mcp.servers.skills_server import _canonicalize_command_surface


@pytest.fixture(autouse=True)
def _clean_registry_cache() -> None:
    registry.invalidate_cache()
    yield
    registry.invalidate_cache()


@pytest.fixture
def _registry_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    commands_dir = tmp_path / "commands"
    agents_dir = tmp_path / "agents"
    commands_dir.mkdir()
    agents_dir.mkdir()
    monkeypatch.setattr(registry, "COMMANDS_DIR", commands_dir)
    monkeypatch.setattr(registry, "AGENTS_DIR", agents_dir)
    registry.invalidate_cache()
    return commands_dir, agents_dir


def _command_label(prefix: str, slug: str) -> str:
    return f"{prefix}{slug}"


def test_runtime_command_prefixes_are_derived_from_the_runtime_catalog() -> None:
    expected_prefixes: list[str] = []
    seen: set[str] = set()
    for descriptor in iter_runtime_descriptors():
        for candidate in (
            descriptor.command_prefix,
            descriptor.command_prefix[1:] if descriptor.command_prefix[:1] in {"/", "$"} else None,
        ):
            if candidate and candidate not in seen:
                seen.add(candidate)
                expected_prefixes.append(candidate)
    for canonical_prefix in ("grd:", "grd-"):
        if canonical_prefix not in seen:
            seen.add(canonical_prefix)
            expected_prefixes.append(canonical_prefix)
    expected_prefixes.sort(key=len, reverse=True)

    assert runtime_command_prefixes() == tuple(expected_prefixes)


def test_runtime_public_command_prefixes_are_derived_from_the_runtime_catalog() -> None:
    expected_prefixes = []
    seen: set[str] = set()
    for descriptor in iter_runtime_descriptors():
        prefix = validated_public_command_prefix(descriptor)
        if prefix in seen:
            continue
        seen.add(prefix)
        expected_prefixes.append(prefix)
    expected_prefixes.sort(key=len, reverse=True)

    assert runtime_public_command_prefixes() == tuple(expected_prefixes)
    assert "/grd-" in runtime_public_command_prefixes()


def test_validated_public_command_prefix_uses_descriptor_owned_surface() -> None:
    descriptor = iter_runtime_descriptors()[0]

    assert validated_public_command_prefix(descriptor) == descriptor.public_command_surface_prefix


@pytest.mark.parametrize("descriptor", iter_runtime_descriptors(), ids=lambda item: item.runtime_name)
def test_registry_accepts_runtime_native_command_labels(
    _registry_roots: tuple[Path, Path],
    descriptor: object,
) -> None:
    commands_dir, _ = _registry_roots
    (commands_dir / "execute-phase.md").write_text(
        "---\nname: grd:execute-phase\ndescription: Execute\n---\nExecute body.\n",
        encoding="utf-8",
    )

    command = registry.get_command(_command_label(descriptor.command_prefix, "execute-phase"))

    assert command.name == "grd:execute-phase"


@pytest.mark.parametrize("descriptor", iter_runtime_descriptors(), ids=lambda item: item.runtime_name)
def test_registry_accepts_runtime_native_skill_labels(
    _registry_roots: tuple[Path, Path],
    descriptor: object,
) -> None:
    commands_dir, _ = _registry_roots
    (commands_dir / "execute-phase.md").write_text(
        "---\nname: grd:execute-phase\ndescription: Execute\n---\nExecute body.\n",
        encoding="utf-8",
    )

    skill = registry.get_skill(_command_label(descriptor.command_prefix, "execute-phase"))

    assert skill.name == "grd-execute-phase"


@pytest.mark.parametrize("descriptor", iter_runtime_descriptors(), ids=lambda item: item.runtime_name)
def test_runtime_native_command_labels_canonicalize_across_shared_surfaces(descriptor: object) -> None:
    label = _command_label(descriptor.command_prefix, "execute-phase")

    assert canonical_command_label(label) == "grd:execute-phase"
    assert canonical_skill_label(label) == "grd-execute-phase"
    assert _canonical_command_name(label) == "grd:execute-phase"


@pytest.mark.parametrize("descriptor", iter_runtime_descriptors(), ids=lambda item: item.runtime_name)
def test_runtime_native_command_surfaces_rewrite_to_canonical_skill_labels(descriptor: object) -> None:
    content = (
        f"Run {_command_label(descriptor.command_prefix, 'execute-phase')} first.\n"
        f"Then try {_command_label(descriptor.command_prefix, 'help')}.\n"
    )

    rewritten = rewrite_runtime_command_surfaces(content, canonical="skill")

    assert "grd-execute-phase" in rewritten
    assert "grd-help" in rewritten
    assert _canonicalize_command_surface(content) == rewritten


@pytest.mark.parametrize("descriptor", iter_runtime_descriptors(), ids=lambda item: item.runtime_name)
def test_runtime_native_command_wildcard_surfaces_rewrite_to_canonical_skill_wildcard(descriptor: object) -> None:
    content = f"Use `{descriptor.command_prefix}*` to browse runtime commands.\n"

    assert _canonicalize_command_surface(content) == "Use `grd-*` to browse runtime commands.\n"


def test_runtime_command_surface_rewrite_does_not_mutate_markdown_paths() -> None:
    content = "Read /tmp/specs/grd-help.md and /tmp/agents/grd-executor.md before continuing."

    assert rewrite_runtime_command_surfaces(content, canonical="skill") == content


def test_runtime_command_surface_rewrite_skips_urls_and_paths_but_keeps_examples() -> None:
    content = (
        "Use /grd:help when you want a real command example.\n"
        "See https://example.test//grd:help and /tmp//grd:help.txt and /tmp/$grd-help.txt.\n"
        "Keep ./docs/grd-help.md and foo$grd-help/bar untouched.\n"
    )

    rewritten = rewrite_runtime_command_surfaces(content, canonical="skill")

    assert "Use grd-help when you want a real command example." in rewritten
    assert "https://example.test//grd:help" in rewritten
    assert "/tmp//grd:help.txt" in rewritten
    assert "/tmp/$grd-help.txt" in rewritten
    assert "./docs/grd-help.md" in rewritten
    assert "foo$grd-help/bar" in rewritten


def test_foreign_bare_slash_command_is_not_canonicalized_into_gpd() -> None:
    assert command_slug_from_label("/help") == "/help"
    assert canonical_command_label("/help") == "grd:/help"
    assert canonical_skill_label("/help") == "grd-/help"
