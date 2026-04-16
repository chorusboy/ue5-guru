# ue5-guru

A Claude Code skill and MCP server for UE5 system teaching and implementation planning. Queries your local engine source directly — no hallucination, no training-data drift.

## What it does

When you ask a UE5 question ("how does GAS attribute replication work", "explain the animation slot system", "where do I start with collision channels"), the skill:

1. Builds a plain-language mental model of the system
2. Dispatches a research subagent to locate the actual classes and headers in your engine source
3. Delivers a class map with verified signatures and header paths
4. Gives you an ordered implementation plan with explicit decision points

Correctness is the priority. Every API assertion is verified against your local source before being stated.

## Requirements

- Python 3.x
- `mcp` SDK: `pip install mcp`
- ripgrep (`rg`) — either in PATH or bundled with VS Code
- A local UE5 engine installation (stock, not project-modified)
- Claude Code

## Setup

1. Clone this repo into your workspace or a dedicated directory:
   ```
   git clone https://github.com/chorusboy/ue5-guru.git
   ```

2. Open the repo as a workspace root in Claude Code. The `.mcp.json` and `.claude/skills/ue5-guru/` are picked up automatically.

3. The MCP server starts automatically when Claude Code connects. No manual launch needed.

## Session setup

At the start of each session the skill asks for:

- **Engine source path** (required) — your stock UE5 installation, e.g. `D:\Games\UE_5.7`
- **Reference projects** (optional) — Epic sample games or other reference projects to search for usage patterns
- **Active project source** (optional) — your game's source, for project-specific context

You can also register additional roots mid-session:
```
ref: lyra = D:\Projects\LyraStarterGame
```

## Running tests

```
cd ue5-guru
python -m pytest tests/ -v
```

Tests require the engine root and optionally the Lyra root to be on disk. Tests that can't find the roots are skipped automatically.

## Self-improvement

After each consultation the skill evaluates its own research effectiveness and makes targeted commits to improve future sessions. Changes are methodology-level (search strategies, tool guidance) — never topic-specific facts.
