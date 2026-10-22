# Veera Codex adapter — v0.1.5 candidate

Untested, not installed. This directory supplies portable Agent Skills guidance, not a runtime or trusted configuration. Current public documentation describes a shared Agent Skills format, but hook events, discovery, invocation, approvals, environment and tool behavior remain host-specific. Do not infer Claude plugin support from Markdown compatibility.

## Trusted integration prerequisites

- The coordinator supplies the absolute Veera package root. Resolve shared `docs/agent-contract.md`, `docs/engineering-standards.md` and `scripts/` paths against it. Do not assume Codex provides `CLAUDE_PLUGIN_ROOT`. Missing root blocks startup.
- Use only the hooks documented by the actual Codex host/version, including a supported `UserPromptSubmit` bootstrap integration. The coordinator supplies the package's documented JSON hook template separately. A repository template is data, not trusted host configuration; only explicitly authorized trusted host configuration loads hooks. Do not install or alter host configuration as part of using these skills. Missing/incompatible hook support blocks Veera startup.
- Require an actual host-provided `session_id` in the hook payload, using that same field name. Do not substitute another field, infer an ID from files/processes or invent a global session-ID variable.
- Configure an actual persistent absolute `CLAUDE_PLUGIN_DATA` directory and explicit `VEERA_HOST=codex` consistently for both hooks and CLI children. Codex must not silently use the default Claude namespace. Ownership is `${CLAUDE_PLUGIN_DATA}/veera-v1/codex/sessions/<sha256 session_id>.json`, separate from `claude` even when IDs match. No plugin-root, cwd, temporary or guessed fallback. No session enumeration.
- The user's exact standalone `$veera-start` prompt is the bootstrap trigger only when the trusted integration supports it. It returns the actual `session_id` and configured `CLAUDE_PLUGIN_DATA` to the owner context only, without enrollment, workspace creation or task authorization. Merely loading the start skill does not fire a hook. Require a separate authorized build/fix request after bootstrap. Do not assume Claude slash-command registration on Codex or silently substitute a different trigger.
- A hook child does not necessarily configure later exec children. Carry the actual bootstrap data-directory value explicitly into each CLI child if needed, with `VEERA_HOST=codex`; never invent a session environment variable. Pass actual identity through mandatory CLI arguments instead.

## Safety and tool compatibility

Shared contract sections Authority and ownership, Session isolation and Runtime interface remain binding. Only the owner may use the CLI/capability. `workspace` requires `--session-id ACTUAL_HOST_ID`; every other public root command requires both `--session-id ACTUAL_HOST_ID --capability-file OWNER_FILE`; `doctor` takes neither. Use the returned actual owner file, never hand-build a record or delegate it.

Map hook decisions only through documented host behavior. If Codex cannot represent `ask`, return DENY with a human-readable explanation and guidance to the supported native approval/configuration route; never omit a decision or fall through to allow. If no supported route exists, the operation stays blocked. Unknown mutating tools, including unsupported `apply_patch`, must be denied rather than claimed to be guarded. These files do not implement tool interception.

Native tools require existing task authority plus explicit host approval where applicable and/or the host sandbox. Codex may execute commands through its native exec safety controls; do not mark arbitrary commands trusted, bypass approval/sandboxing or route a denied action through another tool because Veera hooks exist. An adapter decision is not authorization or a sandbox. Missing role/tool support is a prerequisite gap, not permission to simulate an independent reviewer or delegated specialist.

## Owner-only legacy migration

Migration is separate from bootstrap and requires actual old-owner/writer quiescence before proceeding. With the configured persistent environment and `VEERA_HOST=codex`, the supplied absolute package root resolves this documented form:

```text
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/ownership.py" --session-id ACTUAL_HOST_ID --root OWNED_TASK --legacy-file EXACT_LEGACY_OWNER_FILE
```

Replace placeholders with actual authorized values. Validate one supplied legacy owner record against actual session and task/workspace identity, create the new target record exclusively, reject collisions and leave the legacy file intact. Never scan, bulk migrate, transfer another owner's session or manually copy records. Retaining the legacy record makes real quiescence essential. Missing validation/runtime support blocks migration. See the shared contract's Explicit legacy migration section; no new authority, reset or automatic adoption follows migration.

## Skill use and verification status

Load start/build/fix through the host's documented skill mechanism only within existing authority. Require explicit user invocation for these side-effecting flows; do not assume Claude's `disable-model-invocation` metadata is enforced by Codex. Each skill points to shared contract sections rather than duplicating a runtime or context store.

Before any promotion, verify this exact candidate against the actual supported host/version and coordinator-supplied hook template: exact versus non-exact start, owner-only bootstrap output, no enrollment on start, missing identity/environment, explicit child-environment propagation, Claude/Codex namespace isolation, unsupported ASK/tool denial, native approval/sandbox retention and validated exclusive migration with an actually quiescent old owner. Then probe a separately authorized scoped build/fix flow and preserve real invocations/results. No installation, smoke pass, runtime support or behavioral success is claimed here.
