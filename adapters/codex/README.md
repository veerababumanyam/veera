# Veera Codex adapter

The native `.codex-plugin/plugin.json` selects these skills and hooks. Codex owns execution permissions. Veera does not add an interactive approval gate, change the host's approval settings, or require an approval request that Codex hooks cannot represent.

## Supported behavior

| Operation | Behavior |
| --- | --- |
| Package diagnosis | `scripts/codex_compat.py` reads package files without bootstrap, enrollment, ownership access or writes. |
| Direct `$veera:build <task>` / `$veera:fix <task>` | Trusted hook supplies actual identity and capabilities in the same turn; no separate start message. Hyphen aliases and leading desktop skill links are also supported. |
| `$veera:start` | Optional identity diagnostic; no enrollment or task execution. |
| Controller operations | Existing task ownership, frozen scope, time, evidence and state validation apply. |
| `amend`, `resume`, `blocker-human-resolve` | Reuse recorded upfront user authorization when it covers the action; the controller validates the request without an additional Codex hook approval prompt. |
| Shell and other native tools | Existing Codex permission policy applies. Unfamiliar names are not rejected merely because the adapter cannot classify them. Owned cwd and terminal-state checks still apply. |
| Direct `apply_patch` | Validate the supported envelope and all target paths against ownership, scope and protected settings. Malformed or forbidden patches remain denied. |
| Actual host denial | Binding. Neither an intake record nor a specialist can override the host. |

The old mandatory ASK gate on Codex has been removed. In a host configured to allow actions without prompts, Veera does not manufacture an interactive-approval requirement. This is a change to Veera's policy, not a change to native permissions. An unexpected ASK from a mismatched legacy runtime still fails closed rather than emitting an unsupported hook response.

Shell and opaque tools are not sandboxed by Veera. Their effects remain governed by host permissions, user authority and task instructions. The adapter does not claim it can enforce path scope on arbitrary programs or connector calls. Native subagents retain the host's actual controls.

## Upfront intake

Read [intake and autonomy](../../docs/intake-and-autonomy.md) before execution. Collect essential missing information once at the beginning, reuse consent already supplied, and freeze the user-intent record in the contract. PM, Architect, Advisor and orchestrator handle eligible decisions internally within those limits. Do not repeatedly interrupt the user for already-authorized work.

Task/permission boundaries, genuine missing credentials and host denials are distinct from routine implementation choices. Continue independent eligible work when a particular action cannot proceed. Never claim a role was consulted unless it actually was.

## Bootstrap and ownership

- Inspect actual hook status first; use native review only for untrusted/modified definitions. Installation alone does not prove hook loading. Hook trust and per-action approval are different mechanisms.
- Require the actual `session_id` field from trusted `UserPromptSubmit` output; do not invent identity or discover another session's record.
- Codex supplies `PLUGIN_ROOT`/`PLUGIN_DATA` and compatible `CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` aliases to plugin hooks. Use the returned absolute `package_root`, `plugin_data`, `python_executable` and cwd.
- The hook child sets `VEERA_HOST=codex`. Controller children must receive that host and the actual returned `CLAUDE_PLUGIN_DATA` explicitly if not inherited. Do not change global environment settings.
- Invoke the actual `python_executable`, quoting paths on Windows. The controller guard recognizes that interpreter and the documented `python3` alias.
- Persistent ownership uses only the exact `${CLAUDE_PLUGIN_DATA}/veera-v1/codex/sessions/<sha256 session_id>.json` record, never enumeration or legacy adoption. Claude retains its separate namespace.
- Build/Fix captures identity automatically for that direct task request, then creates an owned workspace through the controller. Start is optional. Successful CLI completion releases the binding automatically; neither startup nor cleanup confers publication authority. See [task lifecycle](../../docs/task-lifecycle.md).
- `workspace` requires the actual session argument. Subsequent root commands require that argument plus the returned owner capability. Only the coordinator uses it; never share it with specialists.

Missing bootstrap blocks the owned delivery controller, not independent host-authorized diagnosis of the package. A broken Veera installation should be repaired through ordinary host tools rather than requiring the broken workflow to repair itself. This does not authorize changing live owner records.

## Recovery and migration

Recover only the same bound task after reconciling its identity, checkpoint and current source. Recorded upfront authorization can cover eligible recovery, but cannot reset limits, bypass stale evidence, adopt another owner or erase a failed push attempt. The controller enforces those conditions.

Legacy migration remains a separate owner operation using `scripts/ownership.py` with the actual session, owned root and one exact legacy record. Require old-owner quiescence, validated identity and exclusive target creation; preserve the original. Never scan sessions, bulk migrate, hand-build ownership or switch namespaces to evade an actual denial.

## Verification and installation

The diagnostic reports package presence and declared capabilities, not hook trust or live activation. Verify the installed candidate in the actual host after its normal update/reload process. Preserve native permissions and existing owner data. Tests use isolated fixtures; they do not establish autonomous production delivery or authenticate specialist behavior.

The [official Codex hook contract](https://learn.chatgpt.com/docs/hooks), checked on 2026-10-23, documents the unsupported ASK response. Veera avoids depending on it on Codex. `PermissionRequest` is not used as a fabricated approval bridge. Claude's existing approval behavior is unchanged.

For missing bootstrap or an error pointing to an old cache version, use [startup troubleshooting](../../docs/startup-troubleshooting.md). Package capabilities are available without bootstrap. The optional `--host-status` diagnostic reads native hook metadata and distinguishes trusted/enabled configuration from stale packages and actual trust failures.
