# GPD to GRD Migration Guide

This guide covers migrating from **Get Physics Done (GPD)** to **Get Research Done (GRD)** -- the domain-agnostic successor.

## What Changed and Why

GPD was built specifically for physics research. GRD generalizes the same workflow engine to support any research domain (physics, machine learning, mechanistic interpretability, and custom domains) through a **domain pack** architecture.

Key changes:

- **Package rename**: `get-physics-done` is now `get-research-done`
- **Directory rename**: `.gpd/` project directories are now `.grd/`
- **Domain packs**: Physics conventions, protocols, and error catalogs are no longer hardcoded -- they ship as the built-in `physics` domain pack
- **Convention lock format**: Flat physics-specific fields are now stored in a unified `conventions` dict
- **Domain-agnostic prompts**: Agent prompts use `{GRD_DOMAIN}` placeholders resolved at runtime

## Automatic Migration

GRD handles several migration steps transparently when it encounters old-format data.

### ConventionLock Field Migration

The old GPD `ConventionLock` stored physics conventions as flat top-level fields:

```yaml
# Old GPD format
convention_lock:
  metric_signature: "(-,+,+,+)"
  fourier_convention: "particle-physics"
  custom_conventions:
    my_custom_field: "some value"
```

GRD automatically migrates this into the new unified `conventions` dict via `_migrate_legacy_format` in `ConventionLock`. When GRD loads a state file with the old format, it:

1. Moves all 18 legacy physics fields (`metric_signature`, `fourier_convention`, `natural_units`, `gauge_choice`, etc.) into `conventions`
2. Merges any `custom_conventions` dict entries into `conventions`
3. Preserves values from the explicit `conventions` dict if both old and new keys exist

The result:

```yaml
# New GRD format
convention_lock:
  conventions:
    metric_signature: "(-,+,+,+)"
    fourier_convention: "particle-physics"
    my_custom_field: "some value"
```

This migration happens at model validation time -- no manual intervention required.

### STATE.md Rendering Compatibility

The `render_state_md` function supports both the new `{"conventions": {...}}` nested format and the legacy flat format when generating STATE.md, including backward-compatible reading of `custom_conventions` dicts.

## Manual Steps

### 1. Install GRD

```bash
npx -y get-research-done
```

This replaces any prior `get-physics-done` installation.

### 2. Rename Project Directory

If your project has a `.gpd/` directory, rename it:

```bash
mv .gpd .grd
```

GRD looks for `.grd/` exclusively. The internal file structure (`config.json`, `state.json`, etc.) is unchanged.

### 3. Update Scripts and Aliases

Replace any references to `gpd` commands in your scripts, shell aliases, or CI pipelines:

| Old (GPD) | New (GRD) |
|-----------|-----------|
| `gpd init` | `grd init` |
| `gpd plan` | `grd plan` |
| `gpd verify` | `grd verify` |
| `.gpd/config.json` | `.grd/config.json` |

### 4. Set Your Domain (Optional)

GRD defaults to the `physics` domain. To use a different domain, set the environment variable:

```bash
export GRD_DOMAIN=machine-learning   # or: physics, mech-interp
```

### 5. Review Convention Lock

If you have an existing `STATE.md` or state JSON, verify that your convention lock rendered correctly after the migration. The conventions should appear under the unified format.

## Domain Packs

### How They Work

A domain pack is a directory containing a `domain.yaml` manifest plus content directories for conventions, protocols, errors, verification rules, and subfield references.

Discovery order (last wins):
1. **Bundled packs** -- shipped with GRD at `src/grd/domains/<name>/`
2. **User packs** -- installed at `~/.grd/domains/<name>/`
3. **Project packs** -- local override at `.grd/domain/` (always wins)

### Built-in Domains

| Domain | Name | Description |
|--------|------|-------------|
| Physics | `physics` | QFT, condensed matter, GR, astrophysics, stat mech, AMO, nuclear/particle |
| Machine Learning | `machine-learning` | Supervised/unsupervised, deep learning, RL, NLP, CV, generative models |
| Mech Interp | `mech-interp` | Circuit discovery, SAEs, activation patching, causal tracing, probing |

### Domain-Specific Features

Each domain pack can define:

- **Convention fields** -- canonical conventions with labels, options, aliases, and criticality flags (`conventions/convention-fields.yaml`)
- **Subfield defaults** -- per-subfield convention presets (`conventions/subfield-defaults.yaml`)
- **Protocols** -- domain-specific research protocols
- **Error catalogs** -- verification error classes
- **Seed patterns** -- bootstrap patterns for new projects
- **Result metadata fields** -- domain-specific `--meta` keys for `grd result add/update`

### Creating a Custom Domain Pack

1. Copy the template: `src/grd/domains/_template/`
2. Edit `domain.yaml` with your domain's name, description, and content layout
3. Add convention field definitions in `conventions/convention-fields.yaml`
4. Add protocols, error catalogs, or subfield references as needed
5. Install to `~/.grd/domains/<name>/` or place in `.grd/domain/` for project-local use

Minimal `domain.yaml`:

```yaml
name: my-domain
display_name: My Research Domain
description: >
  Description of this domain and what it provides.
version: 1
conventions_file: conventions/convention-fields.yaml
content:
  protocols: protocols
  errors: errors
branding:
  tagline: "Your tagline here"
```

## Breaking Changes

1. **Directory name**: GRD does not auto-detect `.gpd/` directories. You must rename to `.grd/`.
2. **Package name**: The npm package is `get-research-done`, not `get-physics-done`.
3. **Convention lock structure**: Code that directly reads flat convention fields from `ConventionLock` must use `conventions["field_name"]` instead.
4. **Domain environment variable**: Physics-specific behavior now requires `GRD_DOMAIN=physics` (the default). Setting a different domain changes which conventions, protocols, and verification rules are active.
5. **Agent prompt placeholders**: Prompt templates use `{GRD_DOMAIN}` and `{GRD_INSTALL_DIR}` for domain-relative paths. Custom prompts referencing hardcoded physics paths need updating.

## FAQ

**Q: Will my existing physics projects work without changes?**
A: Almost. You need to rename `.gpd/` to `.grd/` and reinstall via `npx -y get-research-done`. Convention data migrates automatically.

**Q: Is the physics domain still the default?**
A: Yes. If `GRD_DOMAIN` is unset, GRD defaults to `physics`.

**Q: Can I use multiple domains in one project?**
A: No. Each project uses one domain pack. The project-local `.grd/domain/` override takes highest priority.

**Q: Where do I report issues with domain-specific content?**
A: Domain packs are versioned alongside GRD. File issues in the same repository.

**Q: How do I check which domains are available?**
A: Use `list_available_domains()` programmatically, or check `src/grd/domains/` for bundled packs and `~/.grd/domains/` for user-installed packs.
