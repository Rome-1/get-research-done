# Changelog

All notable changes to Get Research Done (GRD) are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

- Regenerated infra descriptors for domain-agnostic refactor.

## [1.1.0] - 2026-03-20

### Added

- Domain-agnostic architecture: physics content migrated to pluggable domain packs.
- Three bundled domain packs: physics, machine-learning, and mechanistic-interpretability.
- Domain pack template for creating custom domains.
- Machine-learning domain pack with 12 conventions, 8 patterns, 4 protocols, and 4 error catalogs.
- Mechanistic-interpretability domain pack with 14 convention fields, protocols, error catalogs, and project templates.
- Domain-aware content resolution in MCP conventions server.
- DomainContext wired into CLI convention commands and convention operations.
- Domain pack schema hardened with content section and health check.
- Result metadata fields made domain-configurable via `--meta` CLI option.
- Bootstrap seed patterns migrated from core into domain pack YAML.
- Error class coverage definitions migrated from core into domain pack YAML.
- Multi-runtime support for Claude Code, Gemini CLI, Codex, and OpenCode.
- Structured research workflows for planning, execution, verification, and publication.

### Changed

- GPD renamed to GRD (Get Research Done) across entire codebase.
- ConventionLock simplified from 18 flat fields to single `conventions` dict with auto-migration.
- Agent prompts made domain-agnostic via `{GRD_DOMAIN}` placeholder (22 prompts, 9 workflows).
- Physics-specific language removed from generic core modules.

### Fixed

- `_make_lock` helper updated for ConventionLock `conventions` dict.
- Lazy-loading proxy backward compatibility (`__bool__`, `__add__`, `copy()`).
- Domain-aware MCP conventions server loader.
- ConventionLock `custom_conventions` attribute in parity tests.
- Metadata consistency test and convention review fixes.
- Path references and tests updated for physics domain migration.
- Domain pack merges reconciled with updated tests and mech-interp schema.
