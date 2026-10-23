---
name: build
description: Implement requested software features and changes automatically from ordinary task messages, using owned work, focused verification and review. No special command is required; informational questions do not start delivery.
---

# Veera — Build (Codex)

Guidance 0.3.2. Start automatically for an ordinary user request matching this skill. Read `docs/automatic-entry.md` under the installed package root and use the actual host bootstrap context. Explicit `$veera:build <task>` remains optional. Continue in the same turn without asking the user for an activation command, separate start message or routine confirmation. Automatic entry does not enroll, expand scope or authorize publication. For a new automatically routed task, freeze `delivery_mode: "local-verify"` unless the user requested publication; preserve the mode of an existing task.

## Load shared rules selectively

Use the actual bootstrap package root for controller operations. The installed skill location may be used to resolve package documentation before bootstrap arrives. Resolve `adapters/codex/README.md`, `docs/agent-contract.md`, `docs/engineering-standards.md` and `scripts/delivery.py` against that root; do not assume `CLAUDE_PLUGIN_ROOT` exists. Read the adapter README and contract sections Authority and ownership, Session isolation, Bounded contract, Runtime interface, and Evidence and immutable DONE. Read UI acceptance for UI work, Selective reasoning, context and repair before repair/context work, and Specialist handoff and return before actual delegation. Read engineering sections Applicability and authority, Role routing, Repository hygiene and resource ownership and affected stack/UI guidance. Native/project instructions, permissions and stricter ceilings prevail.

## Establish the owned task

First read the adapter's supported-behavior table. Codex uses its existing native permission policy without a Veera interactive approval gate. Capture user-delegable consent in the upfront intake and reuse it for eligible operations. The controller still validates ownership, scope, state and recovery evidence. For failures in Veera itself, use ordinary host-authorized package maintenance rather than depending on the broken delivery workflow.

Use only actual owner-context bootstrap `session_id` and configured persistent absolute `CLAUDE_PLUGIN_DATA`, with explicit `VEERA_HOST=codex` in hooks and CLI children. Carry the actual data-directory value explicitly into CLI children if necessary; do not invent session variables or fallback identities/storage. Actual identity and supported hooks are required for owned enrollment. If context is absent, use startup troubleshooting; reading this installed Build/Fix skill can receive identity through the actual PreToolUse hook. Do not require a direct command or treat a missing prompt event as missing trust. Read only the exact own record under `${CLAUDE_PLUGIN_DATA}/veera-v1/codex/sessions`, never scan other records or adopt legacy state. Migration is separately authorized and requires the shared contract's validation, exclusive creation and actual old-owner quiescence.

Only the coordinator owner runs these forms, substituting and quoting actual values; placeholders are not identities or environment variables:

```text
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" doctor
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" workspace --root ORIGINAL --task SLUG --session-id ACTUAL_HOST_ID
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" SUBCOMMAND --root TASK --session-id ACTUAL_HOST_ID --capability-file OWNER_FILE [COMMAND_ARGUMENTS]
```

Every subsequent public root command uses the third form. Never delegate the owner file or CLI. Resolve ORIGINAL to the authorized application repository, use returned canonical TASK/owner metadata and never modify peers/original to satisfy prerequisites. Resume only the same bound task with status/identity/fingerprint reconciliation, not reinit or fresh authority. Before init only task/plugin reads and draft `.veera-artifacts/` writes are allowed, not source.

## Deliver one bounded feature

Before the steps below, choose the authorized delivery mode in the draft contract. Select publishing only when the user requested it; publishing requires the version/release prerequisites. Otherwise explicitly freeze local-verify before init. For an explicitly nonpublishing task freeze `delivery_mode: "local-verify"` and omit `release`; release/version requirements below apply only to publishing. No mode changes after init.

1. Complete the discovery/interview below before freezing the plan. Record the original start, default 30-minute soft target and 120-minute hard ceiling, including discovery/review/release and respecting stricter limits. Inspect project instructions and the targeted impact map. Freeze one feature, observable acceptance, smallest relevant inspected checks, non-goals, UI evidence if needed, repair ceiling and the single authorized version/release file using the exact shared Bounded contract shape. Write/read back the draft under owned TASK artifacts. Missing release or repository prerequisites block complete delivery.
2. Run doctor and init once with workspace metadata, `--mode build --request TEXT --contract CONTRACT.json --minutes TARGET --hard-minutes HARD_ALLOWANCE`, preserving elapsed discovery. Record discover/plan/implement phases and make focused architecture-consistent changes/tests only in TASK. Coordinator owns routing and PM; use actual project roles only for concrete triggers. Shared context, provenance and bounded blocker protocols remain unchanged; do not fabricate role availability or create a second context store.
3. A soft target calls for actual Architect/Advisor consultation and a PM-owned recorded replan, not abandonment or relaxed gates. Hard expiry, denial, exhausted repairs and missing authority stop affected work; preserve checkpoints. No recursive delegation, automatic workflow or fresh allowance from restored context.
4. For publishing, use release-prepare before final checks. For an explicitly nonpublishing task, freeze `delivery_mode: "local-verify"` and omit release before init; skip all release operations. In either mode verify every frozen selection on the final fingerprint, with positive test counts and actual rendered/browser evidence where required. Obtain actual independent review of that exact tree and original evidence, read/import its attestation; self-review/static-only/zero-test/stale results cannot certify behavior. Follow the shared bounded blocker/repair limits without retries around denials.
5. Publishing finish means ready, not DONE. Publish only the authorized verified tree through at most one plain non-force push, retaining all release checks. The successful publish result is the completion receipt. For local verification, finish returns verified-local; report "verified locally; unpublished". On either successful terminal result the CLI automatically releases this chat's binding while preserving worktree, state and evidence. Do not issue another status/unbind command after session_binding is released. If cleanup-required is returned, retry only owner unbind after resolving that cleanup error; never rerun publication. Failed, stopped or budget-exhausted tasks keep their binding and checkpoint for recovery.

Native tools follow the existing host permission policy. Veera does not require an extra approval prompt on Codex or reject unfamiliar tool names merely because it cannot classify them. Ownership/terminal checks and supported direct-patch scope checks remain. Shells and opaque tools are governed by native permissions and task instructions, not a claimed Veera sandbox. Actual host denials remain binding; do not evade them.

Return scoped changes, actual checks/counts, UI evidence, real reviewer identity, version/release/push state, unmet criteria and checkpoints. No installation, smoke success or unmeasured savings claims.

## Installed bootstrap context

Use the package_root and python_executable returned by the trusted bootstrap hook. The hook also supplies the actual session_id, host, persistent plugin_data, and current cwd. These are runtime values, not placeholders. Set CLAUDE_PLUGIN_DATA to that plugin_data and VEERA_HOST=codex in each controller child. Use the returned absolute `python_executable` for controller commands, with quoted forward-slash paths on Windows; the guard accepts that interpreter as well as `python3`. If bootstrap is missing, follow `docs/startup-troubleshooting.md` with ordinary host tools: inspect current package capabilities and native hook status before prescribing trust or reload. Do not ask for a separate start message, infer missing trust, fabricate identity or claim capabilities require bootstrap. Choose the user-selected project checkout, not the projectless chat folder.

## Model selection

Read `docs/model-routing.md` under the resolved package root. Apply `docs/model-policy.json` before each bounded work item: Codex Sol for light work, Astra for important work. Select through supported host controls, report unavailable required models, and do not claim this text switches the current model. Claude keeps its selected native model. Preserve task ownership and existing delegation authority.

For authorized read-only specialist work, `scripts/model_router.py` classifies a bounded brief and returns a native dispatch descriptor; it does not execute a model on Codex. The parent dispatches through supported native tools under existing host permissions. See `docs/model-routing.md`. Never share owner capabilities or transfer owner writes.

## Discovery, initial questions and internal decisions

Before planning, init or source edits, read `docs/requirements-analysis.md` and `docs/intake-and-autonomy.md` under the resolved package root. For an underspecified or consequential request, use the requirements analyst process to inspect relevant code, project/domain documentation and necessary current primary sources. Resolve contradictions and turn evidence into observable requirements and an ordered plan. For a precise small change, keep analysis proportionate.

Conduct all necessary clarification during this initial discovery: offer two or three options with an evidence-based recommendation and tradeoffs; allow a custom answer. Investigate first, reuse existing answers, and follow up here if essential ambiguity remains. Never infer an answer from silence. Show the scope, acceptance and plan, then continue under existing authorization without another approval gate. Freeze validated `contract.discovery` and `contract.intake`, with no essential questions outstanding, before init.

Once implementation starts, PM, Architect and Advisor handle eligible decisions through the coordinator within captured limits. Do not restart preference interviews or ask repeated confirmations. Block only a genuinely human-only/denied/out-of-scope action, preserve its evidence and continue independent eligible work. Internal recommendations never grant native permissions or expand consent.

## Automatic live dashboard

Immediately after successful init and before the first implementation edit, follow `docs/dashboard.md`: launch the owned `dashboard` command in a host-tracked background process. It opens the browser automatically and saves the live address. Capture its output/process handle and show the user the clickable live URL once at the beginning. Do not wait for a dashboard request or ask again for permission to open this routine local preview. Reuse an existing task server. If the user asks for the dashboard or its path later, use `dashboard-info` and provide the validated URL and absolute record path. A browser launch failure should fall back to the link while eligible work continues.

## Worktree execution context

Set the native execution tool's workdir to TASK and use absolute task paths for patches. Codex canonical Bash hooks omit execution workdir and report the chat directory; that field cannot enforce command location. The adapter retains exact owner/state checks and file-target protection, and validates workdir when original execution arguments are exposed. Native permissions still govern shell and opaque tool effects. A projectless chat does not need to change its permanent root.
