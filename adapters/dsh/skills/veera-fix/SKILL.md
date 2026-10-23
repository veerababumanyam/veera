---
name: veera-fix
description: Diagnose and repair requested software defects automatically from ordinary task messages in DeepSeek Harness, using owned worktrees, focused verification and independent review. No special command is required; informational questions do not start delivery.
---

# Veera — Fix (DeepSeek Harness)

Guidance 0.3.4. Start automatically for an ordinary user request matching this skill. Continue in the same turn; do not ask for an activation command, a separate start message, or routine confirmation. Automatic entry does not enroll, expand scope, or authorize publication. For a new automatically routed task, freeze `delivery_mode: "local-verify"` unless the user requested publication.

## DeepSeek Harness bootstrap

Resolve the veera package root from `$VEERA_ROOT` when set, otherwise the checkout at `C:/Users/VeeraDesktop/Desktop/veera`. Run every controller child with `VEERA_HOST=dsh`. Use these actual DSH facts and never invent identity:

- `session_id` = `$env:DSH_SESSION_ID` (every DSH shell call receives it)
- persistent data root = `$env:DSH_HOME` (default `C:/Users/VeeraDesktop/.dsh`), namespace `veera-v1/dsh/sessions`
- `python_executable` = the value returned by the identity diagnostic below (on Windows prefer `python`/`py`; `python3` can resolve to a non-Veera shim)

Run `python scripts/bootstrap.py --dsh` first. It returns `package_root`, `plugin_data`, `python_executable`, `session_id` and `package_version`. Reuse those exact values; do not adopt another session's record or enumerate sessions.

## Read the shared contract before acting

Under the package root, read `docs/automatic-entry.md`, `docs/agent-contract.md`, `docs/engineering-standards.md` and `adapters/dsh/README.md`. Follow the Fix sections (diagnosis, remediation, regression testing, independent review) and the affected stack/UI guidance for the actual repository. Native project instructions, permissions and stricter ceilings prevail.

## Establish the owned task

1. Confirm the working directory is a Git repository root. `workspace` requires `main` checked out at exactly `main` with a clean tree.
2. Create the owned worktree and enroll the session:
   `python scripts/delivery.py workspace --root <repo-root> --task <slug> --session-id <session_id>`
   The result returns the new worktree `root` and the owner `capability_file`.
3. Change into the returned worktree, then initialize:
   `python scripts/delivery.py init --root <worktree> --session-id <session_id> --capability-file <capability_file> --mode fix --request <task> --contract <contract.json> --minutes 30 --hard-minutes 120`
   Produce the bounded contract per `docs/agent-contract.md`.
4. Drive the lifecycle with `status`, `phase`, `check`, `review`, `decision`, `finish`, `stop`, `repair`, `amend`, `blocker`, `blocker-human-resolve`, `fingerprint`, `archive` and `context` as the shared docs describe.
5. On successful local completion, archive evidence first, then release the binding with `unbind` (it requires a completed/verified-local state).

Preserve ownership, frozen scope, evidence and immutable DONE. A failed controller step is a stop, not a license to bypass the gate. Veera maintenance itself uses ordinary host tools, not this delivery workflow.
