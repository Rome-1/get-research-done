from __future__ import annotations

from grd.core.public_surface_contract import load_public_surface_contract


def test_public_surface_contract_smoke_surfaces_current_resume_authority_phrase() -> None:
    contract = load_public_surface_contract()

    assert (
        contract.resume_authority.public_vocabulary_intro
        == "Canonical continuation fields define the public resume vocabulary"
    )


def test_public_surface_contract_smoke_keeps_bridge_commands_and_named_commands_aligned() -> None:
    contract = load_public_surface_contract()

    assert contract.local_cli_bridge.commands == contract.local_cli_bridge.named_commands.ordered()
    assert contract.local_cli_bridge.named_commands.help == "grd --help"
    assert contract.local_cli_bridge.named_commands.resume == "grd resume"
    assert contract.local_cli_bridge.install_local_example == "grd install <runtime> --local"
    assert contract.local_cli_bridge.doctor_local_command == "grd doctor --runtime <runtime> --local"
    assert contract.local_cli_bridge.doctor_global_command == "grd doctor --runtime <runtime> --global"
    assert (
        contract.local_cli_bridge.validate_command_context_command
        == "grd validate command-context grd:<name>"
    )
