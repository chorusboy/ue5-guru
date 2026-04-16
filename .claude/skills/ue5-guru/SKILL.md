---
name: ue5-guru
description: >
  UE5 session setup and source root management. Run at the start of any UE5
  session before using ue5-explain or ue5-plan. Configures engine path,
  reference projects, and active project source via the ue5-source MCP server.
  Also handles the ref: keyword for registering roots mid-session.
---

# UE5 Guru — Session Setup

Manages source roots for the ue5-source MCP server. Both ue5-explain and
ue5-plan depend on roots being configured before they run.

## Session Initialization

1. Call `list_roots` to check whether paths are already configured.
2. If `engine` is present, skip to step 4.
3. If not configured, ask each question separately and wait for the answer:

   **a. Engine source (required):**
   > "Where is your UE5 engine source? Stock installation only — not a
   > project-modified build. E.g. `D:\Games\UE_5.7`."

   Call `set_root("engine", <path>)`.

   **b. Reference projects (optional):**
   > "Any reference projects to include? Epic sample games, plugin libraries,
   > or other commercial projects you want searchable. Give a name and path
   > for each. Skip if none."

   For each: call `set_root(<name>, <path>)`. Accept any label the user gives.
   Unmodified Epic samples are high-trust; user-owned projects are
   context-dependent — state trust level when citing results.

   **c. Active project source (optional):**
   > "Want to include a specific game project's source for project-specific
   > context? Skip if engine + reference projects are sufficient."

   Call `set_root(<name>, <path>)`. Always label results with the project name.

4. Confirm:
   > "Using: engine → `<path>` | `<name>` → `<path>` | ..."

5. Ask what the user wants to do:
   > "Are you looking to understand a system (`ue5-explain`), or do you have
   > something specific you want to implement (`ue5-plan`)?"

## Adding Roots Mid-Session

At any point, a user can register a new root with:

```
ref: <name> = <path>
```

When detected: call `set_root(<name>, <path>)`, confirm, then continue with
the rest of the message.

## MCP Tools Reference

| Tool | Use for |
|---|---|
| `list_roots` | Check configured roots |
| `set_root(label, path)` | Register a source root |
| `search_ue5(query, root?, file_pattern?)` | Regex search across source files |
| `read_ue5_file(relative_path, root?)` | Read a specific file |
| `list_ue5_module(module_name, root?)` | List all headers in a module or plugin |
| `find_ue5_plugins(query?, root?)` | Discover plugins by name |

All query tools default to `root="engine"` and `file_pattern="*.h"`.
For config-driven systems, also search `file_pattern="*.ini"`.

**If the MCP server is not running:** state this clearly. Fall back to training
knowledge but flag all answers as unverified against live source.

## Source Trust Rules

| Root | Trust |
|---|---|
| `engine` | Authoritative. Always query first. Never assert API behavior without a source read. |
| Reference project | High if unmodified Epic source. State trust level when citing. |
| Active project | Context-dependent. Always label with project name. Note if engine is modified. |

Note material API differences between engine versions when relevant.
