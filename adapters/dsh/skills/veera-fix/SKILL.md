---
name: veera-fix
description: Diagnose and repair requested software defects automatically from ordinary task messages in DeepSeek Harness, using owned worktrees, focused verification and independent review. No special command is required; informational questions do not start delivery.
---

# Veera — Fix (DeepSeek Harness)

Guidance 0.3.4. Start automatically for an ordinary user request matching this skill. Continue in the same turn; do not ask for an activation command, a separate start message, or routine confirmation. Automatic entry does not enroll, expand scope, or authorize publication. For a new automatically routed task, freeze `delivery_mode: "local-verify"` and omit `release` unless the user requested publication; never change the mode after init.

## DeepSeek Harness bootstrap

Resolve the veera package root from `$VEERA_ROOT` when set, otherwise the checkout at `C:/Users/VeeraDesktop/Desktop/veera`. Run every controller child with `VEERA_HOST=dsh`. Use these actual DSH facts and never invent identity:

- `session_id` = `$env:DSH_SESSION_ID` (every DSH shell call receives it)
- persistent data root = `$env:DSH_HOME` (default `C:/Users/VeeraDesktop/.dsh`), namespace `veera-v1/dsh/sessions`
- `python_executable` = the value returned by the identity diagnostic below (on Windows prefer `python`/`py`; `python3` can resolve to a non-Veera shim)

Run `python scripts/bootstrap.py --dsh` first. It returns `package_root`, `plugin_data`, `python_executable`, `session_id` and `package_version`. Reuse those exact values; do not adopt another session's record or enumerate sessions. Below, `CTL` means `PYTHON_EXECUTABLE "PACKAGE_ROOT/scripts/delivery.py"` with those actual values.

## Read the shared contract before acting

Under the package root, read `docs/automatic-entry.md`, `adapters/dsh/README.md`, `docs/agent-contract.md` (Operating core first, then Authority and ownership, Session isolation, Bounded contract, Runtime interface, Evidence and immutable DONE) and `docs/engineering-standards.md` (Applicability and authority, Role routing, Verification and evidence, then the affected stack/UI sections). Native project instructions, permissions and stricter ceilings prevail. Read each source once; never rerun an unchanged command.

## Fix method

A change without a reproduced failure is a guess; a claim without a recorded result is not evidence.

1. **Baseline once:** run the project's test command once and keep counts/failures under `.veera-artifacts/`. Green covers only what the tests cover.
2. **Inventory:** start from reported failures. With no failure list, the specification and docs are the oracle: read them once into a numbered rule table (validation, status/error codes, limits, ordering, authorization/tenancy, concurrency, idempotency, expiry, pagination, persistence, audit) with each rule's enforcing code and covering test. Uncovered or contradicted rules are suspects; comments and markers are leads, not evidence. The specification bounds the search; this is not an audit.
3. **Reproduce:** probe each suspect with the smallest executable check in the project's own test idiom against unchanged source. Before init, probes live only under `.veera-artifacts/probes/` and must not write elsewhere in TASK. A failing probe confirms a defect; a passing one clears it.
4. **Root cause:** trace backward to where the wrong value, state or ordering originates; name the violated invariant. One hypothesis at a time; never stack edits. Probe same-pattern siblings inside scope.
5. **Freeze:** each confirmed defect becomes a criterion (rule ID, expected versus observed, probe output) with a focused regression check, plus the full test command when proportionate. Unconfirmed suspects are reported, not edited.
6. **Red, then green:** in `implement`, move probes into in-scope tests, run them on unfixed code (they must fail for the stated reason), make the smallest root-cause correction, then rerun the regression and the full suite. After three distinct misses on one failure, stop guessing and take the evidence to Advisor/Architect through the Bounded blocker protocol.
7. **Verify once:** enter `verify` only when every frozen argv already passes in the shell. A failed `check` reruns only after `repair` with a new reason (it spends a bounded global repair, returns to `implement` and clears review). A check that changes the tree fails (write test output to OS temp); the count regex must match the runner's summary (matches are summed; zero fails).

## Establish the owned task

1. Confirm the working directory is the authorized Git repository root. `workspace` requires `main` checked out at exactly `main` with a clean committed tree.
2. Create the owned worktree and enroll the session: `CTL workspace --root <repo-root> --task <slug> --session-id <session_id>`. It returns the worktree `root` (TASK) and the owner `capability_file`. Do all discovery and work in TASK, never the original checkout. Before init write only drafts under `.veera-artifacts/`, never source.
3. Discover (Fix method 1–5), write and read back the Bounded contract under `.veera-artifacts/`, run `CTL doctor`, then init once: `CTL init --root <TASK> --session-id <session_id> --capability-file <capability_file> --mode fix --request <task> --contract <contract.json> --minutes <TARGET> --hard-minutes <HARD_ALLOWANCE>`, with a soft target and hard allowance derived from the remaining work estimates, not fixed defaults.
4. Every later command is `CTL <subcommand> --root <TASK> --session-id <session_id> --capability-file <capability_file> ...`. Move `phase` one step at a time (`discover`, `plan`, `implement`, `verify`, `review`); `check --id` only in `verify`; an actual independent reviewer's attestation imported with `review --file` in `review`, covering every criterion ID at the current `fingerprint`. Use `status`, `decision`, `blocker`, `repair --reason`, `stop`, `checkpoint`, `context`, `amend`, `resume` and `blocker-human-resolve` as the shared docs describe; recovery operations need actual human authorization.
5. `finish` returns `verified-local` (report "verified locally; unpublished") or, when publishing, `ready` then `publish` returns `complete`. Either success automatically releases this session's binding and preserves the worktree, state and evidence; do not call `unbind` or `archive` afterwards. Only if the result says `cleanup-required`, resolve that error and retry `unbind` alone, never publication.

Preserve ownership, frozen scope, evidence and immutable DONE. A failed controller step is a stop, not a license to bypass the gate. Return each defect's cause or remaining hypothesis, red and green outputs, check counts/exits, reviewer identity and runtime state. Veera maintenance itself uses ordinary host tools, not this delivery workflow.
