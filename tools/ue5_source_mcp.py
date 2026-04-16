"""UE5 Source MCP Server.

Exposes UE5 engine and sample source files via MCP tools:
  set_root          - register a named source root for this session
  list_roots        - show currently configured roots
  search_ue5        - ripgrep over source files
  read_ue5_file     - read a specific header
  list_ue5_module   - list Public/ headers for a module or plugin
  find_ue5_plugins  - discover plugins by .uplugin scan

Roots are configured per-session via set_root. No paths are hardcoded.

Usage: python D:/projects/tools/ue5_source_mcp.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------

# Roots are empty at startup. The ue5-guru skill populates them via set_root
# at the start of each session after asking the user for paths.
ROOTS: dict[str, Path] = {}

SKIP_DIRS = {"Intermediate", "Saved", "Binaries", "DerivedDataCache", ".git"}

# ---------------------------------------------------------------------------
# Implementation functions (tested directly)
# ---------------------------------------------------------------------------


def _set_root_impl(label: str, path: str) -> str:
    label = label.strip().lower()
    if not label:
        return "Error: label must not be empty."
    p = Path(path.strip())
    if not p.exists():
        return f"Error: path does not exist: {p}"
    if not p.is_dir():
        return f"Error: path is not a directory: {p}"
    ROOTS[label] = p
    return f"Root '{label}' set to: {p}"


def _list_roots_impl() -> str:
    if not ROOTS:
        return "No roots configured. Call set_root to register paths for this session."
    lines = ["Configured roots:"]
    for label, path in sorted(ROOTS.items()):
        exists = "ok" if path.exists() else "MISSING"
        lines.append(f"  {label}: {path}  [{exists}]")
    return "\n".join(lines)


def _get_root(root: str) -> Path:
    if not ROOTS:
        raise ValueError(
            "No roots configured. Call set_root(label, path) first — "
            "the ue5-guru skill handles this at session start."
        )
    if root not in ROOTS:
        raise ValueError(
            f"Unknown root '{root}'. Configured: {sorted(ROOTS.keys())}. "
            "Call set_root to add it."
        )
    path = ROOTS[root]
    if not path.exists():
        raise ValueError(f"Root '{root}' path does not exist: {path}")
    return path


def _find_rg() -> str | None:
    """Locate ripgrep binary, falling back to known Windows install locations."""
    found = shutil.which("rg")
    if found:
        return found
    # Fallback: VSCode ships its own rg.exe on Windows
    import glob as _glob
    patterns = [
        r"C:\Users\*\AppData\Local\Programs\Microsoft VS Code\*\resources\app\node_modules\@vscode\ripgrep\bin\rg.exe",
        r"C:\Program Files\Microsoft VS Code\resources\app\node_modules\@vscode\ripgrep\bin\rg.exe",
    ]
    for pattern in patterns:
        matches = _glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def _search_impl(query: str, root: str = "engine", file_pattern: str = "*.h") -> str:
    root_path = _get_root(root)
    rg_bin = _find_rg()
    if not rg_bin:
        return "Error: ripgrep (rg) not found in PATH."

    cmd = [
        rg_bin,
        "--glob", file_pattern,
        "--glob", "!Intermediate",
        "--glob", "!Saved",
        "--glob", "!Binaries",
        "--glob", "!DerivedDataCache",
        "--with-filename",
        "--line-number",
        "--max-count", "10",
        "--max-filesize", "2M",
        "-e", query,
        ".",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace", cwd=str(root_path),
        )
    except subprocess.TimeoutExpired:
        return f"Search timed out for '{query}' in root '{root}'"

    lines = result.stdout.strip().splitlines()
    if not lines:
        return f"[{root}] No matches for '{query}'"

    output = [f"[{root}]"] + lines[:200]
    if len(lines) > 200:
        output.append(f"... truncated at 200 of {len(lines)} matches")
    return "\n".join(output)


def _read_file_impl(relative_path: str, root: str = "engine") -> str:
    root_path = _get_root(root)
    target = root_path / Path(relative_path.replace("\\", "/"))

    try:
        target.resolve().relative_to(root_path.resolve())
    except ValueError:
        return f"Error: path escapes root '{root}'"

    if not target.exists():
        return f"[{root}] File not found: {relative_path}"
    if not target.is_file():
        return f"[{root}] Not a file: {relative_path}"

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading file: {e}"

    MAX_CHARS = 500_000
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + f"\n... (truncated at {MAX_CHARS} chars)"

    return f"[{root}] {relative_path}\n{'=' * 60}\n{content}"


def _list_module_impl(module_name: str, root: str = "engine") -> str:
    root_path = _get_root(root)
    matches: list[str] = []
    seen: set[Path] = set()

    # UE5 module layouts:
    #   Standard:  <ModuleName>/Public/              (rglob finds .../<ModuleName>/Public)
    #   Plugin:    <PluginName>/Source/<ModuleName>/Public/
    #   Flat:      <PluginName>/Source/Public/       (module name == plugin name, no sub-dir)
    patterns = [
        f"{module_name}/Public",         # standard & nested module
        f"{module_name}/Source/Public",  # flat plugin layout (module == plugin)
    ]

    for pattern in patterns:
        for public_dir in root_path.rglob(pattern):
            if any(p in SKIP_DIRS for p in public_dir.parts):
                continue
            if not public_dir.is_dir():
                continue
            if public_dir in seen:
                continue
            seen.add(public_dir)
            for header in sorted(public_dir.rglob("*.h")):
                rel = str(header.relative_to(root_path))
                if rel not in matches:
                    matches.append(rel)

    if not matches:
        return f"[{root}] No module '{module_name}' found"

    return (
        f"[{root}] Module '{module_name}' ({len(matches)} headers)\n"
        + "\n".join(matches)
    )


def _find_plugins_impl(query: str | None = None, root: str = "engine") -> str:
    root_path = _get_root(root)
    results: list[str] = []

    for uplugin in sorted(root_path.rglob("*.uplugin")):
        if any(p in SKIP_DIRS for p in uplugin.parts):
            continue
        name = uplugin.stem
        if query and query.lower() not in name.lower():
            continue
        try:
            data = json.loads(uplugin.read_text(encoding="utf-8", errors="replace"))
            friendly = data.get("FriendlyName", name)
            desc = data.get("Description", "").strip()
        except Exception:
            friendly, desc = name, ""

        rel = str(uplugin.relative_to(root_path))
        entry = f"{friendly} [{name}]\n  Path: {rel}"
        if desc:
            entry += f"\n  {desc}"
        results.append(entry)

    if not results:
        label = f"matching '{query}' " if query else ""
        return f"[{root}] No plugins {label}found"

    cap = 50
    suffix = ""
    if len(results) > cap:
        suffix = f"\n\n... and {len(results) - cap} more. Use a query string to filter."
        results = results[:cap]

    return f"[{root}] {len(results)} plugins\n\n" + "\n\n".join(results) + suffix


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp_server = FastMCP("ue5-source")


@mcp_server.tool()
def set_root(label: str, path: str) -> str:
    """Register a named source root for this session.

    Call this at session start before using any other tools.

    Args:
        label: Short name for this root — e.g. 'engine', 'lyra', 'project'.
               'engine' is required. Others are optional.
        path:  Absolute path to the root directory on disk.
    """
    return _set_root_impl(label, path)


@mcp_server.tool()
def list_roots() -> str:
    """List all source roots currently configured for this session.

    Call this at session start to check whether paths are already set.
    If no roots are configured, set_root must be called before any other tools.
    """
    return _list_roots_impl()


@mcp_server.tool()
def search_ue5(query: str, root: str = "engine", file_pattern: str = "*.h") -> str:
    """Search UE5 source files using ripgrep.

    Args:
        query: Regex pattern to search for.
        root: Source root — engine (default), lyra, or project (if configured).
        file_pattern: Glob pattern for file types (default *.h).
    """
    return _search_impl(query, root, file_pattern)


@mcp_server.tool()
def read_ue5_file(relative_path: str, root: str = "engine") -> str:
    """Read a file from a UE5 source root.

    Args:
        relative_path: File path relative to the root (forward or back slashes).
        root: Source root — engine (default), lyra, or project (if configured).
    """
    return _read_file_impl(relative_path, root)


@mcp_server.tool()
def list_ue5_module(module_name: str, root: str = "engine") -> str:
    """List all Public/ headers for a named UE5 module or plugin.

    Args:
        module_name: Exact module or plugin name (e.g. GameplayAbilities, UMG, CommonGame).
        root: Source root — engine (default), lyra, or project (if configured).
    """
    return _list_module_impl(module_name, root)


@mcp_server.tool()
def find_ue5_plugins(query: str = "", root: str = "engine") -> str:
    """Discover UE5 plugins by scanning .uplugin files.

    Args:
        query: Optional name filter (case-insensitive substring). Empty = return all (capped at 50).
        root: Source root — engine (default), lyra, or project (if configured).
    """
    return _find_plugins_impl(query or None, root)


if __name__ == "__main__":
    mcp_server.run()
