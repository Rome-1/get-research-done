"""Structured public-surface contract for repeated onboarding and local CLI guidance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

__all__ = [
    "BeginnerOnboardingContract",
    "LocalCliBridgeContract",
    "PostStartSettingsContract",
    "PublicSurfaceContract",
    "RecoveryLadderContract",
    "beginner_onboarding_contract",
    "beginner_onboarding_caveats",
    "beginner_onboarding_hub_url",
    "beginner_preflight_requirements",
    "beginner_startup_ladder",
    "beginner_startup_ladder_text",
    "load_public_surface_contract",
    "local_cli_bridge_commands",
    "local_cli_bridge_contract",
    "local_cli_bridge_note",
    "post_start_settings_contract",
    "post_start_settings_note",
    "post_start_settings_recommendation",
    "recovery_ladder_contract",
    "recovery_ladder_note",
]


@dataclass(frozen=True, slots=True)
class BeginnerOnboardingContract:
    hub_url: str
    preflight_requirements: tuple[str, ...]
    caveats: tuple[str, ...]
    startup_ladder: tuple[str, ...]

    def render_startup_ladder(self) -> str:
        return "`" + " -> ".join(self.startup_ladder) + "`"


@dataclass(frozen=True, slots=True)
class LocalCliBridgeContract:
    commands: tuple[str, ...]
    terminal_phrase: str
    purpose_phrase: str

    def render_note(self) -> str:
        return (
            f"Use {_join_backticked_commands(self.commands)} {self.terminal_phrase} "
            f"when you want {self.purpose_phrase}."
        )


@dataclass(frozen=True, slots=True)
class PostStartSettingsContract:
    primary_sentence: str
    default_sentence: str

    def render_note(self) -> str:
        return f"{self.primary_sentence} {self.default_sentence}"


@dataclass(frozen=True, slots=True)
class RecoveryLadderContract:
    title: str
    local_snapshot_command: str
    local_snapshot_phrase: str
    cross_workspace_command: str
    cross_workspace_phrase: str
    resume_phrase: str
    next_phrase: str
    pause_phrase: str

    def render_note(
        self,
        *,
        resume_work_phrase: str,
        suggest_next_phrase: str,
        pause_work_phrase: str,
    ) -> str:
        return (
            f"{self.title}: use `{self.local_snapshot_command}` for {self.local_snapshot_phrase}. "
            f"If that is the wrong workspace, use `{self.cross_workspace_command}` to {self.cross_workspace_phrase}, "
            f"then {self.resume_phrase} with {resume_work_phrase}. After resuming, "
            f"{suggest_next_phrase} is {self.next_phrase}. Before stepping away mid-phase, "
            f"run {pause_work_phrase} so that ladder has {self.pause_phrase}."
        )


@dataclass(frozen=True, slots=True)
class PublicSurfaceContract:
    beginner_onboarding: BeginnerOnboardingContract
    local_cli_bridge: LocalCliBridgeContract
    post_start_settings: PostStartSettingsContract
    recovery_ladder: RecoveryLadderContract


def _join_backticked_commands(commands: tuple[str, ...]) -> str:
    rendered = tuple(f"`{command}`" for command in commands)
    if not rendered:
        raise ValueError("public surface contract requires at least one local CLI command")
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return f"{rendered[0]} and {rendered[1]}"
    return ", ".join(rendered[:-1]) + f", and {rendered[-1]}"


def _require_object(payload: object, *, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _require_string(payload: dict[str, object], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value


def _require_string_list(payload: dict[str, object], key: str, *, label: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}.{key} must be a non-empty list")
    commands: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}.{key} entries must be non-empty strings")
        commands.append(item)
    return tuple(commands)


@lru_cache(maxsize=1)
def load_public_surface_contract() -> PublicSurfaceContract:
    contract_path = files("gpd.core").joinpath("public_surface_contract.json")
    raw_payload = json.loads(contract_path.read_text(encoding="utf-8"))
    payload = _require_object(raw_payload, label="public_surface_contract")

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"Unsupported public surface contract schema_version: {schema_version!r}")

    beginner_payload = _require_object(payload.get("beginner_onboarding"), label="beginner_onboarding")
    bridge_payload = _require_object(payload.get("local_cli_bridge"), label="local_cli_bridge")
    settings_payload = _require_object(payload.get("post_start_settings"), label="post_start_settings")
    recovery_payload = _require_object(payload.get("recovery_ladder"), label="recovery_ladder")

    return PublicSurfaceContract(
        beginner_onboarding=BeginnerOnboardingContract(
            hub_url=_require_string(beginner_payload, "hub_url", label="beginner_onboarding"),
            preflight_requirements=_require_string_list(
                beginner_payload,
                "preflight_requirements",
                label="beginner_onboarding",
            ),
            caveats=_require_string_list(beginner_payload, "caveats", label="beginner_onboarding"),
            startup_ladder=_require_string_list(beginner_payload, "startup_ladder", label="beginner_onboarding"),
        ),
        local_cli_bridge=LocalCliBridgeContract(
            commands=_require_string_list(bridge_payload, "commands", label="local_cli_bridge"),
            terminal_phrase=_require_string(bridge_payload, "terminal_phrase", label="local_cli_bridge"),
            purpose_phrase=_require_string(bridge_payload, "purpose_phrase", label="local_cli_bridge"),
        ),
        post_start_settings=PostStartSettingsContract(
            primary_sentence=_require_string(
                settings_payload,
                "primary_sentence",
                label="post_start_settings",
            ),
            default_sentence=_require_string(
                settings_payload,
                "default_sentence",
                label="post_start_settings",
            ),
        ),
        recovery_ladder=RecoveryLadderContract(
            title=_require_string(recovery_payload, "title", label="recovery_ladder"),
            local_snapshot_command=_require_string(
                recovery_payload,
                "local_snapshot_command",
                label="recovery_ladder",
            ),
            local_snapshot_phrase=_require_string(
                recovery_payload,
                "local_snapshot_phrase",
                label="recovery_ladder",
            ),
            cross_workspace_command=_require_string(
                recovery_payload,
                "cross_workspace_command",
                label="recovery_ladder",
            ),
            cross_workspace_phrase=_require_string(
                recovery_payload,
                "cross_workspace_phrase",
                label="recovery_ladder",
            ),
            resume_phrase=_require_string(
                recovery_payload,
                "resume_phrase",
                label="recovery_ladder",
            ),
            next_phrase=_require_string(
                recovery_payload,
                "next_phrase",
                label="recovery_ladder",
            ),
            pause_phrase=_require_string(
                recovery_payload,
                "pause_phrase",
                label="recovery_ladder",
            ),
        ),
    )


def beginner_onboarding_contract() -> BeginnerOnboardingContract:
    return load_public_surface_contract().beginner_onboarding


def beginner_onboarding_hub_url() -> str:
    return beginner_onboarding_contract().hub_url


def beginner_preflight_requirements() -> tuple[str, ...]:
    return beginner_onboarding_contract().preflight_requirements


def beginner_onboarding_caveats() -> tuple[str, ...]:
    return beginner_onboarding_contract().caveats


def beginner_startup_ladder() -> tuple[str, ...]:
    return beginner_onboarding_contract().startup_ladder


def beginner_startup_ladder_text() -> str:
    return beginner_onboarding_contract().render_startup_ladder()


def local_cli_bridge_contract() -> LocalCliBridgeContract:
    return load_public_surface_contract().local_cli_bridge


def local_cli_bridge_commands() -> tuple[str, ...]:
    return local_cli_bridge_contract().commands


def local_cli_bridge_note() -> str:
    return local_cli_bridge_contract().render_note()


def post_start_settings_contract() -> PostStartSettingsContract:
    return load_public_surface_contract().post_start_settings


def post_start_settings_note() -> str:
    return post_start_settings_contract().primary_sentence


def post_start_settings_recommendation() -> str:
    return post_start_settings_contract().default_sentence


def recovery_ladder_contract() -> RecoveryLadderContract:
    return load_public_surface_contract().recovery_ladder


def recovery_ladder_note(
    *,
    resume_work_phrase: str,
    suggest_next_phrase: str,
    pause_work_phrase: str,
) -> str:
    return recovery_ladder_contract().render_note(
        resume_work_phrase=resume_work_phrase,
        suggest_next_phrase=suggest_next_phrase,
        pause_work_phrase=pause_work_phrase,
    )
