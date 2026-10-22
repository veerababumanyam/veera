# Veera v0.1.4 isolation correction

## Confirmed mechanism and scope

User reported interference with unrelated sessions/projects. No incident transcript was supplied, but source inspection confirmed the prior hook walked cwd ancestors and invoked mutating status without session identity. Workspace setup edited shared Git exclusions and publication could update another checkout. These paths are removed in this staged update.

Changes confined to `/home/veera/veera` and disposable test fixtures. No unrelated sessions were enumerated/contacted; no unrelated project or active configuration was repaired or modified. Baseline package preserved as `artifacts/baseline-0.1.3.zip`. No external Git push. This plugin folder has no Git repository and was not initialized solely for staging.

Candidate manifest `artifacts/candidate-v5-sha256.json`, aggregate `5f1b697c40a148099f8e3d166d611a135e067ea7cc06c11c3e48e2161ea2c914`. Excludes artifacts/bytecode/session-routing records and verification notes.

## Implemented boundaries

- Exact host-session routing before cwd/project discovery. Unbound hooks return no-op before state, Git, locks or expiry updates. Bound sessions cannot operate in other or nested repositories.
- Mandatory session/capability arguments at public CLI dispatch, validated before contract/report/state reads. Session IDs must be actual host IDs, not invented env variables. Coordinator capability is not delegated to specialists.
- Owner pre-init draft preparation remains possible; file reads/writes remain task-scoped, with plugin guidance read exceptions. Nested write targets are checked before evidence/terminal allowances. Arbitrary shell is host-approval-gated, not claimed sandboxed.
- No shared Git exclude/config updates. Only own reserved untracked state/evidence omitted by controller queries; tracked reserved source rejected.
- Occupied main blocks before push without inspecting/modifying that checkout. Successful single remote push no longer updates local main or any peer checkout. Task worktree/branch creation and repository coordination lock remain the narrowly authorized shared Git administration effects.
- Completed-task unbind removes only that session's routing record; state/evidence/worktrees preserved. No automatic legacy adoption or broad cleanup.

## Actual executed checks

Environment: Linux, Python 3.12.3, Git 2.43.0, Node 24.22.1, Claude Code 2.1.307.

- `python3 -m unittest discover -s /home/veera/veera/tests -v`: **95 tests passed**, 8.483 seconds, exit 0. `artifacts/unittest-v5.log`.
- `node /home/veera/veera/tests/test_web.js`: **6 assertions passed**, exit 0. `artifacts/web-test-v5.log`.
- `python3 /home/veera/veera/tests/browser_smoke.py`: Chrome smoke passed, exit 0. `artifacts/browser-result-v5.json`.
- `claude plugin validate /home/veera/veera --strict --json`: passed, exit 0. `artifacts/plugin-validation-v5.json`; optional catalog icon warning remains.
- `claude plugin validate /home/veera/veera/skills --strict --json`: passed, exit 0. `artifacts/skills-validation-v5.json`.
- `claude plugin validate /home/veera/veera/agents --strict --json`: passed, exit 0. `artifacts/agents-validation-v5.json`.

Isolation fixtures explicitly instrument unbound hooks to reject cwd resolution/state calls, check foreign CLI before input/state/subprocess access, preserve shared config/excludes, prevent wrong-root/nested writes, maintain owner scope, permit pre-init draft preparation, enforce recovery approval independent of owner-option order, and retain task data on unbind. Publication fixtures now require the fixture user to free main explicitly; they assert original source/version and local main remain unchanged after successful remote publication. This replaces the earlier auto-sync behavior intentionally, not silently dropping it.

## Independent review and fixes

`harness-proposer` diagnosed the ownership-boundary defect. `harness-composer` updated session/release/hygiene guidance. Coordinator implemented runtime/tests. `harness-critic` identified nested write-target and recovery argument-order gaps; corrected both and added regressions. Final narrow verdict: **accept-for-tested-scope** for those two findings, based on source and named regression evidence. Reviewer did not execute tests or authenticate host session IDs; final manifest/invocation record supplied here.

## Limits / activation

Staged and locally tested, **not installed into active settings**. Fresh host session loading this plugin and supplying its actual identity is required to use the new CLI. Existing running sessions do not acquire updated hooks automatically. Legacy unbound runs are not adopted or edited. No real host-wide multi-session pilot was performed.

Explicit IDs and owner-file paths are cooperative routing, not cryptographic per-agent authentication. Same-UID code can bypass Python APIs/files; untrusted scripts, host tooling, subagent identity inheritance and permissions need native host/OS isolation. A plugin cannot guarantee containment of arbitrary executable code using prompt guidance or path checks alone. No universal zero-spill guarantee beyond the selected tested mechanisms is claimed.
