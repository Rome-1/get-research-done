# Get Research Done (GRD)

### AI copilot for structured research

<p align="center">
  <a href="https://github.com/Rome-1/get-research-done/actions/workflows/test.yml"><img alt="CI" src="https://github.com/Rome-1/get-research-done/actions/workflows/test.yml/badge.svg"></a>
  <a href="https://github.com/Rome-1/get-research-done/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-d4d4d8?style=flat&labelColor=3f3f46"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-ffd43b?style=flat&labelColor=3776ab&logo=python&logoColor=white"></a>
  <a href="https://www.npmjs.com/package/get-research-done"><img alt="npm" src="https://img.shields.io/npm/v/get-research-done?style=flat&logo=npm&logoColor=white&labelColor=1f1f1f&color=cb3837"></a>
</p>

<p align="center">
  <a href="#supported-runtimes"><img alt="Claude Code supported" src="https://img.shields.io/badge/Claude%20Code-supported-d97757?style=flat&labelColor=141413&logo=claude&logoColor=faf9f5"></a>
  <a href="#supported-runtimes"><img alt="Codex supported" src="https://img.shields.io/badge/Codex-supported-f5f5f5?style=flat&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyBpZD0iTGF5ZXJfMSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2ZXJzaW9uPSIxLjEiIHZpZXdCb3g9IjAgMCAxNTguNzEyOCAxNTcuMjk2Ij4KICA8IS0tIEdlbmVyYXRvcjogQWRvYmUgSWxsdXN0cmF0b3IgMjkuMi4xLCBTVkcgRXhwb3J0IFBsdWctSW4gLiBTVkcgVmVyc2lvbjogMi4xLjAgQnVpbGQgMTE2KSAgLS0%2BCiAgPHBhdGggZmlsbD0iI0ZGRkZGRiIgZD0iTTYwLjg3MzQsNTcuMjU1NnYtMTQuOTQzMmMwLTEuMjU4Ni40NzIyLTIuMjAyOSwxLjU3MjgtMi44MzE0bDMwLjA0NDMtMTcuMzAyM2M0LjA4OTktMi4zNTkzLDguOTY2Mi0zLjQ1OTksMTMuOTk4OC0zLjQ1OTksMTguODc1OSwwLDMwLjgzMDcsMTQuNjI4OSwzMC44MzA3LDMwLjIwMDYsMCwxLjEwMDcsMCwyLjM1OTMtLjE1OCwzLjYxNzhsLTMxLjE0NDYtMTguMjQ2N2MtMS44ODcyLTEuMTAwNi0zLjc3NTQtMS4xMDA2LTUuNjYyOSwwbC0zOS40ODEyLDIyLjk2NTFaTTEzMS4wMjc2LDExNS40NTYxdi0zNS43MDc0YzAtMi4yMDI4LS45NDQ2LTMuNzc1Ni0yLjgzMTgtNC44NzYzbC0zOS40ODEtMjIuOTY1MSwxMi44OTgyLTcuMzkzNGMxLjEwMDctLjYyODUsMi4wNDUzLS42Mjg1LDMuMTQ1OCwwbDMwLjA0NDEsMTcuMzAyNGM4LjY1MjMsNS4wMzQxLDE0LjQ3MDgsMTUuNzI5NiwxNC40NzA4LDI2LjExMDcsMCwxMS45NTM5LTcuMDc2OSwyMi45NjUtMTguMjQ2MSwyNy41Mjd2LjAwMjFaTTUxLjU5Myw4My45OTY0bC0xMi44OTgyLTcuNTQ5N2MtMS4xMDA3LS42Mjg1LTEuNTcyOC0xLjU3MjgtMS41NzI4LTIuODMxNHYtMzQuNjA0OGMwLTE2LjgzMDMsMTIuODk4Mi0yOS41NzIyLDMwLjM1ODUtMjkuNTcyMiw2LjYwNywwLDEyLjc0MDMsMi4yMDI5LDE3LjkzMjQsNi4xMzQ5bC0zMC45ODcsMTcuOTMyNGMtMS44ODcxLDEuMTAwNy0yLjgzMTQsMi42NzM1LTIuODMxNCw0Ljg3NjR2NDUuNjE1OWwtLjAwMTQtLjAwMTVaTTc5LjM1NjIsMTAwLjA0MDNsLTE4LjQ4MjktMTAuMzgxMXYtMjIuMDIwOWwxOC40ODI5LTEwLjM4MTEsMTguNDgxMiwxMC4zODExdjIyLjAyMDlsLTE4LjQ4MTIsMTAuMzgxMVpNOTEuMjMxOSwxNDcuODU5MWMtNi42MDcsMC0xMi43NDAzLTIuMjAzMS0xNy45MzI0LTYuMTM0NGwzMC45ODY2LTE3LjkzMzNjMS44ODcyLTEuMTAwNSwyLjgzMTgtMi42NzI4LDIuODMxOC00Ljg3NTl2LTQ1LjYxNmwxMy4wNTY0LDcuNTQ5OGMxLjEwMDUuNjI4NSwxLjU3MjMsMS41NzI4LDEuNTcyMywyLjgzMTR2MzQuNjA1MWMwLDE2LjgyOTctMTMuMDU2NCwyOS41NzIzLTMwLjUxNDcsMjkuNTcyM3YuMDAxWk01My45NTIyLDExMi43ODIybC0zMC4wNDQzLTE3LjMwMjRjLTguNjUyLTUuMDM0My0xNC40NzEtMTUuNzI5Ni0xNC40NzEtMjYuMTEwNywwLTEyLjExMTksNy4yMzU2LTIyLjk2NTIsMTguNDAzLTI3LjUyNzJ2MzUuODYzNGMwLDIuMjAyOC45NDQzLDMuNzc1NiwyLjgzMTQsNC44NzYzbDM5LjMyNDgsMjIuODA2OC0xMi44OTgyLDcuMzkzOGMtMS4xMDA3LjYyODctMi4wNDUuNjI4Ny0zLjE0NTYsMFpNNTIuMjIyOSwxMzguNTc5MWMtMTcuNzc0NSwwLTMwLjgzMDYtMTMuMzcxMy0zMC44MzA2LTI5Ljg4NzEsMC0xLjI1ODUuMTU3OC0yLjUxNjkuMzE0My0zLjc3NTRsMzAuOTg3LDE3LjkzMjNjMS44ODcxLDEuMTAwNSwzLjc3NTcsMS4xMDA1LDUuNjYyOCwwbDM5LjQ4MTEtMjIuODA3djE0Ljk0MzVjMCwxLjI1ODUtLjQ3MjEsMi4yMDIxLTEuNTcyOCwyLjgzMDhsLTMwLjA0NDMsMTcuMzAyNWMtNC4wODk4LDIuMzU5LTguOTY2MiwzLjQ2MDUtMTMuOTk4OSwzLjQ2MDVoLjAwMTRaTTkxLjIzMTksMTU3LjI5NmMxOS4wMzI3LDAsMzQuOTE4OC0xMy41MjcyLDM4LjUzODMtMzEuNDU5NCwxNy42MTY0LTQuNTYyLDI4Ljk0MjUtMjEuMDc3OSwyOC45NDI1LTM3LjkwOCwwLTExLjAxMTItNC43MTktMjEuNzA2Ni0xMy4yMTMzLTI5LjQxNDMuNzg2Ny0zLjMwMzUsMS4yNTk1LTYuNjA3LDEuMjU5NS05LjkwOSwwLTIyLjQ5MjktMTguMjQ3MS0zOS4zMjQ3LTM5LjMyNTEtMzkuMzI0Ny00LjI0NjEsMC04LjMzNjMuNjI4NS0xMi40MjYyLDIuMDQ1LTcuMDc5Mi02LjkyMTMtMTYuODMxOC0xMS4zMjU0LTI3LjUyNzEtMTEuMzI1NC0xOS4wMzMxLDAtMzQuOTE5MSwxMy41MjY4LTM4LjUzODQsMzEuNDU5MUMxMS4zMjU1LDM2LjAyMTIsMCw1Mi41MzczLDAsNjkuMzY3NWMwLDExLjAxMTIsNC43MTg0LDIxLjcwNjUsMTMuMjEyNSwyOS40MTQyLS43ODY1LDMuMzAzNS0xLjI1ODYsNi42MDY3LTEuMjU4Niw5LjkwOTIsMCwyMi40OTIzLDE4LjI0NjYsMzkuMzI0MSwzOS4zMjQ4LDM5LjMyNDEsNC4yNDYyLDAsOC4zMzYyLS42Mjc3LDEyLjQyNi0yLjA0NDEsNy4wNzc2LDYuOTIxLDE2LjgzMDIsMTEuMzI1MSwyNy41MjcxLDExLjMyNTFaIi8%2BCjwvc3ZnPg%3D%3D"></a>
  <a href="#supported-runtimes"><img alt="Gemini CLI supported" src="https://img.shields.io/badge/Gemini%20CLI-supported-4285f4?style=flat&labelColor=202124&logo=googlegemini&logoColor=8e75b2"></a>
  <a href="#supported-runtimes"><img alt="OpenCode supported" src="https://img.shields.io/badge/OpenCode-supported-cfcecd?style=flat&labelColor=565656&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAABzUlEQVR4AeycQQrCQBAEF1%2Bg6J%2F0o5LPCXmCnnNx0E2nNqGEPciw024VffV0PZ%2FfHo7BqflBCSgAxd%2BaAhQAE4DjbYACYAJwvA1QAEwAjrcBCgAIDBRpA2AZClAATACOtwEKgAnA8TZAATABOD7egNc8tz2ftJ%2B4gPQD9r5fAbDBDQXALx00XgGwGAUoACYAx9sABcAE4HgboACYABxvAxSwJHC7XFryLNP4bzYg7KBar4CKUHiugDDgar0CKkLhuQLCgKv1CqgIhecKCAOu1iugIhSeKyAMuFqvgIpQeK6AMOBq%2FXAC7o9H6z5fdlRAtp4PJ2BrAHSeAmADClAATACOtwEKgAnA8TZAATABON4GKAAmAMev2AD4JTuNVwAsTgEKgAnA8TZAATABON4GKAAmAMfbAAXABOB4G9ApoPe6AnoJdt5XQCfA3uvDCXhOU0ueXmBr3x9OwNoPHH2fAmBDClAATACOtwEKgAnA8TZAAX8QONAVGwDLVIACYAJwfLwByf%2F%2B2WJ32k9cQPoBe9%2BvANigAhQAE4DjbYACYAJw%2FA8NgH%2FpQeMVAItVgAJgAnC8DVAATACOtwEKgAnA8TZAATABON4GFALS4w8AAAD%2F%2Fx7wkLQAAAAGSURBVAMAKj5LkLSa6SQAAAAASUVORK5CYII%3D"></a>
</p>

Get Research Done is an open-source AI copilot for structured research — a generalization of [Get Physics Done](https://github.com/psi-oss/get-physics-done) that works across any scientific or technical domain. GRD helps turn a research question into a rigorous workflow: scope the problem, plan the work, derive results, verify them, and package the output.

GRD started in physics and is built to go further. Biology, chemistry, ML, economics, engineering — if the domain has hypotheses, evidence, and conclusions, GRD is designed to support it. Contributions that extend GRD to new domains, runtimes, or verification methods are actively welcome, from humans and agents alike.

https://github.com/user-attachments/assets/e79f8153-c0bd-484f-b69e-da8f142649e0

[Quick Start](#quick-start) · [Supported Runtimes](#supported-runtimes) · [Workflow](#what-grd-does) · [Commands](#key-in-runtime-commands) · [Models](#optional-model-profiles-and-tier-overrides) · [Advanced CLI](#advanced-cli-utilities) · [System Requirements](#system-requirements)

## Who This Is For

GRD is for hard research problems that cannot be handled reliably with manual prompting.

It is designed for long-horizon projects that require rigorous verification, structured research memory, multi-step analytical work, complex numerical studies, and manuscript writing or review.

We welcome contributions via GitHub issues or pull requests — domain extensions, new runtime integrations, verification methods, and everything in between. Human contributors and AI agents both welcome. If GRD is useful in your work, star the repo and share it with collaborators who might benefit.

### Two interfaces

GRD has two command surfaces:

- **In-runtime commands** (primary) — slash commands inside your AI runtime (Claude Code, Gemini CLI, Codex, OpenCode). Example: `/grd:new-project`, `/grd:plan-phase`. These drive the research workflow.
- **`grd` CLI** (standalone terminal tool) — for validation, inspection, and configuration outside the runtime. Example: `grd health`, `grd search`, `grd domain list`.

Most research work happens through in-runtime commands. The standalone CLI is for diagnostics, querying, and project management.

## Quick Start

Install GRD:

```bash
npx get-research-done
```

`help -> start -> tour -> new-project / map-research -> resume-work`

The installer adds GRD to your runtime config, but it does not launch the runtime for you.

1. Open your chosen runtime from your normal system terminal (`claude` for Claude Code, `gemini` for Gemini CLI, `codex` for Codex, `opencode` for OpenCode).
2. Run its help command first: Claude Code / Gemini CLI use `/grd:help`, Codex uses `$grd-help`, and OpenCode uses `/grd-help`.
3. Start with `new-project` for a fresh research project or `map-research` for an existing folder or project.

- From inside the folder where your project should live, install GPD with the matching `npx -y get-physics-done` bootstrap command from [Start Here](#start-here), then launch `claude`, `codex`, `gemini`, or `opencode`.
- Run the matching GPD help command shown in [Supported Runtimes](#supported-runtimes).
- Then use `start` if you are not sure what fits this folder, `tour` for a read-only walkthrough, `new-project --minimal` for new work, `map-research` for existing work, or `resume-work` when you return later.
- Treat the new-work choice as distinct from the existing-work choice; pick one, then follow it through.

The bootstrap installer requires Node.js 20+, Python 3.11+ with `venv`, and one supported runtime (`claude`, `gemini`, `codex`, or `opencode`).

If the install worked, both of these should be true:

1. `gpd --help` works in your normal terminal.
2. Your runtime-specific GPD help command works inside the runtime.

Then choose the path that matches your starting point:

| Starting point | First command | What it's for |
|----------------|---------------|----------------|
| New research project | `new-project` | Start a fresh GRD research workflow. |
| Existing research folder or codebase | `map-research` | Map existing work before planning. |
| Configure workflow and model defaults | `settings` | Set workflow toggles, tier models, and research preferences. |

Use the runtime-specific command syntax shown in [Supported Runtimes](#supported-runtimes), for example `/grd:settings` or `/grd:set-profile review`.

`gpd resume` is the normal-terminal recovery step; `resume-work` is the in-runtime continue command after the right folder is open.

After resuming, the runtime `suggest-next` command is the fastest post-resume next command when you only need the next action.

<details>
<summary><strong>Optional Terminal-Side Readiness And Troubleshooting Reference</strong></summary>

Use this when you want to verify install health, unattended readiness, paper-toolchain prerequisites, or local CLI surfaces from your normal terminal. If you want the full beginner path, stay with the onboarding hub and your selected OS/runtime guides.

**Bootstrap hard blockers**

- `node` / `npx` work in your normal system terminal
- Python 3.11+ with the standard `venv` module is available in that same terminal
- Your selected runtime is already installed and launchable there (`claude`, `gemini`, `codex`, or `opencode`)

If any of those fail, fix them before troubleshooting GPD itself. These are bootstrap prerequisites for the matching installer command, not a claim that every local `gpd ...` command rechecks them.

**Advisories**

- Choose `--local` or `--global` explicitly if you do not want the installer's default path selection
- Runtime permissions are runtime-owned permission alignment only; use the guided checks after startup to decide whether the runtime is ready.
- Use your runtime-specific `settings` command after the first successful launch as the guided path for unattended configuration. Balanced (`balanced`) is the recommended unattended default.
- For the broader terminal-side diagnostics, readiness, recovery, visibility, cost, and preset surface, start with `gpd --help` from your normal terminal.
- Use `gpd validate unattended-readiness --runtime <runtime> --autonomy balanced` when you want a terminal-side unattended or overnight verdict.
- If you plan paper/manuscript work later, use `gpd doctor --runtime <runtime> --local` for the project-local target or `gpd doctor --runtime <runtime> --global` for the global target first. For the fuller preset catalog, shared Wolfram integration details, and plan-preflight boundaries, use `gpd presets list`, `gpd integrations status wolfram`, and `gpd validate plan-preflight <PLAN.md>` from your normal terminal.
- Provider authentication is checked manually in the runtime itself; GPD will point this out, but it does not hard-block installation readiness on it
- Use `--upgrade` only when you intentionally want the latest unreleased GitHub `main` snapshot

**Quick verification path**

1. Install with an explicit runtime when possible, for example use the matching bootstrap command with `--<runtime-flag> --local`.
2. From the same terminal, run `gpd doctor --runtime <runtime> --local` and `gpd --help`. Add `--live-executable-probes` if you also want cheap local executable probes such as `pdflatex --version` or `wolframscript -version`. Here, `gpd doctor --runtime ...` is a runtime-readiness check for the selected runtime target. If you plan to use the paper/manuscript workflow preset later, treat the `Workflow Presets` and `LaTeX Toolchain` rows in this doctor report as paper-toolchain readiness signals for local smoke checks; `write-paper` can still proceed degraded, but `paper-build` is the build truth.
3. Launch your selected runtime and run its GPD help command (`/gpd:help`, `$gpd-help`, or `/gpd-help`).
4. If you want unattended execution, use your runtime-specific `settings` command as the guided configuration path and keep autonomy at Balanced (`balanced`) unless you intentionally want a more hands-off posture.
5. Run `gpd permissions status --runtime <runtime> --autonomy balanced` for the read-only runtime-owned permission snapshot, then run `gpd validate unattended-readiness --runtime <runtime> --autonomy balanced`. If it returns `not-ready`, run `gpd permissions sync --runtime <runtime> --autonomy balanced`; if it returns `relaunch-required`, exit and relaunch the selected runtime before treating unattended use as ready.
6. If those checks pass, continue with the runtime-specific `new-project`, `new-project --minimal`, `resume-work`, or `map-research` command.

**Troubleshooting**

- If the bootstrap installer fails before either `gpd doctor --runtime <runtime> --local` or `gpd doctor --runtime <runtime> --global` can run, fix Node / Python / `venv` bootstrap prerequisites first.
- If the matching `gpd doctor --runtime <runtime> --local` or `gpd doctor --runtime <runtime> --global` command fails, fix the selected runtime's launcher / target / runtime-readiness issue first.
- If that matching doctor command only warns about `Workflow Presets` or `LaTeX Toolchain`, the base install can still be fine; treat that as degraded readiness for `write-paper` and local smoke checks rather than a full install blocker. Use `gpd paper-build` to judge whether the manuscript scaffold is buildable.
- If the runtime launches but GPD commands are missing, rerun the installer with an explicit runtime and explicit scope from your normal system terminal.
- If you want the read-only runtime-owned permission snapshot first, run `gpd permissions status --runtime <runtime> --autonomy balanced`. If `gpd validate unattended-readiness --runtime <runtime> --autonomy balanced` returns `not-ready`, run `gpd permissions sync --runtime <runtime> --autonomy balanced` and check again; if it returns `relaunch-required`, exit and relaunch the runtime before unattended use.
- If the runtime itself cannot launch or is not authenticated, fix the runtime/provider setup outside GPD before retrying the GPD install.

</details>

Typical new-project workflow:

`/grd:new-project -> /grd:discuss-phase 1 -> /grd:plan-phase 1 -> /grd:execute-phase 1 -> /grd:verify-work 1`

<details>
<summary><strong>Install options</strong></summary>

| Flag | Meaning |
|------|---------|
| `--claude`, `--codex`, `--gemini`, `--opencode` | Select one runtime. `--claude-code` and `--gemini-cli` also work. |
| `--all` | Select all supported runtimes. |
| `--local`, `-l` | Use the current project only. |
| `--global`, `-g` | Use the global runtime config dir. |
| `--uninstall` | Uninstall from the selected runtime config instead of installing. |
| `--reinstall` | Reinstall the matching tagged GitHub source into `~/.grd/venv`. |
| `--upgrade` | Upgrade `~/.grd/venv` from the latest GitHub `main` source. |
| `--target-dir <path>` | Override the runtime config directory; defaults to local scope unless the path resolves to that runtime's canonical global config dir. |
| `--force-statusline` | Replace an existing runtime statusline during install. |
| `--help`, `-h` | Show bootstrap help. |

Ordinary installs stay pinned to the matching tagged release. Use `--upgrade` only when you intentionally want the latest unreleased `main` source.

Install the unreleased GitHub `main` snapshot explicitly:

```bash
npx -y github:psi-oss/get-research-done --upgrade
```

</details>

## Supported Runtimes

GRD currently installs into four AI runtimes. To preselect one during install, use the matching `npx` flag, or use `--all` to install everything in one pass:

| Runtime | `npx` flag | Help command | Start command |
|---------|------------|--------------|---------------|
| Claude Code | `--claude` | `/grd:help` | `/grd:new-project` |
| Codex | `--codex` | `$grd-help` | `$grd-new-project` |
| Gemini CLI | `--gemini` | `/grd:help` | `/grd:new-project` |
| OpenCode | `--opencode` | `/grd-help` | `/grd-new-project` |

Each runtime uses its own command prefix, but the workflow is the same across all four. After installing GRD, open your chosen runtime normally from your system terminal and use the commands shown above.

Notes:
- Claude Code-specific note: GRD writes `.claude/settings.json` for hooks and statusline. MCP servers are added to project `.mcp.json` for local installs or `~/.claude.json` for global installs.
- Codex-specific note: GRD writes `.codex/config.toml` during install, enables `features.multi_agent = true`, configures the required notify hook and built-in MCP servers, registers GRD agent roles in `[agents.*]`, and for local installs exposes only public `grd-*` agents there as discoverable skills in repo-scoped `.agents/skills/`; the full agent catalog still installs under `.codex/agents/` for direct invocation.
- Codex global skills use `CODEX_SKILLS_DIR` when set, or `~/.agents/skills/` by default.
- Gemini-specific note: GRD writes `.gemini/settings.json` during install, enables `experimental.enableAgents`, configures the required hooks and built-in MCP servers, and installs `policies/grd-auto-edit.toml` for Gemini auto-edit shell approvals.
- OpenCode-specific note: GRD writes `.opencode/opencode.json` for local installs or `~/.config/opencode/opencode.json` for global installs, installs flat `command/grd-*.md` files, configures built-in MCP servers under the `mcp` key, and manages GRD-owned `permission.read` / `permission.external_directory` entries.

<details>
<summary><strong>Config path overrides</strong></summary>

| Runtime | Local config dir | Global config dir | Environment overrides |
|---------|------------------|-------------------|-----------------------|
| Claude Code | `./.claude/` | `~/.claude/` | `CLAUDE_CONFIG_DIR` |
| Gemini CLI | `./.gemini/` | `~/.gemini/` | `GEMINI_CONFIG_DIR` |
| Codex | `./.codex/` | `~/.codex/` | `CODEX_CONFIG_DIR`; discoverable global skills use `CODEX_SKILLS_DIR` |
| OpenCode | `./.opencode/` | `~/.config/opencode/` | `OPENCODE_CONFIG_DIR`, `OPENCODE_CONFIG`, `XDG_CONFIG_HOME` |

GRD respects these overrides during install, uninstall, and runtime detection.

</details>

## What GRD Does

GRD guides research in four stages:

1. **Formulate**: asks targeted questions to pin down scope, assumptions, notation, and verification targets.
2. **Plan**: creates a phased roadmap with concrete tasks, dependencies, and success criteria.
3. **Execute**: runs specialist agents for derivations, numerical checks, literature work, and writing.
4. **Verify**: checks dimensional consistency, limiting cases, symmetry constraints, conservation laws, and numerical stability.

Each phase produces real artifacts such as `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `.tex` derivations, `.py` verification scripts, and figures.

GRD also locks conventions for up to 18 research fields across a project so notation, sign choices, and verification assumptions stay consistent as phases accumulate.

## How Work Is Structured

GRD's main workflow in `.grd/` is organized like this:

```text
Project
└── Milestone (v1.0, v1.1, v2.0, ...)
    └── Phase (1, 2, 2.1, 3, ...)
        └── Plan (01-01, 01-02, ...)
            └── Task
```

During execution, plans are grouped into waves:

```text
Wave 1: plans with no unmet dependencies
Wave 2: plans that depend on wave 1 outputs
Wave 3: plans that depend on earlier waves
```

- **Project**: the overall research workspace and its persistent context.
- **Milestone**: a major research checkpoint such as a paper submission, revision cycle, or result package. One project can have multiple milestones.
- **Phase**: one coherent chunk of work inside a milestone. Integer phases are planned work; decimal phases like `2.1` are inserted later when urgent work appears.
- **Plan**: the detailed execution breakdown for a phase, created by the runtime-specific `plan-phase N` command.
- **Wave**: not a separate top-level planning object, but the execution order inside a phase. Plans in the same wave can run in parallel; later waves depend on earlier ones.

Phase numbers continue across the whole project, so a new milestone may start at `Phase 6` rather than resetting to `Phase 1`.

## Domain Packs

GRD uses **domain packs** to provide domain-specific conventions, protocols, error catalogs, and verification rules. A domain pack is a directory with a `domain.yaml` file and supporting content.

The bundled **physics** domain pack is loaded by default. Set `GRD_DOMAIN=<name>` to select a different domain.

**Discovery order** (last wins):
1. **Bundled packs**: shipped with GRD (currently: physics)
2. **User packs**: `~/.grd/domains/<name>/`
3. **Project packs**: `.grd/domain/` (project-local override)

To create a new domain pack, copy `src/grd/domains/_template/` and customize `domain.yaml` and the conventions YAML.

## Worked Example

<details>
<summary><strong>Conformal bootstrap workflow</strong></summary>

The example below uses Claude Code / Gemini CLI syntax.

Suppose you want to use crossing symmetry and the numerical conformal bootstrap to bound low-lying operator dimensions in the 3D Ising CFT.

```text
/grd:new-project
> Use crossing symmetry and the numerical conformal bootstrap to bound low-lying operator dimensions in the 3D Ising CFT.
```

GRD will:
- ask clarifying questions about the correlator sector, conventions, target observables, numerical precision, and verification strategy
- create `.grd/PROJECT.md`, `.grd/REQUIREMENTS.md`, `.grd/ROADMAP.md`, and `.grd/STATE.md`
- break the work into phases such as crossing-equation setup, derivative-basis construction, semidefinite-program formulation, convergence checks, and interpretation of the resulting bounds

Then continue with:

```text
/grd:plan-phase 1
/grd:execute-phase 1
/grd:verify-work 1
```

Once the relevant phases are complete and verified, continue toward write-up with:

```text
/grd:write-paper "3D Ising bootstrap bounds"
/grd:arxiv-submission
/grd:peer-review
/grd:respond-to-referees
```

Typical artifacts include derivation notes, numerical scripts, convergence studies, and phase-level planning and verification documents under `.grd/`.

</details>

## Key GPD Paths

These commands run inside your installed AI runtime after GRD has been installed there. The examples below use Claude Code / Gemini CLI syntax.

### Core Runtime Paths

| Path | Use these commands |
|------|--------------------|
| Start or orient | `start`, `tour` |
| Create or import work | `new-project`, `new-project --minimal`, `map-research` |
| Leave or return after a break | `gpd resume`, `gpd resume --recent`, `resume-work`, `pause-work`, `suggest-next` |
| Run the research loop | `discuss-phase N`, `plan-phase N`, `execute-phase N`, `verify-work`, `progress`, `quick` |
| Write and review | `write-paper`, `peer-review`, `respond-to-referees`, `arxiv-submission` |
| Configure or branch | `settings`, `set-profile`, `set-tier-models`, `tangent`, `branch-hypothesis` |

Typical research loop: `/grd:new-project -> /grd:discuss-phase 1 -> /grd:plan-phase 1 -> /grd:execute-phase 1 -> /grd:verify-work -> repeat -> /grd:complete-milestone`

Typical publication loop: `/grd:write-paper -> /grd:peer-review -> /grd:respond-to-referees -> /grd:arxiv-submission`

### Command Context

Not every GRD command needs the same amount of project state.

| Command type | Meaning | Examples |
|--------------|---------|----------|
| `Projectless` | Can run before `.grd/PROJECT.md` exists | `/grd:new-project`, `/grd:map-research`, `/grd:add-todo` |
| `Project-aware` | Uses project context when present, but can also run from explicit standalone inputs | `/grd:discover "finite-temperature RG flow"`, `/grd:explain "Ward identity"`, `/grd:literature-review "axion monodromy"` |
| `Project-required` | Requires initialized GRD project state | `/grd:progress`, `/grd:plan-phase`, `/grd:write-paper`, `/grd:peer-review` |

Passing a manuscript path to a project-required command such as `/grd:peer-review paper/` selects the manuscript target, but does not bypass project initialization.

The full command reference below uses Claude Code / Gemini CLI syntax. Codex uses `$grd-...` and OpenCode uses `/grd-...`.

<details>
<summary><strong>Where To Find The Full Runtime Command Reference</strong></summary>

This README is the onboarding and orientation surface, not the complete in-runtime command manual.

- For the full in-runtime command reference, examples, and per-command usage details, run your runtime's help command such as `/gpd:help --all`, `$gpd-help --all`, or `/gpd-help --all`.
- For local CLI commands such as install checks, readiness, validation, permissions, observability, recovery, and diagnostics, run `gpd --help` in your normal system terminal.
Use the runtime-specific `pause-work` command when you want an explicit context handoff to restore on return.

#### Tangents & Hypothesis Branches

Tangents and alternative paths live primarily in `gpd:tangent`, `gpd:branch-hypothesis`, and `gpd:compare-branches`.

| Command | What it does |
|---------|--------------|
| `/grd:new-project` | Initialize a new research project with deep context gathering and `PROJECT.md` |
| `/grd:map-research` | Map existing research project — theoretical framework, computations, conventions, and open questions |

#### Phase Planning

| Command | What it does |
|---------|--------------|
| `/grd:discuss-phase <number>` | Gather phase context through adaptive questioning before planning |
| `/grd:research-phase <number>` | Research how to tackle a phase (standalone - usually use `/grd:plan-phase` instead) |
| `/grd:list-phase-assumptions <number>` | Surface the AI's assumptions about a phase approach before planning |
| `/grd:discover [phase or topic] [--depth {quick,medium,deep}]` | Run discovery phase to investigate methods, literature, and approaches before planning |
| `/grd:show-phase <number>` | Inspect a single phase's artifacts, status, and results |
| `/grd:plan-phase <number>` | Create detailed execution plan for a phase (`PLAN.md`) with verification loop |

#### Execution

| Command | What it does |
|---------|--------------|
| `/grd:execute-phase <phase-number>` | Execute all plans in a phase with wave-based parallelization |

#### Derivation

| Command | What it does |
|---------|--------------|
| `/grd:derive-equation` | Perform a rigorous research derivation with systematic verification at each step |

#### Quick Mode

| Command | What it does |
|---------|--------------|
| `/grd:quick` | Execute a quick research task with GRD guarantees (atomic commits, state tracking) but skip optional agents |

#### Roadmap Management

| Command | What it does |
|---------|--------------|
| `/grd:add-phase <description>` | Add research phase to end of current milestone in roadmap |
| `/grd:insert-phase <after> <description>` | Insert urgent research work as decimal phase (for example, `72.1`) between existing phases |
| `/grd:remove-phase <number>` | Remove a future phase from roadmap and renumber subsequent phases |
| `/grd:revise-phase <number> "<reason>"` | Supersede a completed phase and create a replacement for iterative revision |
| `/grd:merge-phases <source> <target>` | Merge results from one phase into another |

#### Milestone Management

| Command | What it does |
|---------|--------------|
| `/grd:new-milestone <name>` | Start a new research milestone cycle — update `PROJECT.md` and route to requirements |
| `/grd:complete-milestone <version>` | Archive completed research milestone and prepare for next phase of investigation |

#### Progress Tracking

| Command | What it does |
|---------|--------------|
| `/grd:progress` | Check research progress, show context, and route to the next action (execute or plan) |
| `/grd:suggest-next` | Suggest the most impactful next action based on current project state |

#### Research Support

| Command | What it does |
|---------|--------------|
| `/grd:explain [concept]` | Explain a research concept rigorously in the context of the active project or standalone question |

#### Session Management

| Command | What it does |
|---------|--------------|
| `/grd:resume-work` | Resume research from the previous session with full context restoration |
| `/grd:pause-work` | Create a context handoff when pausing research mid-phase |

#### Todo Management

| Command | What it does |
|---------|--------------|
| `/grd:add-todo [description]` | Capture an idea or task as a todo from current research conversation context |
| `/grd:check-todos [area]` | List pending research todos and select one to work on |

#### Validation

| Command | What it does |
|---------|--------------|
| `/grd:verify-work [phase]` | Verify research results through research consistency checks |

#### Debugging

| Command | What it does |
|---------|--------------|
| `/grd:debug [issue description]` | Systematic debugging of research calculations with persistent state across context resets |

#### Physics Validation

| Command | What it does |
|---------|--------------|
| `/grd:dimensional-analysis` | Systematic dimensional analysis audit on all equations in a derivation or phase |
| `/grd:limiting-cases` | Systematically identify and verify all relevant limiting cases for a result or phase |
| `/grd:numerical-convergence` | Systematic convergence testing for numerical research computations |
| `/grd:compare-experiment` | Systematically compare theoretical predictions with experimental or observational data |
| `/grd:validate-conventions [phase]` | Validate convention consistency across all phases |
| `/grd:regression-check [phase]` | Scan-only audit for convention conflicts and verification-state regressions in completed phase summaries and verifications |

#### Quantitative Analysis

| Command | What it does |
|---------|--------------|
| `/grd:parameter-sweep [phase]` | Systematic parameter sweep with parallel execution and result aggregation |
| `/grd:sensitivity-analysis` | Systematic sensitivity analysis — which parameters matter most and how uncertainties propagate |
| `/grd:error-propagation` | Track how uncertainties propagate through multi-step calculations across phases |
| `/grd:compare-results [phase, artifact, or comparison target]` | Compare internal results, baselines, or methods and emit decisive verdicts |

#### Research Publishing

| Command | What it does |
|---------|--------------|
| `/grd:write-paper [title or topic] [--from-phases 1,2,3]` | Structure and write a research paper from research results |
| `/grd:peer-review [paper directory or manuscript path]` | Conduct a staged six-pass peer review of a manuscript and supporting research artifacts in the current GRD project |
| `/grd:respond-to-referees` | Structure a point-by-point response to referee reports and update the manuscript |
| `/grd:arxiv-submission` | Prepare a paper for arXiv submission with validation and packaging |
| `/grd:literature-review [topic]` | Structured literature review for a research topic with citation network analysis and open question identification |

#### Hypothesis Branches

| Command | What it does |
|---------|--------------|
| `/grd:branch-hypothesis <description>` | Create a hypothesis branch for parallel investigation of an alternative approach |
| `/grd:compare-branches` | Compare results across hypothesis branches side-by-side |

#### Decision Tracking

| Command | What it does |
|---------|--------------|
| `/grd:decisions [phase or keyword]` | Display and search the cumulative decision log |

#### Visualization & Export

| Command | What it does |
|---------|--------------|
| `/grd:graph` | Visualize dependency graph across phases and identify gaps |
| `/grd:slides [topic]` | Create presentation slides from a GRD project or the current folder |
| `/grd:export [--format {html,latex,zip,all}]` | Export research results to HTML, LaTeX, or ZIP package |
| `/grd:error-patterns [category]` | View accumulated research error patterns for this project |
| `/grd:record-insight [description]` | Record a project-specific learning or pattern to the insights ledger |

#### Milestone Auditing

| Command | What it does |
|---------|--------------|
| `/grd:audit-milestone [version]` | Audit research milestone completion against original research goals |
| `/grd:plan-milestone-gaps` | Create phases to close all gaps identified by research milestone audit |

#### Configuration

| Command | What it does |
|---------|--------------|
| `/grd:settings` | Configure GRD workflow toggles, tier models, and research preferences |
| `/grd:set-profile <profile>` | Switch research profile for GRD agents (`deep-theory`, `numerical`, `exploratory`, `review`, `paper-writing`) |

#### Utility Commands

| Command | What it does |
|---------|--------------|
| `/grd:compact-state` | Archive historical entries from `STATE.md` to keep it under the 150-line target |
| `/grd:sync-state` | Reconcile diverged `STATE.md` and `state.json` after manual edits or corruption |
| `/grd:undo` | Roll back the last GRD operation with a safety checkpoint |
| `/grd:update` | Update GRD to the latest version with changelog display |
| `/grd:reapply-patches` | Reapply local modifications after a GRD update |
| `/grd:health` | Run project health checks and optionally auto-fix issues |
| `/grd:help` | Show available GRD commands and usage guide |

For full per-command detail and examples inside your runtime, run `/grd:help --all` or the equivalent runtime-specific help command.

</details>

## Optional: Model Profiles And Tier Overrides

GRD maps runtime-specific model names onto three capability tiers. Most users can leave this at the runtime default and only adjust it if they want to tune planning, execution, or verification behavior.

| Tier | Meaning |
|------|---------|
| `tier-1` | Highest capability |
| `tier-2` | Balanced default |
| `tier-3` | Fastest / most economical |

Available profiles are `deep-theory`, `numerical`, `exploratory`, `review`, and `paper-writing`.

| Runtime | Set profile | Open settings |
|---------|-------------|---------------|
| Claude Code / Gemini CLI | `/grd:set-profile review` | `/grd:settings` |
| Codex | `$grd-set-profile review` | `$grd-settings` |
| OpenCode | `/grd-set-profile review` | `/grd-settings` |

<details>
<summary><strong>Runtime-specific model string examples</strong></summary>

When you set explicit tier overrides, the model string is runtime-native. GRD passes it through unchanged, so it must match what that runtime already accepts:

- **Claude Code**: aliases like `opus`, `sonnet`, `haiku`, `default`, `sonnet[1m]`, or a provider-native pinned model ID. If your Claude Code install is backed by Bedrock, Vertex, or Foundry, use that provider's deployment/version identifier.
- **Codex**: the exact string Codex accepts for its `model` setting. If you configured a non-default Codex `model_provider`, keep that provider's exact model ID format. For OpenAI-hosted Codex tiers, the recommended mapping is `tier-1 = gpt-5.4`, `tier-2 = gpt-5.4-mini`, `tier-3 = gpt-5.4-nano`.
- **Gemini CLI**: an exact Gemini model name accepted by your installed Gemini runtime. Prefer exact model names for GRD tier overrides rather than the interactive Auto picker.
- **OpenCode**: a full `provider/model` string such as `anthropic/<model>`, `openai/<model>`, or `google/<model>`.

</details>

<details>
<summary><strong>Manual config example</strong></summary>

Per-project tier settings live in `.grd/config.json` under `model_overrides`:

```json
{
  "model_profile": "review",
  "model_overrides": {
    "codex": {
      "tier-1": "<runtime-native-model-id>",
      "tier-2": "<runtime-native-model-id>",
      "tier-3": "<runtime-native-model-id>"
    },
    "claude-code": {
      "tier-1": "<runtime-native-model-id>",
      "tier-2": "<runtime-native-model-id>",
      "tier-3": "<runtime-native-model-id>"
    },
    "gemini": {
      "tier-1": "<runtime-native-model-id>",
      "tier-2": "<runtime-native-model-id>",
      "tier-3": "<runtime-native-model-id>"
    }
  }
}
```

Valid runtime keys are `claude-code`, `codex`, `gemini`, and `opencode`. If no override is set for the active runtime, GRD uses that runtime's default model.

</details>

## Advanced CLI Utilities

The `grd` CLI also includes machine-readable validation, observability, and tracing commands for automation, review-grade checks, and debugging.

<details>
<summary><strong>Validation commands</strong></summary>

| Command | What it does |
|---------|--------------|
| `grd validate consistency` | Run cross-phase consistency and project health checks for the current workspace |
| `grd validate command-context <command> [arguments]` | Report whether a command is global, projectless, project-aware, or project-required in the current workspace |
| `grd validate project-contract <file.json or -> [--mode approved|draft]` | Validate a project-scoping contract before downstream artifact generation |
| `grd validate review-contract <command>` | Show the typed review contract for publication and review workflows |
| `grd validate review-preflight <command> [subject] --strict` | Check state integrity, manuscript or artifact presence, and review prerequisites |
| `grd validate paper-quality <file.json>` | Score a structured paper-quality manifest and fail on blocking issues |
| `grd validate paper-quality --from-project .` | Build paper-quality input from project artifacts, then score it conservatively |
| `grd validate plan-contract <PLAN.md>` | Validate PLAN frontmatter, including the embedded contract block and ID cross-links |
| `grd validate summary-contract <SUMMARY.md>` | Validate summary frontmatter plus contract-result / comparison alignment |
| `grd validate verification-contract <VERIFICATION.md>` | Validate verification frontmatter plus contract-result / comparison alignment |
| `grd validate review-ledger <file.json>` | Validate the final staged peer-review issue ledger |
| `grd validate referee-decision <file.json> [--strict] [--ledger <file.json>]` | Validate a staged peer-review decision against hard recommendation gates and optional ledger consistency |
| `grd validate reproducibility-manifest <file.json> [--strict] [--kernel-verdict]` | Validate a reproducibility manifest, optionally requiring review-ready coverage or emitting a content-addressed kernel verdict |

</details>

<details>
<summary><strong>Observability and trace inspection</strong></summary>

GRD stores project-local observability under `.grd/observability/` and detailed plan traces under `.grd/traces/`.

| Command | What it does |
|---------|--------------|
| `grd observe sessions [--status ...] [--command ...] [--last N]` | List recorded observability sessions |
| `grd observe show [--session ...] [--category ...] [--name ...] [--action ...] [--status ...] [--command ...] [--phase ...] [--plan ...] [--last N]` | Show logged observability events with filters |
| `grd observe event <category> <name> [--action ...] [--status ...] [--command ...] [--phase ...] [--plan ...] [--session ...] [--data <json>]` | Append an explicit observability event with optional structured metadata |
| `grd trace start <phase> <plan>` | Start a plan-local trace session |
| `grd trace log <event> [--data <json>]` | Append an event to the active trace |
| `grd trace stop` | Stop the active trace session |
| `grd trace show [--phase ...] [--plan ...] [--type ...] [--last N]` | Inspect plan-local trace events |

For read-only long-run visibility from your normal system terminal, use `gpd observe execution`.
When the status is uncertain, conservatively say `possibly stalled` instead of relying on runtime hotkeys.
Start with `gpd observe show --last 20` when you need the recent event trail.
If `gpd observe execution` surfaces an alternative-path follow-up or `branch later` recommendation, route it through the runtime `tangent` command first; use the matching `branch-hypothesis` command only when you want the explicit git-backed alternative path.

| Path | What it stores |
|------|----------------|
| `.grd/observability/sessions/*.jsonl` | Per-session event logs |
| `.grd/observability/current-session.json` | Latest session metadata for status and resume tooling |
| `.grd/traces/` | Plan-local execution traces for debugging and post-mortem review |
| `.grd/STATE.md` | Concise human-readable continuity state, not the full event ledger |

Low-level function and span calls are not recorded automatically. Observability is reserved for explicit workflow facts, trace lifecycle, and any agent or subagent events surfaced by the active runtime.

</details>

<details>
<summary><strong>Manuscript build</strong></summary>

| Command | What it does |
|---------|--------------|
| `grd paper-build [PAPER-CONFIG.json] [--output-dir <dir>]` | Materialize the canonical manuscript scaffold from `paper/PAPER-CONFIG.json`, emit `main.tex`, bibliography artifacts, and the paper artifact manifest |

</details>

## System Requirements

- Node.js with `npm`/`npx` (see the `Need Node.js?` note above if Node.js is missing)
- Python 3.11+ with the standard `venv` module (see the OS guides above for beginner setup steps on macOS, Linux, and Windows)
- Network access to npm and GitHub for the bootstrap installer
- One of: Claude Code, Gemini CLI, Codex, or OpenCode
- API access for the model provider used by your selected runtime

## Known Limitations

- Runtime-internal tool and subagent detail is limited by what the active provider/runtime exposes. GRD records the workflow, session, and trace events it can emit locally, but it does not fabricate opaque provider internals.

## Uninstall

Run `npx -y get-research-done --uninstall` for interactive uninstall. The equivalent subcommand form `npx -y get-research-done uninstall` also works, and you can add the runtime and scope flags above for a non-interactive uninstall.

Uninstall removes GRD from the selected runtime config only. It does not delete project `.grd/` artifacts or shared files under `~/GRD`; remove `~/.grd/` manually, or `GRD_HOME` if you used it, for a full wipe after uninstalling from all runtimes.

## Inspiration

GRD takes its name in explicit analogy with [GSD (Get Shit Done)](https://github.com/gsd-build/get-shit-done), whose adoption demonstrates how AI-native command workflows can be genuinely useful. GRD takes inspiration from that system to build a sophisticated prompt-engineered agentic system specifically designed for research.

GRD is also the research-general sibling of [Get Physics Done (GPD)](https://github.com/psi-oss/get-physics-done) — the physics-specific upstream that motivated much of the verification, formal-proof, and convention-lock tooling landing here. Improvements flow in both directions.

## Citation and Acknowledgement

If GRD contributes to published research, please cite **both** the upstream project and this fork. Metadata for the upstream is in [`CITATION.cff`](https://github.com/psi-oss/get-research-done/blob/main/CITATION.cff).

**Upstream (Physical Superintelligence PBC):**

```bib
@software{physical_superintelligence_2026_grd,
  author = {{Physical Superintelligence PBC}},
  title = {Get Research Done (GRD)},
  version = {1.1.0},
  year = {2026},
  url = {https://github.com/psi-oss/get-research-done},
  license = {Apache-2.0}
}
```

**This fork (Rome Thorstenson):**

```bib
@software{thorstenson_2026_grd_fork,
  author = {Thorstenson, Rome},
  title = {Get Research Done (GRD) --- Rome-1 fork},
  year = {2026},
  url = {https://github.com/Rome-1/get-research-done},
  license = {Apache-2.0}
}
```

Plain text:

```text
Physical Superintelligence PBC (2026). Get Research Done (GRD) (Version 1.1.0). https://github.com/psi-oss/get-research-done
Thorstenson, R. (2026). Get Research Done (GRD) — Rome-1 fork. https://github.com/Rome-1/get-research-done
```

## License

GRD is released under the Apache License 2.0. See [`LICENSE`](https://github.com/psi-oss/get-research-done/blob/main/LICENSE).
