---
name: veera-build
description: Implement requested software features and changes automatically from ordinary task messages in DeepSeek Harness, using owned worktrees, focused verification and review. No special command is required; informational questions do not start delivery.
---

# Veera — Build (DeepSeek Harness)

Guidance 0.3.4. Start automatically for an ordinary user request matching this skill. Continue in the same turn; do not ask for an activation command, a separate start message, or routine confirmation. Automatic entry does not enroll, expand scope, or authorize publication. For a new automatically routed task, freeze `delivery_mode: "local-verify"` and omit `release` unless the user requested publication; never change the mode after init.

## DeepSeek Harness bootstrap

Resolve the veera package root from `$VEERA_ROOT` when set, otherwise the checkout at `C:/Users/VeeraDesktop/Desktop/veera`. Run every controller child with `VEERA_HOST=dsh`. Use these actual DSH facts and never invent identity:

- `session_id` = `$env:DSH_SESSION_ID` (every DSH shell call receives it)
- persistent data root = `$env:DSH_HOME` (default `C:/Users/VeeraDesktop/.dsh`), namespace `veera-v1/dsh/sessions`
- `python_executable` = the value returned by the identity diagnostic below (on Windows prefer `python`/`py`; `python3` can resolve to a non-Veera shim)

Run `python scripts/bootstrap.py --dsh` first. It returns `package_root`, `plugin_data`, `python_executable`, `session_id` and `package_version`. Reuse those exact values; do not adopt another session's record or enumerate sessions.

## Read the shared contract before acting

Under the package root, read `docs/automatic-entry.md`, `adapters/dsh/README.md`, `docs/agent-contract.md` (Operating core first, then the sections the Build skill names), `docs/engineering-standards.md` (Applicability and authority, Role routing, Verification and evidence, then the affected stack/UI sections), `docs/requirements-analysis.md` and `docs/intake-and-autonomy.md`. Native project instructions, permissions and stricter ceilings prevail.

## Establish the owned task

Only the coordinator runs the controller; never share the capability file. Pass `--session-id <session_id> --capability-file <capability_file>` on every command after `workspace`.

1. Discover first: inspect the request, any written spec and the code on the impact path; resolve essential questions in one upfront interview (zero when the spec and code answer them). Confirm the original is a clean committed Git root with `main` checked out.
2. Create the owned worktree and enroll the session:
   `python scripts/delivery.py workspace --root <repo-root> --task <slug> --session-id <session_id>`
   The result returns the new worktree `root` and the owner `capability_file`. Work only in that worktree.
3. Write and read back the Bounded contract under the worktree's `.veera-artifacts/`, including `discovery` and `intake`, then run `doctor` and initialize once:
   `python scripts/delivery.py init --root <worktree> --session-id <session_id> --capability-file <capability_file> --mode build --request <task> --contract <contract.json> --minutes <soft> --hard-minutes <hard>`
   Derive both allowances from the estimated remaining work, after subtracting elapsed discovery and within stricter user/project limits; there is no fixed default.
4. Drive the lifecycle with `status`, `phase` (one step at a time: discover, plan, implement, verify, review), `check` (verify only), `fingerprint`, `review` (review only, with an actual independent reviewer's JSON on the current fingerprint), `decision`, `repair` (new reason, before corrective edits after verify/review), `blocker`, `blocker-human-resolve`, `context`, `stop`, `checkpoint`, `resume`, `amend` and `finish`, as the shared docs describe. Publishing adds `release-prepare` (implement only) and `publish`.
5. Follow section Delivery craft of `skills/build/SKILL.md` under the package root for requirements, checks, slices, Review focus and repair; its CLI forms are Claude's, so keep the DSH forms above.
6. A successful `finish` (local `verified-local`) or `publish` (`complete`) releases this session's binding automatically and is the completion receipt. Run `unbind` only when that result reports `cleanup-required`. `archive` accepts only `complete` tasks and is never automatic.

Preserve ownership, frozen scope, evidence and immutable DONE. A failed controller step is a stop, not a license to bypass the gate; an exit-2 refusal names the prerequisite to fix, never a call to repeat unchanged. Veera maintenance itself uses ordinary host tools, not this delivery workflow.
