from __future__ import annotations

from gpd.adapters import get_adapter, iter_runtime_descriptors
from gpd.core.onboarding_surfaces import (
    beginner_onboarding_hub_url,
    beginner_runtime_surface,
    beginner_runtime_surfaces,
    beginner_startup_ladder_text,
)


def test_beginner_onboarding_surface_contract_exposes_hub_and_ladder() -> None:
    assert beginner_onboarding_hub_url().endswith("/docs/README.md")
    assert beginner_startup_ladder_text() == "`help -> start -> tour -> new-project / map-research -> resume-work`"


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
