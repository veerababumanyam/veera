# Automatic task lifecycle

Veera is installed once for the user. Each explicitly requested task gets its own lifecycle; there is no separate mandatory start/stop conversation.

## Begin with the task

- In Claude Code or Codex, describe the task normally: “Add CSV export” or “The total is wrong for refunds; fix it.” No activation command is required.
- Explicit `/veera:build` / `/veera:fix` on Claude and `$veera:build` / `$veera:fix` on Codex remain optional shortcuts.
- DeepSeek Harness has no prompt hook: its coordinator selects `veera-build`/`veera-fix` from the request and runs `scripts/bootstrap.py --dsh` for identity.

The existing trusted UserPromptSubmit hook supplies actual host session identity, cwd, interpreter and package/data paths for ordinary messages as well as direct commands. It does not enroll, read task records, create a worktree or execute implementation. The coordinator interprets the user's intent and conversation, then proceeds with the matching Build/Fix skill, upfront intake, owned workspace and contract. New automatic work defaults to local verification unless publication was requested. It must not ask for an activation command. See [automatic entry](automatic-entry.md).

Questions and quoted examples do not start delivery, even when lightweight routing context is present. Empty input, a message that begins with a quote, fence, blockquote, link or tag, and any `/` or `$` command other than a supported Veera command do not trigger automatic context; neither do router delegates (`VEERA_ROUTER_ACTIVE`). `veera:start` remains an optional identity diagnostic. Follow-ups reuse an existing task; they do not reset its budget or scope. For missing context, follow [startup troubleshooting](startup-troubleshooting.md) instead of asking for a command or assuming hooks need trust. Reading a skill is not itself identity evidence; only actual hook output is.

Before implementation, [requirements analysis](requirements-analysis.md) researches the relevant code/domain, resolves essential questions with options and recommendations, and freezes the requirements and plan. Execution then uses the captured internal decision limits.

The dashboard command also receives current-chat identity directly. Build/Fix opens its dashboard as prescribed in [dashboard behavior](dashboard.md).

## End on actual completion

The public controller CLI automatically releases only the current chat's exact binding after:

- `finish` returns `verified-local` for an explicitly local verification task, or legacy `complete`;
- `publish` returns `complete` after confirmed authorized publication.

`ready` is not completion and keeps the binding. Successful output includes `session_binding: "released"`. Use that output as the completion receipt instead of issuing another owner-only status or unbind command after release. Worktree, source, state, history, checkpoints and evidence stay on disk. No archive, source deletion, peer changes or budget resets are performed. The next explicitly authorized task can create its own workspace using the same chat identity.

The dashboard server stops after its existing 60-second terminal grace period. Known dashboard links continue during that grace period. After release, use the already-returned link or task-local saved address record; owner-only `dashboard-info` is no longer available for that released task. An expired link must not be described as live.

A cleanup failure returns `session_binding: "cleanup-required"` alongside the successful completion status and an error. Resolve only that cleanup error and retry `unbind` for the exact completed task. Never rerun publication or reinterpret successful delivery as failed merely because cleanup could not finish.

## Preserve incomplete work

Blocked, budget-exhausted, user-stopped and failed work retain their binding and checkpoints. There is no automatic renewal, reinitialization or adoption of another task. They need eligible recovery within existing authority, not a new start prompt. Releasing a completed task ends its active guard; it does not authorize editing its frozen records. Native permissions and project instructions continue to govern subsequent work.

The automatic release is part of the public CLI workflow. Embedded calls to controller library functions retain explicit ownership management for their caller. No SessionEnd hook is used: closing a chat is not evidence that a task completed.
