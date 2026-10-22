---
name: start
description: Explicit owner-only Veera bootstrap through a trusted, supported Codex host integration; no enrollment or task execution.
---

# Veera — Start (Codex)

Guidance v0.1.6. The native Codex manifest selects these skills and the Codex hook adapter. Require explicit user invocation. The coordinator must supply the absolute package root; read `adapters/codex/README.md` and `docs/agent-contract.md` sections Authority and ownership and Session isolation under that root. Do not assume `CLAUDE_PLUGIN_ROOT` or Claude skill invocation controls exist on Codex.

The user submits exactly `$veera:start` as a standalone prompt. Only an actually configured trusted host `UserPromptSubmit` integration performs bootstrap. Reading this skill or a JSON template does not install or fire hooks. Missing documented host support/configuration blocks startup; do not silently substitute another trigger.

Require actual hook-provided `session_id`, configured persistent absolute `CLAUDE_PLUGIN_DATA` and explicit `VEERA_HOST=codex`. Bootstrap returns the first two only to this owner's context. Never fabricate an ID, invent a global session variable, infer from another session, fall back to plugin-local/cwd storage or share values with specialists/shared artifacts. Hooks and CLI must use the same environment; explicitly carry the actual returned data directory into later CLI children if not inherited.

Start does not enroll, create a workspace, inspect task state, migrate records or authorize build/fix/release. Do not scan sessions. Native permissions and sandbox remain binding; unsupported ASK becomes DENY with human guidance and unknown mutating tools including unsupported `apply_patch` are denied, not bypassed.

Return bootstrap success or the precise prerequisite without copying owner values into shared output. Wait for a separate authorized build/fix request through the host's supported skill invocation mechanism. No hook installation, smoke success or task completion claim.

## Installed bootstrap context

Use the package_root and python_executable returned by the trusted bootstrap hook. The hook also supplies the actual session_id, host, persistent plugin_data, and current cwd. These are runtime values, not placeholders. Set CLAUDE_PLUGIN_DATA to that plugin_data and VEERA_HOST=codex in each controller child. Use quoted forward-slash paths on Windows and `python3` for controller commands. If hooks have not been trusted, use the native `/hooks` review flow and submit `$veera:start` again in a new turn; do not fabricate bootstrap context. Choose the user-selected project checkout, not the projectless chat folder.

## Model selection

Read `docs/model-routing.md` under the resolved package root. Apply `docs/model-policy.json` before each bounded work item: Codex Sol for light work, Astra for important work. Select through supported host controls, report unavailable required models, and do not claim this text switches the current model. Claude keeps its selected native model. Preserve task ownership and existing delegation authority.
