# Veera DeepSeek Harness adapter

The DeepSeek Harness (DSH) adapter makes Veera available to DSH sessions as five global skills under `~/.agents/skills`. DSH has no Claude-style prompt hooks and no Codex plugin manifest, so this adapter ships portable DSH skills that reuse the same host-agnostic Python controller (`scripts/*.py`), now with `VEERA_HOST=dsh` support.

## How DSH differs from Claude/Codex

| Concern | Claude Code | Codex | DeepSeek Harness |
| --- | --- | --- | --- |
| Skill discovery | plugin `skills/` | `.codex-plugin` | `~/.agents/skills/<name>/SKILL.md` (frontmatter `name` + `description`) |
| Identity | `UserPromptSubmit` hook `session_id` | hook `session_id` | `DSH_SESSION_ID` in every shell call |
| Persistent data | `CLAUDE_PLUGIN_DATA` | `PLUGIN_DATA`/`CLAUDE_PLUGIN_DATA` | `DSH_HOME` (default `~/.dsh`) |
| Package root | `CLAUDE_PLUGIN_ROOT` | `PLUGIN_ROOT` | `$VEERA_ROOT` or the checkout path |
| Auto entry | hook supplies identity | hook supplies identity | coordinator reads the loaded skill |

Because DSH has no prompt hook, automatic Build/Fix selection is done by the coordinator reading the skill description and the ordinary request, then running `bootstrap.py --dsh` for real identity. There is no implicit enrollment: `workspace` is the first mutating controller call.

## Install (global, for the current DSH user)

Copy each skill bundle into the shared agents root that `dsh-skill-filesystem` scans at rank 500:

```powershell
$dst = "$env:USERPROFILE\.agents\skills"
Copy-Item "adapters\dsh\skills\*" $dst -Recurse
```

DSH watches that root, so the skills appear in the next session catalog without a restart. Each `SKILL.md` resolves the package root from `$VEERA_ROOT` or the documented checkout, so the copied skill files can still reach `scripts/` and `docs/`.

## Identity and controller commands

Run the identity diagnostic first:

```powershell
$env:VEERA_HOST = 'dsh'
python scripts/bootstrap.py --dsh
```

It returns `package_root`, `plugin_data`, `python_executable`, `session_id` and `package_version`. All controller children receive `VEERA_HOST=dsh` plus the actual `DSH_SESSION_ID` and `DSH_HOME`; the capability file lives at `<DSH_HOME>/veera-v1/dsh/sessions/<sha256(session_id)>.json` and is returned by `workspace`. On Windows prefer `python`/`py` over `python3`, which can resolve to a non-Veera shim.

## Model routing (auto-switch)

`veera-route` classifies a bounded brief and returns a native `subagent` dispatch carrying `provider`/`model`/`reasoning_effort`:

- important work → `deepseek-account` / `deepseek-v4-pro` / `high`
- routine work → `deepseek-account` / `deepseek-flash` / `high`

This requires DSH's host subagent model selection to be enabled once in the active profile patch (`~/.dsh/profiles/desktop/cordis.patch.yml`):

```yaml
- id: subagent-model-selection-settings
  name: "@deepseek-ai/dsh-tool-subagent/model-selection-settings"
  config:
    enabled: true
    allowedModels:
      - provider: deepseek-account
        model: deepseek-v4-pro
      - provider: deepseek-account
        model: deepseek-flash
```

The setting is sampled when a fresh top-level session is composed, so it takes effect for the next new session (or after a DSH restart). Without it, `veera-route` still classifies but reports the required selection instead of silently substituting a model.

## Namespace

Persistent routing uses a separate `veera-v1/dsh/sessions` namespace. Claude and Codex keep their own namespaces; no cross-host adoption, enumeration, or global settings changes.

## Supported behavior

- Automatic Build/Fix selection from ordinary task requests (coordinator-driven, no command required).
- `veera-start` identity/setup diagnostic (optional, no enrollment).
- `veera-dashboard` live task dashboard and saved-address lookup.
- `veera-route` automatic DeepSeek model routing: `deepseek-v4-pro` (high effort) for important work, `deepseek-flash` (high effort) for routine work, dispatched as a native subagent via the host `subagent-model-selection-settings` route list.
- Full controller gates: ownership, frozen scope, evidence, immutable DONE, local verification, and the one explicitly authorized publish.
