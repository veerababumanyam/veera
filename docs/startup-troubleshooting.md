# Diagnose startup without a start/retry loop

Missing bootstrap context is a symptom, not evidence that hooks are untrusted. Check the current installation and actual native status before recommending a remedy. These diagnostics use ordinary host-authorized tools and do not depend on the delivery controller.

## Supported invocation

Ordinary software task requests automatically route to Build/Fix; users do not need a command in each chat. The hook supplies lightweight context and the coordinator decides intent using [automatic entry](automatic-entry.md). Questions, opt-outs and quoted examples must not enroll a task. Do not prescribe a direct invocation as the repair for missing context.

Codex accepts plain `$veera:start`, `$veera:build <task>`, `$veera:fix <task>` and `$veera:dashboard`, including hyphen aliases. A leading desktop skill link with the matching label and Veera skill path also works. Surrounding whitespace is ignored. Link targets may refer to an older Veera cache version; they are parsed only as an invocation hint, never read or executed. The running trusted hook supplies its own current package path/version and actual host session identity.

Quoted examples and explanatory mentions do not start delivery. Invalid explicit links and commands are not treated as natural-language task requests. Claude's native slash-command behavior is unchanged, and Build/Fix also permits automatic skill selection. A separate start message is unnecessary.

Tool-created desktop chats may receive their initial request as delegated input, without UserPromptSubmit. When the coordinator selects and reads this installed Build/Fix skill, the existing PreToolUse hook supplies actual identity for an unbound session. This uses the real host event and adds context only; it does not approve tools, enroll, change trust or override an owned guard. Use that result in the same turn. If neither event returns usable identity, diagnose the actual integration failure rather than asking for a differently worded request.

## Inspect before prescribing a fix

Resolve the **current** installed package using the available skill metadata or native plugin listing. Do not keep reopening an old `0.2.5/.../SKILL.md` path copied into an error. With an allowed native shell, run the current package's `scripts/codex_compat.py` using the available Python interpreter. Default mode only reads package files. Package capabilities are available independently of bootstrap; `activation: not-verified` must remain explicit.

For a startup failure, add `--host-status --cwd ABSOLUTE_PROJECT`. This opt-in diagnostic uses the installed Codex executable's native `initialize` and `hooks/list` protocol through a short-lived metadata-only process. It starts no chat, model, agent or delivery, reads no session registry and changes no settings, trust, permissions or credentials. The wait is bounded; only its own child is stopped on timeout. Only Veera hook metadata is returned. Fresh configuration is not proof that an already-open chat reloaded.

| Native diagnostic status | Meaning and next step |
| --- | --- |
| `ready` | Both Veera hooks are enabled, trusted and loaded from this package. Do not ask for trust again. Check invocation format, stale chat context, interpreter/process errors or missing actual hook data. |
| `package-mismatch` | The native host resolves a different installed package. Reconcile through the supported plugin update/reload path; do not patch versioned caches or pretend an old skill is current. |
| `missing` | A required event is absent. Inspect the enabled installation, selected manifest and reported loading errors. |
| `disabled` | A Veera hook is disabled. Report the actual setting; do not infer a trust failure or silently override it. |
| `review-required` | The host reports untrusted or modified hooks. Only here is the native hook review flow the relevant next step. Native trust remains a host operation. |
| `unavailable` | The executable/query is unavailable or timed out. Trust is unknown, not denied. Preserve the package diagnostic and report this narrower limitation. |

Codex's `/hooks` interface reviews actual hook definitions; installation and trust are separate. See the [official hook contract](https://learn.chatgpt.com/docs/hooks). Never write trusted hashes manually or use a bypass flag as a repair.

## What the diagnostic cannot replace

No package check or native metadata response creates a session binding or proves a hook ran. Delivery still needs actual host-provided bootstrap identity from UserPromptSubmit or the supported PreToolUse skill-read path. A fixture must never be presented as the user's real identity or used to enroll their task. If an already-open chat retained obsolete package context, explain one host reload; ordinary task messages work after reload without a command.

## Windows session-directory access denied

An ownership-record `PermissionError` or Windows code 5 is a filesystem access failure, separate from activation, hook trust or Veera approval settings. Do not prescribe another start command or repeat an unchanged denied operation. Preserve the exact task worktree, checkpoint, session identity and recorded delivery mode.

Before 0.3.1, Veera created session, task-state and archive directories with `mode=0o700`. [Python's Windows mkdir behavior](https://docs.python.org/3.14/library/os.html#os.mkdir) changed in 3.13: this mode creates a user/administrator-only access-control list. Regression tests confirm these directories disable inherited access, which can exclude the host's execution identity. This is a compatibility defect, not proof of the ACL on any particular inaccessible directory.

Version 0.3.1 creates new Windows directories with inherited parent access and keeps POSIX directories at `0700` and records at `0600`. It neither grants access beyond the host-managed parent nor modifies existing permissions. Updating the plugin therefore prevents this creation defect but does not repair an already-inaccessible directory.

When both writes and permission inspection are denied, report the exact denied path and preserve the task. Access must be restored through the host's normal authorized Windows administration process. A failed inheritance-repair command is not evidence of a successful repair; do not repeatedly invoke it, take ownership, elevate through a workaround, change namespaces or fabricate a binding. Internal PM/Architect/Advisor decisions cannot supply Windows token privileges.

After actual access-restoration evidence is available, the original owning chat can run the documented workspace command with its original repository and task slug to recover the same unchanged pre-init worktree. Recovery validates ownership, Git registration, metadata and source state before enrollment. Retain the saved local-verification choice; no source/database tests or publication may be claimed merely because startup diagnostics passed.

## Owned worktree rejected from a projectless Codex chat

Codex's canonical Bash hook can report the original chat cwd while omitting the execution command's explicit workdir. This was observed in a real 0.3.1 task immediately after successful enrollment, and is also described in [the upstream report](https://github.com/openai/codex/issues/32360) and [hook implementation](https://github.com/openai/codex/blob/main/codex-rs/core/src/hook_runtime.rs).

Version 0.3.2 stops claiming that this session field proves command location. It validates the exact binding and task state for every owned call, checks known read/patch targets, and validates effective workdir when original execution arguments are exposed. Canonical shell and opaque tools remain subject to native host permissions and the task's scope instructions. Relative patch paths still resolve from the actual chat cwd; they are never silently redirected into the task.

Use explicit `workdir: TASK` for execution and absolute task paths for direct patches. A chat created outside the worktree need not change its permanent root. Existing genuine owner/state/scope/host denials remain binding. Diagnose a plugin defect from a separate authorized maintenance context instead of retrying the rejected call unchanged or fabricating a different owner.
