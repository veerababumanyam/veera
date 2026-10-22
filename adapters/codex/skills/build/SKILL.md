---
name: build
description: Deliver one explicitly authorized bounded Veera feature using the shared contract, owned worktree, focused verification and independent release review.
---

# Veera — Build (Codex)

Guidance v0.1.6. The native Codex manifest selects these skills and the Codex hook adapter. Require explicit user invocation after successful exact standalone `$veera:start` bootstrap and a separate authorized build request. Start never enrolls or grants implementation/release authority.

## Load shared rules selectively

Require the coordinator-provided absolute package root. Resolve `adapters/codex/README.md`, `docs/agent-contract.md`, `docs/engineering-standards.md` and `scripts/delivery.py` against that root; do not assume `CLAUDE_PLUGIN_ROOT` exists. Read the adapter README and contract sections Authority and ownership, Session isolation, Bounded contract, Runtime interface, and Evidence and immutable DONE. Read UI acceptance for UI work, Selective reasoning, context and repair before repair/context work, and Specialist handoff and return before actual delegation. Read engineering sections Applicability and authority, Role routing, Repository hygiene and resource ownership and affected stack/UI guidance. Native/project instructions, permissions and stricter ceilings prevail.

## Establish the owned task

Use only actual owner-context bootstrap `session_id` and configured persistent absolute `CLAUDE_PLUGIN_DATA`, with explicit `VEERA_HOST=codex` in hooks and CLI children. Carry the actual data-directory value explicitly into CLI children if necessary; do not invent session variables or fallback identities/storage. Missing bootstrap, environment, root or supported trusted hooks blocks startup. Read only the exact own record under `${CLAUDE_PLUGIN_DATA}/veera-v1/codex/sessions`, never scan other records or adopt legacy state. Migration is separately authorized and requires the shared contract's validation, exclusive creation and actual old-owner quiescence.

Only the coordinator owner runs these forms, substituting and quoting actual values; placeholders are not identities or environment variables:

```text
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" doctor
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" workspace --root ORIGINAL --task SLUG --session-id ACTUAL_HOST_ID
python3 "/ABSOLUTE_PACKAGE_ROOT/scripts/delivery.py" SUBCOMMAND --root TASK --session-id ACTUAL_HOST_ID --capability-file OWNER_FILE [COMMAND_ARGUMENTS]
```

Every subsequent public root command uses the third form. Never delegate the owner file or CLI. Resolve ORIGINAL to the authorized application repository, use returned canonical TASK/owner metadata and never modify peers/original to satisfy prerequisites. Resume only the same bound task with status/identity/fingerprint reconciliation, not reinit or fresh authority. Before init only task/plugin reads and draft `.veera-artifacts/` writes are allowed, not source.

## Deliver one bounded feature

Before the steps below, choose the authorized delivery mode in the draft contract. Publishing is the default and requires the version/release prerequisites. For an explicitly nonpublishing task freeze `delivery_mode: "local-verify"` and omit `release`; release/version requirements below apply only to publishing. No mode changes after init.

1. Record the original start, default 30-minute soft target and 120-minute hard ceiling, including discovery/review/release and respecting stricter limits. Inspect project instructions and the targeted impact map. Freeze one feature, observable acceptance, smallest relevant inspected checks, non-goals, UI evidence if needed, repair ceiling and the single authorized version/release file using the exact shared Bounded contract shape. Write/read back the draft under owned TASK artifacts. Missing release or repository prerequisites block complete delivery.
2. Run doctor and init once with workspace metadata, `--mode build --request TEXT --contract CONTRACT.json --minutes TARGET --hard-minutes HARD_ALLOWANCE`, preserving elapsed discovery. Record discover/plan/implement phases and make focused architecture-consistent changes/tests only in TASK. Coordinator owns routing and PM; use actual project roles only for concrete triggers. Shared context, provenance and bounded blocker protocols remain unchanged; do not fabricate role availability or create a second context store.
3. A soft target calls for actual Architect/Advisor consultation and a PM-owned recorded replan, not abandonment or relaxed gates. Hard expiry, denial, exhausted repairs and missing authority stop affected work; preserve checkpoints. No recursive delegation, automatic workflow or fresh allowance from restored context.
4. For publishing, use release-prepare before final checks. For an explicitly nonpublishing task, freeze `delivery_mode: "local-verify"` and omit release before init; skip all release operations. In either mode verify every frozen selection on the final fingerprint, with positive test counts and actual rendered/browser evidence where required. Obtain actual independent review of that exact tree and original evidence, read/import its attestation; self-review/static-only/zero-test/stale results cannot certify behavior. Follow the shared bounded blocker/repair limits without retries around denials.
5. Publishing finish means ready, not DONE. Publish only the exact authorized verified tree through at most one plain non-force push to origin/main, retaining shared release guards; never synchronize or alter peer/local main checkouts. No substitute push or automatic retry. Confirm actual complete status before DONE; unbind only the exact own completed record, preserving state/evidence/worktrees. Local finish means terminal verified-local; report "verified locally; unpublished", preserve the binding/evidence and do not publish or claim DONE. Stop/checkpoint unmet outcomes; resume only under the shared authorization and unchanged-history rules.

Native tools remain subject to explicit approval where applicable and/or host sandbox controls. Native exec is not trusted by Veera hooks. Unsupported ASK must become DENY with human guidance; unknown mutating tools including unsupported `apply_patch` are denied. Do not switch tools to evade a denial. Missing independent roles or host facilities are blockers, not prompt-simulated support.

Return scoped changes, actual checks/counts, UI evidence, real reviewer identity, version/release/push state, unmet criteria and checkpoints. No installation, smoke success or unmeasured savings claims.

## Installed bootstrap context

Use the package_root and python_executable returned by the trusted bootstrap hook. The hook also supplies the actual session_id, host, persistent plugin_data, and current cwd. These are runtime values, not placeholders. Set CLAUDE_PLUGIN_DATA to that plugin_data and VEERA_HOST=codex in each controller child. Use quoted forward-slash paths on Windows and `python3` for controller commands. If hooks have not been trusted, use the native `/hooks` review flow and submit `$veera:start` again in a new turn; do not fabricate bootstrap context. Choose the user-selected project checkout, not the projectless chat folder.

## Model selection

Read `docs/model-routing.md` under the resolved package root. Apply `docs/model-policy.json` before each bounded work item: Codex Sol for light work, Astra for important work. Select through supported host controls, report unavailable required models, and do not claim this text switches the current model. Claude keeps its selected native model. Preserve task ownership and existing delegation authority.

For already-authorized read-only specialist work, use `scripts/model_router.py` with a bounded task file instead of selecting a model manually. It automatically executes Sol for recognized routine work and Astra for consequential or uncertain work. See `docs/model-routing.md`. Never share owner capabilities, transfer owner writes or bypass a denied action through this bridge.
