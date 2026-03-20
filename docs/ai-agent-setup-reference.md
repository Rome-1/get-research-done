# Setting Up AI Agents Across Runtimes: A GRD Reference Guide

This document explains how GRD (Get Research Done) sets up AI agent tooling across four runtimes — Claude Code, Gemini CLI, Codex, and OpenCode — and how to use this codebase as a reference for building your own multi-runtime agent system.

## Architecture Overview

GRD solves a core problem: **write agent tooling once, deploy it to any AI coding runtime**. The system has four layers:

```
┌─────────────────────────────────────────────────┐
│  Canonical Content (commands/, agents/, specs/)  │  ← Write once
├─────────────────────────────────────────────────┤
│  Adapter Layer (per-runtime translation)         │  ← Transform at install
├─────────────────────────────────────────────────┤
│  Runtime Catalog (descriptor-driven metadata)    │  ← Configure per runtime
├─────────────────────────────────────────────────┤
│  MCP Servers + Hooks (shared infrastructure)     │  ← Run everywhere
└─────────────────────────────────────────────────┘
```

**Key insight**: All commands, agents, and workflows are authored in a single canonical format (Claude Code markdown). At install time, each runtime adapter transforms them into the format that runtime expects.

---

## 1. Bootstrap: `npx -y get-research-done`

**Entry point**: `bin/install.js`

The bootstrap installer:
1. Detects Python 3.11+ and creates a managed venv at `~/.grd/venv/`
2. Installs the GRD Python package from GitHub releases
3. Prompts the user to select runtime(s) and install scope (global vs local)
4. Calls the Python adapter layer to install artifacts into the runtime's config directory

```
npx -y get-research-done
  → detects python
  → pip install get-research-done
  → python -m grd.adapters → adapter.install(grd_root, target_dir)
```

The `install()` method is a **template method** on the base adapter class (`src/grd/adapters/base.py`). Each step is a hook that subclasses override:

```python
class RuntimeAdapter(abc.ABC):
    def install(self, grd_root, target_dir, *, is_global=False, explicit_target=False):
        self._validate(grd_root)
        self._pre_cleanup(target_dir)
        self._install_commands(grd_root, target_dir, path_prefix, failures)
        self._install_content(grd_root, target_dir, path_prefix, failures)
        self._install_agents(grd_root, target_dir, path_prefix, failures)
        self._install_hooks(grd_root, target_dir, failures)
        self._configure_runtime(target_dir, is_global)
        self._write_manifest(target_dir, version)
        self._verify(target_dir)
```

---

## 2. Canonical Content Format

### Commands (`src/grd/commands/*.md`)

Commands are markdown files with YAML frontmatter. They become slash commands in the runtime.

```yaml
---
name: grd:dimensional-analysis
description: Systematic dimensional analysis audit
argument-hint: "[phase number or file path]"
context_mode: project-aware
allowed-tools:
  - file_read
  - shell
  - search_files
  - find_files
---

<objective>
Perform a systematic dimensional analysis...
</objective>

<process>
1. Load project state: `grd state load`
2. ...
</process>
```

**Key fields**:
- `name`: Canonical command name (translated per runtime)
- `allowed-tools`: Canonical tool names (translated per runtime)
- `context_mode`: `global` | `projectless` | `project-aware` | `project-required`
- `@{GRD_INSTALL_DIR}/path` — resolved to installed path at install time

### Agents (`src/grd/agents/*.md`)

Agent definitions are markdown files with role descriptions.

```yaml
---
name: grd-planner
description: Creates executable phase plans with task breakdown
tools: file_read, file_write, shell, search_files, mcp__context7__*
commit_authority: direct
surface: public
role_family: coordination
color: green
---

<role>
You are the GRD planner agent. Your job is to...
</role>
```

**Key fields**:
- `tools`: Comma-separated canonical tool names (supports `mcp__*` wildcards)
- `surface`: `public` (user-visible) or `internal` (system-only)
- `commit_authority`: `direct` (can commit) or `orchestrator` (needs approval)

---

## 3. Tool Name Translation

Each runtime has different names for the same tools. GRD maintains a canonical vocabulary and translates at install time.

**Canonical → Runtime mapping** (from `src/grd/adapters/tool_names.py`):

| Canonical | Claude Code | Gemini | Codex | OpenCode |
|-----------|-------------|--------|-------|----------|
| `file_read` | `Read` | `read_file` | `read_file` | `read_file` |
| `file_write` | `Write` | `write_file` | `write_file` | `write_file` |
| `file_edit` | `Edit` | `replace` | `apply_patch` | `edit_file` |
| `shell` | `Bash` | `run_shell_command` | `shell` | `shell` |
| `search_files` | `Grep` | `search_file_content` | `grep` | `grep` |
| `find_files` | `Glob` | `glob` | `glob` | `glob` |
| `web_search` | `WebSearch` | `google_web_search` | `web_search` | `websearch` |
| `ask_user` | `AskUserQuestion` | `ask_user` | `ask_user` | `question` |

Each adapter defines its map as a class attribute:

```python
class ClaudeCodeAdapter(RuntimeAdapter):
    tool_name_map = {
        "file_read": "Read",
        "file_write": "Write",
        "file_edit": "Edit",
        "shell": "Bash",
        ...
    }
```

Translation happens in three places:
1. **Frontmatter tool lists**: `allowed-tools: [file_read]` → `allowed-tools: [Read]`
2. **Body text references**: `"use the file_read tool"` → `"use the Read tool"`
3. **MCP tool handling**: `mcp__server__tool` kept as-is or dropped (Gemini auto-discovers)

---

## 4. Per-Runtime Install Artifacts

### Claude Code (`~/.claude/`)

```
~/.claude/
├── commands/grd/*.md        # Slash commands (nested directory)
├── agents/grd-*.md          # Agent definitions (flat)
├── hooks/
│   ├── statusline.py        # Status bar hook
│   └── check_update.py      # Update checker
├── get-research-done/       # Shared content (workflows, references)
├── settings.json            # Modified: statusLine, hooks, mcpServers
└── grd-file-manifest.json   # Install tracking
```

**Config format**: JSON (`settings.json`)
**Command prefix**: `/grd:`
**MCP config**: `mcpServers` key in settings.json or `.mcp.json`

### Gemini CLI (`~/.gemini/`)

```
~/.gemini/
├── command/*.toml             # Commands as TOML (not markdown)
├── agents/*.md                # Agents with restricted frontmatter
├── hooks/...
├── get-research-done/
├── settings.json              # Modified: experimental.enableAgents, hooks
└── grd-file-manifest.json
```

**Config format**: JSON (`settings.json`) + TOML commands
**Command prefix**: `/grd:`
**MCP config**: Auto-discovered at runtime (no install-time setup)
**Special**: Commands converted from markdown → TOML at install. Agent frontmatter stripped to Gemini-allowed fields only.

### Codex (`~/.codex/`)

```
~/.codex/
├── agents/*.md               # Agent definitions
├── config.toml               # Modified: multi_agent, notify sections
├── mcp.toml                  # MCP server definitions
├── hooks/...
└── grd-file-manifest.json

~/.agents/skills/grd-*.md     # Skills (global) — separate from config dir
```

**Config format**: TOML (`config.toml`, `mcp.toml`)
**Command prefix**: `$grd-` (skills invocation)
**MCP config**: `mcp.toml` with `[servers.grd-*]` sections
**Special**: Skills directory is separate from config directory. Agent roles registered in `config.toml` `[multi_agent]`.

### OpenCode (`~/.config/opencode/`)

```
~/.config/opencode/
├── command/grd-*.md           # Commands (flat, no name in frontmatter)
├── agents/*.md                # Agents with color hex codes
├── opencode.json              # Modified: permissions, mcp
├── mcp.json                   # MCP server definitions
└── grd-file-manifest.json
```

**Config format**: JSONC (`opencode.json`)
**Command prefix**: `/grd-` (hyphen, not colon)
**MCP config**: `mcp.json` (JSON format)
**Special**: Color names converted to hex (`cyan` → `#00FFFF`). `name` field removed from command frontmatter (filename is the identifier).

---

## 5. Runtime Catalog: Descriptor-Driven Metadata

Instead of hardcoding runtime details, GRD uses a JSON catalog (`src/grd/adapters/runtime_catalog.json`) that drives adapter behavior:

```json
{
  "runtime_name": "claude-code",
  "display_name": "Claude Code",
  "priority": 10,
  "config_dir_name": ".claude",
  "install_flag": "--claude",
  "launch_command": "claude",
  "command_prefix": "/grd:",
  "activation_env_vars": ["CLAUDE_CODE_SESSION", "CLAUDE_CODE"],
  "selection_flags": ["--claude-code", "--claude"],
  "global_config": {
    "strategy": "env_or_home",
    "env_var": "CLAUDE_CONFIG_DIR",
    "home_subpath": ".claude"
  },
  "hook_payload": {
    "workspace_keys": ["current_dir", "cwd", "path"],
    "model_keys": ["display_name", "name", "id"],
    "context_remaining_keys": ["remaining_percentage"]
  }
}
```

This means adding a new runtime requires:
1. A catalog entry (JSON)
2. An adapter class (Python, extending `RuntimeAdapter`)
3. A tool name map

---

## 6. MCP Servers

GRD ships 7 MCP servers as Python entry points, plus an optional arxiv server:

| Server | Entry Point | Purpose |
|--------|------------|---------|
| `grd-mcp-conventions` | `grd.mcp.servers.conventions_server` | Convention lock management |
| `grd-mcp-verification` | `grd.mcp.servers.verification_server` | Verification checks |
| `grd-mcp-protocols` | `grd.mcp.servers.protocols_server` | Step-by-step methodology |
| `grd-mcp-errors` | `grd.mcp.servers.errors_mcp` | Error catalog + detection |
| `grd-mcp-patterns` | `grd.mcp.servers.patterns_server` | Cross-project patterns |
| `grd-mcp-state` | `grd.mcp.servers.state_server` | Project state management |
| `grd-mcp-skills` | `grd.mcp.servers.skills_server` | Skill discovery + routing |

Servers are registered as `pyproject.toml` entry points:
```toml
[project.scripts]
"grd-mcp-conventions" = "grd.mcp.servers.conventions_server:main"
```

Each runtime registers them differently:
- **Claude Code**: `mcpServers` in `settings.json` with `command` + `args`
- **Codex**: `[servers.grd-*]` sections in `mcp.toml`
- **OpenCode**: entries in `mcp.json`
- **Gemini**: auto-discovered (no explicit config)

Public descriptor files (`infra/grd-*.json`) define health checks for each server, used by CI and the install flow.

---

## 7. Hook System

Four hook scripts provide cross-runtime infrastructure:

| Hook | Purpose | Trigger |
|------|---------|---------|
| `statusline.py` | Shows GRD status in runtime UI | Every prompt cycle |
| `check_update.py` | Polls GitHub for new versions | Session start |
| `runtime_detect.py` | Determines active runtime | On demand |
| `notify.py` | Dispatches notifications | Event-driven |

Hooks read a JSON payload from stdin (provided by the runtime) and extract fields using the catalog's `hook_payload` policy. This makes hook scripts runtime-agnostic — the catalog defines which JSON keys to look for.

```python
# Hook command building (install_utils.py)
def build_hook_command(target_dir, hook_filename, *, is_global, config_dir_name):
    interpreter = hook_python_interpreter()  # ~/.grd/venv/bin/python
    if is_global:
        return f"{interpreter} {target_dir}/hooks/{hook_filename}"
    return f"{interpreter} {config_dir_name}/hooks/{hook_filename}"
```

---

## 8. Key Patterns for Your Own Multi-Runtime Agent System

### Pattern 1: Write canonical, translate at install

Don't maintain separate content per runtime. Write everything in one format and transform it. GRD's `translate_shared_markdown()` method handles:
- Path placeholder resolution (`@{GRD_INSTALL_DIR}`)
- Tool name translation in frontmatter and body text
- Runtime-specific tag stripping

### Pattern 2: Template method for install pipeline

The base adapter's `install()` defines the sequence; subclasses override hooks. This prevents duplicated install logic while allowing runtime-specific behavior.

### Pattern 3: Descriptor-driven runtime metadata

Put runtime-specific constants (config dirs, env vars, command prefixes) in a data file, not code. This makes adding new runtimes a configuration change, not an architecture change.

### Pattern 4: Manifest tracking for safe reinstalls

Track every installed file with content hashes. On reinstall, you can detect user modifications and avoid overwriting them.

### Pattern 5: MCP as the shared tool layer

MCP servers provide domain-specific tools that work identically across all runtimes. The runtime handles MCP protocol transport; your servers provide the capabilities.

### Pattern 6: Hierarchical config resolution

Support multiple config resolution strategies: environment variables, XDG directories, home-relative paths. The runtime catalog's `global_config.strategy` field makes this configurable per runtime.

---

## File Map

```
src/grd/
├── adapters/
│   ├── base.py                 # Template method install pipeline
│   ├── claude_code.py          # Claude Code adapter
│   ├── gemini.py               # Gemini CLI adapter
│   ├── codex.py                # Codex adapter
│   ├── opencode.py             # OpenCode adapter
│   ├── install_utils.py        # Shared install helpers
│   ├── runtime_catalog.py      # Descriptor loading
│   ├── runtime_catalog.json    # Runtime metadata
│   └── tool_names.py           # Canonical ↔ runtime tool mapping
├── agents/                     # Canonical agent definitions (markdown)
├── commands/                   # Canonical command definitions (markdown)
├── hooks/                      # Runtime hook scripts
├── mcp/
│   ├── builtin_servers.py      # MCP server registry
│   └── servers/                # Individual MCP server implementations
├── specs/                      # Shared workflows, references, templates
└── registry.py                 # AgentDef/CommandDef dataclasses
```
