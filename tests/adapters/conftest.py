"""Shared fixtures for adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def grd_root(tmp_path: Path) -> Path:
    """Create a minimal GRD package data directory (mirrors real layout).

    Layout:
      commands/help.md          — simple command
      commands/sub/deep.md      — nested command (tests flattening)
      agents/grd-verifier.md    — agent with tools list
      agents/grd-executor.md    — agent with allowed-tools array
      hooks/statusline.py       — hook script
      hooks/check_update.py     — hook script
      specs/references/ref.md   — GRD content reference
      specs/templates/tpl.md    — GRD content template
      specs/workflows/wf.md     — GRD content workflow
    """
    root = tmp_path / "grd_root"

    # commands/
    cmds = root / "commands"
    cmds.mkdir(parents=True)
    (cmds / "help.md").write_text(
        "---\nname: grd:help\ndescription: Show GRD help\n"
        "allowed-tools:\n  - file_read\n  - shell\ncolor: cyan\n---\n"
        "Help body with {GRD_INSTALL_DIR}/ref and ~/.claude/agents path.\n",
        encoding="utf-8",
    )
    sub = cmds / "sub"
    sub.mkdir()
    (sub / "deep.md").write_text(
        "---\nname: grd:sub-deep\ndescription: Deep command\n---\nDeep body.\n",
        encoding="utf-8",
    )

    # agents/
    agents = root / "agents"
    agents.mkdir()
    (agents / "grd-verifier.md").write_text(
        "---\nname: grd-verifier\ndescription: Verifies physics results\n"
        "surface: internal\nrole_family: verification\n"
        "tools: file_read, file_write, shell, search_files, find_files, web_search, web_fetch\ncolor: green\n---\n"
        "Verifier body with {GRD_INSTALL_DIR}/data.\n"
        "Config dir: {GRD_CONFIG_DIR}\n"
        "Runtime flag: {GRD_RUNTIME_FLAG}\n"
        "Use the file_read tool to check files.\n",
        encoding="utf-8",
    )
    (agents / "grd-executor.md").write_text(
        "---\nname: grd-executor\ndescription: Executes research plans\n"
        "surface: public\nrole_family: worker\n"
        "allowed-tools:\n  - file_read\n  - file_write\n  - file_edit\n  - shell\n"
        "  - mcp__physics_server\ncolor: blue\n---\n"
        "Executor body.\n",
        encoding="utf-8",
    )

    # hooks/
    hooks = root / "hooks"
    hooks.mkdir()
    (hooks / "statusline.py").write_text("#!/usr/bin/env python3\nprint('status')\n", encoding="utf-8")
    (hooks / "check_update.py").write_text("#!/usr/bin/env python3\nprint('update')\n", encoding="utf-8")

    # specs/ (GRD content directories)
    for subdir in ("references", "templates", "workflows"):
        d = root / "specs" / subdir
        d.mkdir(parents=True)
        name = f"{subdir[:3]}.md"
        if subdir == "references":
            content = (
                "# References\n"
                "Path: {GRD_INSTALL_DIR}/test\n"
                "Home: ~/.claude/test\n"
                "Search with web_search and web_fetch.\n"
            )
        elif subdir == "workflows":
            content = (
                "# Workflows\n"
                'Use ask_user([{"label": "Yes"}])\n'
                'Launch task(prompt="Run it")\n'
                "Run /grd:plan-phase 1 next.\n"
            )
        else:
            content = "# Templates\nPath: {GRD_INSTALL_DIR}/test\nHome: ~/.claude/test\n"

        (d / name).write_text(content, encoding="utf-8")

    return root
