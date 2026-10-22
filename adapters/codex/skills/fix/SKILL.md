---
name: fix
description: Diagnose and remediate one explicitly authorized Veera defect with focused regression evidence, owned-worktree changes and independent release review.
---

# Veera — Fix (Codex)

Guidance v0.1.6. The native Codex manifest selects these skills and the Codex hook adapter. Require explicit user invocation after successful exact standalone `$veera:start` bootstrap and a separate authorized fix request. Inspection alone does not authorize remediation/publication, and start never enrolls or grants task authority.

## Load shared rules selectively

Require the coordinator-provided absolute package root. Resolve `adapters/codex/README.md`, `docs/agent-contract.md`, `docs/engineering-standards.md` and `scripts/delivery.py` against it; do not assume `CLAUDE_PLUGIN_ROOT`. Read the adapter README and contract sections Authority and ownership, Session isolation, Bounded contract, Runtime interface, and Evidence and immutable DONE. Read UI acceptance for UI defects, Selective reasoning, context and repair before repair/context work, and Specialist handoff and return before actual delegation. Read engineering sections Applicability and authority, Role routing, Repository hygiene and resource ownership and the affected boundary/stack/UI sections. Native/project instructions, permissions and stricter ceilings prevail.

## Establish the owned task

Use only actual owner-context bootstrap `session_id` and configured persistent absolute `CLAUDE_PLUGIN_DATA`, with explicit `VEERA_HOST=codex` consistently in hooks and CLI children. Carry that actual data directory into CLI child environments if needed; do not invent session variables or fallback identities/storage. Missing bootstrap, environment, supplied root or trusted supported hooks blocks startup. Routing uses only the exact own record under `${CLAUDE_PLUGIN_DATA}/veera-v1/codex/sessions`; never scan other sessions or adopt legacy state. Migration is separate and requires the shared contract's validation, exclusive creation and actual old-owner quiescence.

Only the coordinator owner runs these forms, replacing and quoting actual values; placeholders are not identities or environment variables:

```text
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" doctor
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" workspace --root ORIGINAL --task SLUG --session-id ACTUAL_HOST_ID
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" SUBCOMMAND --root TASK --session-id ACTUAL_HOST_ID --capability-file OWNER_FILE [COMMAND_ARGUMENTS]
```

Every later public root command uses the third form. Never delegate owner capabilities or CLI. Resolve ORIGINAL to the authorized application repository; use returned canonical TASK/owner metadata, never guessed records or changes to peers/original to satisfy prerequisites. Resume the same bound task only after status/identity/fingerprint reconciliation, never reinit or renewed authority. Before init allow only own task/plugin reads and draft `.veera-artifacts/` writes, not source changes.

## Diagnose, remediate and prove

Before the steps below, choose the authorized delivery mode in the draft contract. Publishing is the default and requires the version/release prerequisites. For an explicitly nonpublishing task freeze `delivery_mode: "local-verify"` and omit `release`; release/version requirements below apply only to publishing. No mode changes after init.

1. Record original start, default 30-minute soft target and 120-minute hard ceiling including diagnosis/review/release, respecting stricter limits. Inspect project instructions, expected versus observed behavior, exact reproduction/evidence and the narrow causal path. Distinguish confirmed cause from hypothesis. Missing credentials/permissions block, never justify a bypass.
2. Freeze one remedy and focused regression criteria/checks before editing, including affected UI/browser evidence, non-goals, repair ceiling and single authorized release version file. Use the exact shared Bounded contract shape and inspected argv/count parsing; write/read back the task-local draft. Missing release or repository prerequisites block complete delivery. Run doctor and init once with workspace metadata and `--mode fix --request TEXT --contract CONTRACT.json --minutes TARGET --hard-minutes HARD_ALLOWANCE`, preserving elapsed diagnosis.
3. Record discover/plan/implement phases. Preserve pre-fix regression failure when practical, state its absence otherwise, and minimally correct the confirmed defect in TASK without adjacent rewrites. Coordinator alone routes actual triggered specialists and owns PM. Use the shared context/provenance and bounded blocker protocols, not invented identities, simulated consultation or a second context store. Soft expiry requires actual Architect/Advisor consultation and recorded PM replan, not abandoned acceptance. Hard limits, denial and exhausted repairs remain binding.
4. For publishing, use release-prepare before final checks. For an explicitly nonpublishing task, freeze `delivery_mode: "local-verify"` and omit release before init; skip all release operations. In either mode run every frozen selection on the final fingerprint, keeping actual invocations, counts, outputs and required rendered/browser evidence. Obtain actual independent review of the same tree, causal evidence and original check artifacts; read/import its attestation. Static-only/zero-test/stale/synthetic output and self-review do not prove the fix. Observe shared bounded repairs/attempts; no retry around denial or acceptance weakening.
5. Publishing finish means ready, not DONE. Publish only the exact authorized verified tree through at most one plain non-force push to origin/main, retaining shared release guards; never modify/synchronize peer/local main checkouts. Failed/ambiguous pushes block without retry or substitute push. Confirm actual complete status before DONE; unbind only the exact own completed record, preserving state/evidence/worktrees. Local finish means terminal verified-local; report "verified locally; unpublished", preserve the binding/evidence and do not publish or claim DONE. Stop/checkpoint unmet outcomes and resume only with required authority and unchanged history.

Native tools remain subject to explicit approval where applicable and/or host sandbox controls. Native exec is not trusted by Veera hooks. Unsupported ASK becomes DENY with human guidance; unknown mutating tools including unsupported `apply_patch` are denied, never routed around through another tool. Missing host facilities or independent roles are blockers, not permission to pretend support.

Return confirmed cause or remaining hypothesis, scoped remedy, actual regression/check counts, UI evidence, real reviewer identity, version/release/push state and outstanding criteria/checkpoints. No installation, smoke success or unmeasured savings claims.

## Installed bootstrap context

Use the package_root and python_executable returned by the trusted bootstrap hook. The hook also supplies the actual session_id, host, persistent plugin_data, and current cwd. These are runtime values, not placeholders. Set CLAUDE_PLUGIN_DATA to that plugin_data and VEERA_HOST=codex in each controller child. Use quoted forward-slash paths on Windows and `python3` for controller commands. If hooks have not been trusted, use the native `/hooks` review flow and submit `$veera:start` again in a new turn; do not fabricate bootstrap context. Choose the user-selected project checkout, not the projectless chat folder.

## Model selection

Read `docs/model-routing.md` under the resolved package root. Apply `docs/model-policy.json` before each bounded work item: Codex Sol for light work, Astra for important work. Select through supported host controls, report unavailable required models, and do not claim this text switches the current model. Claude keeps its selected native model. Preserve task ownership and existing delegation authority.

For already-authorized read-only specialist work, use `scripts/model_router.py` with a bounded task file instead of selecting a model manually. It automatically executes Sol for recognized routine work and Astra for consequential or uncertain work. See `docs/model-routing.md`. Never share owner capabilities, transfer owner writes or bypass a denied action through this bridge.
