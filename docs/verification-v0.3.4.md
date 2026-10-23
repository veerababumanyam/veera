# Verification 0.3.4 — DeepSeek Harness adapter

## Scope

This release adds a DeepSeek Harness (DSH) adapter, teaches the shared Python controller the `dsh` host, and adds automatic DeepSeek model routing (pro/flash). It does not change the Claude or Codex paths.

## What changed

- `scripts/ownership.py` — `registry()` accepts `VEERA_HOST=dsh` and resolves the persistent data root from `DSH_HOME` (default `~/.dsh`) into a separate `veera-v1/dsh/sessions` namespace.
- `scripts/bootstrap.py` — host whitelists include `dsh`; `context()` reads `DSH_HOME` and the `.dsh-plugin` manifest; a new `--dsh` mode reports the identity/setup diagnostic from the managed `DSH_*` environment.
- `scripts/safety.py` — native permission policy now includes `dsh` (DSH has its own approval model, no Veera ASK gate).
- `scripts/model_router.py` — `dsh` is an accepted calling host; it classifies and dispatches a native subagent carrying the selected DeepSeek route (`deepseek-v4-pro`/`deepseek-flash`, high effort) instead of the Codex bridge.
- `docs/model-policy.json` — `dsh` section maps light → `deepseek-flash` + high and important → `deepseek-v4-pro` + high, provider `deepseek-account`.
- `~/.dsh/profiles/desktop/cordis.patch.yml` — enables `subagent-model-selection-settings` with the two DeepSeek routes so the `subagent` tool exposes per-child `provider`/`model`/`reasoning_effort`.
- `adapters/dsh/` — adapter README and five DSH skills: `veera-build`, `veera-fix`, `veera-start`, `veera-dashboard`, `veera-route`.
- `.dsh-plugin/plugin.json` — adapter manifest (version 0.3.4).

## Checks run on this host

| Check | Result |
| --- | --- |
| `python -m py_compile` on edited scripts | `PY_COMPILE_OK` |
| `python scripts/bootstrap.py --dsh` (managed DSH env) | `status: ready`, real `DSH_SESSION_ID`, `plugin_data` = `C:/Users/VeeraDesktop/.dsh`, `package_root` = checkout |
| `python scripts/delivery.py doctor` | python 3.14.7, git 2.55.0.windows.5, `status: available` |
| `model_router.py --host dsh` (routine brief) | `deepseek-flash` + `high` + `deepseek-account` |
| `model_router.py --host dsh` (important brief) | `deepseek-v4-pro` + `high`, `status: dispatch_required`, `dispatch.tool: subagent` |
| Profile patch YAML | parses; `subagent-model-selection-settings` `enabled: true` with both routes |
| Full unittest suite | 262 tests, OK (skipped=6) |

## Remaining unknowns

- DSH has no prompt hook, so automatic entry is coordinator-driven (the model reads the loaded skill and the ordinary request); it cannot observe a `UserPromptSubmit` event.
- The end-to-end owned delivery flow (`workspace` → `init` → `finish` → `unbind`) is not exercised here because it mutates the repository worktree and requires a task the user actually asks for. The controller CLI and ownership namespace are the parts this release touches, and they are smoke-tested above.
- Skills are installed into `~/.agents/skills`, which DSH watches; the next session catalog picks them up without a restart.
- The `subagent-model-selection-settings` host setting is sampled when a fresh top-level session is composed, so the per-child `provider`/`model`/`reasoning_effort` fields appear only in a new session (or after a DSH restart). This session predates the change, so `veera-route` here would still fall back to reporting the selection.
