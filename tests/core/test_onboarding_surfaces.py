from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gpd.adapters import get_adapter, iter_runtime_descriptors
from gpd.core import onboarding_surfaces as onboarding_surfaces_module
from gpd.core import public_surface_contract as public_surface_contract_module
from gpd.core.onboarding_surfaces import (
    beginner_onboarding_hub_url,
    beginner_runtime_surface,
    beginner_runtime_surfaces,
    beginner_startup_ladder_text,
)
from gpd.core.public_surface_contract import (
    beginner_onboarding_caveats,
    beginner_preflight_requirements,
    load_public_surface_contract,
    resume_authority_contract,
    resume_authority_fields,
)
from tests import doc_surface_contracts as doc_surface_contracts_module


def _load_public_surface_contract_with_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    class _FakeFiles:
        def __init__(self, contract_path: Path) -> None:
            self._contract_path = contract_path

        def joinpath(self, name: str) -> Path:
            assert name == "public_surface_contract.json"
            return self._contract_path

    contract_path = tmp_path / "public_surface_contract.json"
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(public_surface_contract_module, "files", lambda package: _FakeFiles(contract_path))
    load_public_surface_contract.cache_clear()


def test_beginner_onboarding_surface_contract_exposes_hub_and_ladder() -> None:
    assert beginner_onboarding_hub_url().endswith("/docs/README.md")
    assert beginner_startup_ladder_text() == "`help -> start -> tour -> new-project / map-research -> resume-work`"
    assert beginner_preflight_requirements() == (
        "One supported runtime is already installed and can open from your normal terminal.",
        "Node.js 20+ is available in that same terminal.",
        "Python 3.11+ with the standard `venv` module is available there too.",
    )
    assert beginner_onboarding_caveats() == (
        "GPD is not a standalone app.",
        "GPD does not install your runtime for you.",
        "GPD does not include model access, billing, or API credits.",
        "This hub is the beginner path, not the full reference.",
    )


def test_beginner_startup_ladder_stays_separate_from_deeper_recovery_follow_ups() -> None:
    startup_ladder = beginner_startup_ladder_text()

    assert startup_ladder.endswith("resume-work`")
    assert "suggest-next" not in startup_ladder
    assert "pause-work" not in startup_ladder
    assert "Node" not in startup_ladder
    assert "Python" not in startup_ladder
    assert "--local" not in startup_ladder
    assert "standalone" not in startup_ladder
    assert "billing" not in startup_ladder


def test_beginner_runtime_surfaces_follow_runtime_catalog() -> None:
    surfaces = beginner_runtime_surfaces()
    descriptors = iter_runtime_descriptors()

    assert tuple(surface.runtime_name for surface in surfaces) == tuple(
        descriptor.runtime_name for descriptor in descriptors
    )

    for surface in surfaces:
        adapter = get_adapter(surface.runtime_name)
        assert surface.display_name == adapter.display_name
        assert surface.launch_command == adapter.launch_command
        assert surface.help_command == adapter.help_command
        assert surface.start_command == adapter.format_command("start")
        assert surface.tour_command == adapter.format_command("tour")
        assert surface.new_project_command == adapter.new_project_command
        assert surface.new_project_minimal_command == f"{adapter.new_project_command} --minimal"
        assert surface.map_research_command == adapter.map_research_command
        assert surface.resume_work_command == adapter.format_command("resume-work")
        assert surface.settings_command == adapter.format_command("settings")


def test_beginner_runtime_surface_single_lookup_matches_bulk_surface() -> None:
    for surface in beginner_runtime_surfaces():
        assert beginner_runtime_surface(surface.runtime_name) == surface


def test_beginner_runtime_surface_single_lookup_uses_adapter_descriptor_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_name = iter_runtime_descriptors()[0].runtime_name

    def _boom() -> tuple[object, ...]:
        raise AssertionError("single runtime lookup should not scan the runtime catalog")

    monkeypatch.setattr(onboarding_surfaces_module, "iter_runtime_descriptors", _boom)

    surface = onboarding_surfaces_module.beginner_runtime_surface(runtime_name)
    adapter = get_adapter(runtime_name)

    assert surface.display_name == adapter.display_name
    assert surface.install_flag == adapter.install_flag
    assert surface.settings_command == adapter.format_command("settings")


def test_resume_authority_contract_exposes_full_validated_surface() -> None:
    contract = resume_authority_contract()

    assert contract.public_vocabulary_intro == "Public resume vocabulary centers on canonical continuation fields"
    assert contract.public_fields == resume_authority_fields()
    assert contract.top_level_boundary_phrase == "public top-level resume vocabulary only"
    assert not hasattr(contract, "compat_surface")
    assert not hasattr(contract, "session_mirror")
    assert not hasattr(contract, "compatibility_phrase")


def test_public_surface_contract_loader_tolerates_additive_keys(monkeypatch, tmp_path: Path) -> None:
    canonical_path = Path(__file__).resolve().parents[2] / "src" / "gpd" / "core" / "public_surface_contract.json"
    canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    additive_payload = copy.deepcopy(canonical_payload)
    additive_payload["legacy_note"] = "unexpected"
    additive_payload["beginner_onboarding"]["legacy_note"] = "unexpected"
    additive_payload["resume_authority"]["legacy_note"] = "unexpected"
    additive_payload["recovery_ladder"]["legacy_note"] = "unexpected"

    _load_public_surface_contract_with_payload(monkeypatch, tmp_path, additive_payload)
    contract = load_public_surface_contract()

    assert contract.beginner_onboarding.hub_url == canonical_payload["beginner_onboarding"]["hub_url"]
    assert contract.resume_authority.public_fields == tuple(canonical_payload["resume_authority"]["public_fields"])
    assert contract.recovery_ladder.title == canonical_payload["recovery_ladder"]["title"]
    load_public_surface_contract.cache_clear()


def test_public_surface_contract_loader_normalizes_whitespace_and_dedupes_lists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    canonical_path = Path(__file__).resolve().parents[2] / "src" / "gpd" / "core" / "public_surface_contract.json"
    canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    noisy_payload = copy.deepcopy(canonical_payload)

    noisy_payload["beginner_onboarding"]["hub_url"] = f"  {canonical_payload['beginner_onboarding']['hub_url']}  "
    noisy_payload["beginner_onboarding"]["startup_ladder"] = [
        f"  {canonical_payload['beginner_onboarding']['startup_ladder'][0]}  ",
        *canonical_payload["beginner_onboarding"]["startup_ladder"][1:],
        canonical_payload["beginner_onboarding"]["startup_ladder"][1],
    ]
    noisy_payload["local_cli_bridge"]["commands"] = [
        f"  {canonical_payload['local_cli_bridge']['commands'][0]}  ",
        *canonical_payload["local_cli_bridge"]["commands"][1:],
        canonical_payload["local_cli_bridge"]["commands"][0],
    ]
    noisy_payload["post_start_settings"]["primary_sentence"] = (
        f"  {canonical_payload['post_start_settings']['primary_sentence']}  "
    )
    noisy_payload["resume_authority"]["public_fields"] = [
        canonical_payload["resume_authority"]["public_fields"][0],
        f"  {canonical_payload['resume_authority']['public_fields'][1]}  ",
        *canonical_payload["resume_authority"]["public_fields"][2:],
        canonical_payload["resume_authority"]["public_fields"][1],
    ]
    noisy_payload["recovery_ladder"]["title"] = f"  {canonical_payload['recovery_ladder']['title']}  "

    _load_public_surface_contract_with_payload(monkeypatch, tmp_path, noisy_payload)
    contract = load_public_surface_contract()

    assert contract.beginner_onboarding.hub_url == canonical_payload["beginner_onboarding"]["hub_url"]
    assert contract.beginner_onboarding.startup_ladder == tuple(canonical_payload["beginner_onboarding"]["startup_ladder"])
    assert contract.local_cli_bridge.commands == tuple(canonical_payload["local_cli_bridge"]["commands"])
    assert contract.post_start_settings.primary_sentence == canonical_payload["post_start_settings"]["primary_sentence"]
    assert contract.resume_authority.public_fields == tuple(canonical_payload["resume_authority"]["public_fields"])
    assert contract.recovery_ladder.title == canonical_payload["recovery_ladder"]["title"]
    load_public_surface_contract.cache_clear()


def test_public_surface_contract_loader_rejects_missing_required_fields(monkeypatch, tmp_path: Path) -> None:
    canonical_path = Path(__file__).resolve().parents[2] / "src" / "gpd" / "core" / "public_surface_contract.json"
    canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    missing_payload = copy.deepcopy(canonical_payload)
    del missing_payload["resume_authority"]["public_vocabulary_intro"]

    _load_public_surface_contract_with_payload(monkeypatch, tmp_path, missing_payload)
    with pytest.raises(ValueError, match=r"resume_authority is missing required key\(s\): public_vocabulary_intro"):
        load_public_surface_contract()

    load_public_surface_contract.cache_clear()


def test_public_surface_contract_loader_rejects_invalid_required_field_types(monkeypatch, tmp_path: Path) -> None:
    canonical_path = Path(__file__).resolve().parents[2] / "src" / "gpd" / "core" / "public_surface_contract.json"
    canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    invalid_payload = copy.deepcopy(canonical_payload)
    invalid_payload["resume_authority"]["public_fields"] = "unexpected"

    _load_public_surface_contract_with_payload(monkeypatch, tmp_path, invalid_payload)
    with pytest.raises(ValueError, match=r"resume_authority\.public_fields must be a non-empty list"):
        load_public_surface_contract()

    load_public_surface_contract.cache_clear()


def test_public_surface_contract_loader_rejects_boolean_schema_version(monkeypatch, tmp_path: Path) -> None:
    canonical_path = Path(__file__).resolve().parents[2] / "src" / "gpd" / "core" / "public_surface_contract.json"
    canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    canonical_payload["schema_version"] = True
    _load_public_surface_contract_with_payload(monkeypatch, tmp_path, canonical_payload)
    load_public_surface_contract.cache_clear()

    with pytest.raises(ValueError, match=r"Unsupported public surface contract schema_version: True"):
        load_public_surface_contract()

    load_public_surface_contract.cache_clear()


def test_doc_surface_contract_helpers_read_runtime_normalized_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = public_surface_contract_module.PublicSurfaceContract(
        beginner_onboarding=public_surface_contract_module.BeginnerOnboardingContract(
            hub_url="https://example.com/hub",
            preflight_requirements=("Preflight A",),
            caveats=("Caveat A",),
            startup_ladder=("help", "start"),
        ),
        local_cli_bridge=public_surface_contract_module.LocalCliBridgeContract(
            commands=("gpd --help",),
            terminal_phrase="in your normal terminal",
            purpose_phrase="workspace diagnostics",
        ),
        post_start_settings=public_surface_contract_module.PostStartSettingsContract(
            primary_sentence="Run settings after start.",
            default_sentence="Balanced defaults apply.",
        ),
        resume_authority=public_surface_contract_module.ResumeAuthorityContract(
            durable_authority_phrase="Durable authority phrase",
            public_vocabulary_intro="Public vocabulary intro",
            public_fields=("resume_file",),
            top_level_boundary_phrase="Top-level boundary phrase",
        ),
        recovery_ladder=public_surface_contract_module.RecoveryLadderContract(
            title="Recovery ladder title",
            local_snapshot_command="status",
            local_snapshot_phrase="local snapshot",
            cross_workspace_command="resume --recent",
            cross_workspace_phrase="pick another workspace",
            resume_phrase="continue with resume-work",
            next_phrase="check suggest-next",
            pause_phrase="fresh continuation breadcrumbs",
        ),
    )
    monkeypatch.setattr(doc_surface_contracts_module, "load_public_surface_contract", lambda: contract)
    doc_surface_contracts_module._public_surface_contract_payload.cache_clear()

    assert doc_surface_contracts_module.beginner_preflight_requirements() == ("Preflight A",)
    assert doc_surface_contracts_module.beginner_onboarding_caveats() == ("Caveat A",)
    assert doc_surface_contracts_module.beginner_startup_ladder_text() == "`help -> start`"
    assert doc_surface_contracts_module.resume_authority_public_vocabulary_intro() == "Public vocabulary intro"

    doc_surface_contracts_module._public_surface_contract_payload.cache_clear()
