# GPD on Linux

GPD adds structured physics-research commands to Claude Code, Codex, Gemini CLI, or OpenCode.

In these docs, "runtime" means the AI terminal app you talk to.

## What you need first

- A Linux machine with internet access
- Permission to install software
- Node.js 20 or newer
- Python 3.11 or newer with `venv`
- One supported runtime that already starts from your terminal:
  Claude Code, Codex, Gemini CLI, or OpenCode

## Open a terminal

Use whichever option matches your desktop:

- On Ubuntu and many GNOME-based desktops, press `Ctrl` + `Alt` + `T`
- Or open your app launcher, type `Terminal`, and press `Enter`
- If you already see a shell prompt, you are in the right place

## Check Node and Python

Run:

```bash
node --version
npm --version
npx --version
python3 --version
python3 -m venv --help
```

You want:

- Node `v20` or newer
- Python `3.11` or newer
- `python3 -m venv --help` to print help text instead of an error

## Install or update missing tools

Linux distributions vary more than macOS or Windows, so the safest path is:

- Use the official Node.js download or package-manager docs linked below if `node --version` is missing or older than `v20`
- Use your Linux distribution's package manager for Python if `python3` is missing or older than `3.11`

If `python3 -m venv --help` fails on Debian or Ubuntu, install the missing `venv` package:

```bash
sudo apt update
sudo apt install python3-venv
```

If you are on Fedora and `python3` is missing, a common install command is:

```bash
sudo dnf install python3
```

After installing anything, open a new terminal and rerun the version checks.

## Linux-specific notes

- Linux package names differ by distribution. If one command here does not match your distro, use the official docs linked below, then come back to the version checks.
- Claude Code's official docs list Ubuntu 20.04+, Debian 10+, and Alpine Linux 3.19+ as supported. If you use Alpine or another musl-based distro, read Anthropic's Linux install notes before continuing.

## Make sure your runtime works

Before installing GPD, confirm that your runtime starts from Terminal:

- Claude Code: `claude --version`
- Codex: `codex --help`
- Gemini CLI: `gemini --help`
- OpenCode: `opencode --help`

Then use the matching runtime guide:

- [Claude Code quickstart](./claude-code.md)
- [Codex quickstart](./codex.md)
- [Gemini CLI quickstart](./gemini-cli.md)
- [OpenCode quickstart](./opencode.md)

## Install GPD

Most beginners should install GPD into one runtime at a time and use `--local`.

| Runtime | Install command |
|---------|-----------------|
| Claude Code | `npx -y get-physics-done --claude --local` |
| Codex | `npx -y get-physics-done --codex --local` |
| Gemini CLI | `npx -y get-physics-done --gemini --local` |
| OpenCode | `npx -y get-physics-done --opencode --local` |

## Confirm success

1. In Terminal, run:

```bash
gpd --help
```

2. Open your runtime and run its GPD help command:

- Claude Code or Gemini CLI: `/gpd:help`
- Codex: `$gpd-help`
- OpenCode: `/gpd-help`

If both of those work, the install is in good shape.

## Where to go next

Use the exact command for your runtime:

| What you want to do | Claude Code / Gemini CLI | Codex | OpenCode |
|---------------------|--------------------------|-------|----------|
| Start a new project | `/gpd:new-project --minimal` | `$gpd-new-project --minimal` | `/gpd-new-project --minimal` |
| Map an existing folder | `/gpd:map-research` | `$gpd-map-research` | `/gpd-map-research` |
| Reopen work from your normal terminal | `gpd resume` | `gpd resume` | `gpd resume` |

## Official docs

- Ubuntu: [Package management](https://ubuntu.com/server/docs/package-management/)
- Node.js: [Download Node.js](https://nodejs.org/en/download)
- Node.js: [Node.js package-manager guidance](https://nodejs.org/en/download/package-manager)
- Python: [`venv` documentation](https://docs.python.org/3/library/venv.html)
- Anthropic: [Claude Code getting started](https://code.claude.com/docs/en/getting-started)
