# Automatic task lifecycle

Veera is installed once for the user. Each explicitly requested task gets its own lifecycle; there is no separate mandatory start/stop conversation.

## Begin with the task

- Claude Code: `/veera:build <task>` or `/veera:fix <task>`.
- Codex: `$veera:build <task>` or `$veera:fix <task>`; hyphen aliases and leading desktop skill links also work.

The existing trusted UserPromptSubmit hook recognizes these direct commands, including their task arguments, and supplies the actual host session identity, cwd, interpreter and package/data paths in the same turn. It does not enroll, read task records, create a worktree or execute implementation. The coordinator proceeds with the authorized task, upfront intake, owned workspace and contract. It must not ask for another start message.

Ordinary prompts, quoted mentions, command lookalikes and the other host's syntax do not trigger bootstrap. This avoids adding Veera context to every unrelated message. `veera:start` remains an optional identity diagnostic. For missing context, follow [startup troubleshooting](startup-troubleshooting.md) instead of repeatedly asking for start or assuming hooks need trust. Reading a skill alone is not host identity evidence; missing or untrusted hooks remain an integration issue to fix, not a reason to manufacture an ID.

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
