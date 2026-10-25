# Automatic entry for ordinary requests

On Claude Code and Codex the UserPromptSubmit hook supplies actual session identity for ordinary messages; DeepSeek Harness has no prompt hook, so its coordinator runs `scripts/bootstrap.py --dsh`. This context is neither enrollment nor a judgment that the message is a task. Decide from the request and conversation in any wording or language, never a verb checklist. No command is needed.

## Decide: first match wins

1. **You are a delegate** (findings-only, router child, specialist): never enroll or run Veera workflows; only the user-facing coordinator owns delivery.
2. **Explicit opt-out or another selected workflow**: respect it.
3. **Veera's own maintenance**: ordinary host-authorized package tools; repairing the plugin never depends on its delivery workflow.
4. **Follow-up to an owned task bound to this session** (check only this session's exact binding): continue it with its captured answers; answer questions about it. Never create a new task, renew a budget or expand scope because another message arrived. New work begins after the previous task completed and released its binding.
5. **No change asked for**: answer questions and do requested read-only investigation, review or planning without enrollment, worktree or dashboard. A quoted example, status question, greeting or reference to a skill is not a request to execute it.
6. **A software change asked for**: **Fix** when existing behavior is wrong against intended, documented or tested behavior (crash, failing test, wrong result, or a bare report like "the total is wrong for refunds"); **Build** for new or changed behavior. If both, the primary deliverable decides; one task. Approving a change you proposed counts.

Still unclear whether a change is wanted: answer or investigate read-only and ask once; never enroll on a guess.

## Enter

Read the matching skill under the returned package root: `skills/<build|fix>/SKILL.md` on Claude, `adapters/codex/skills/<build|fix>/SKILL.md` on Codex, `adapters/dsh/skills/veera-<build|fix>/SKILL.md` on DeepSeek Harness. Continue this turn; never ask for a command or routine activation approval.

New automatically routed work uses `delivery_mode: "local-verify"` unless the user actually requested publication. Capture existing consent and essential requirements up front. Automatic routing authorizes no push, release, deployment, destructive operation or external message; native denials stay binding; discovery, tests, review and completion requirements still apply.

Use the actual `session_id`, `plugin_data`, `host`, `cwd`, `package_root` and `python_executable` from the hook. `requested_action: "auto"` is a routing invitation, not a Build/Fix classification. `enrolled: false` means the hook enrolled nothing, not that the session has no task.

## Without a prompt event

Tool-created desktop chats may start with delegated input and no UserPromptSubmit. The PreToolUse hook then supplies the same actual identity when an unbound coordinator reads this package's Build/Fix skill (on Claude, also when it invokes `veera:build`/`veera:fix`). It only adds context: it never allows a tool, overrides a guard, scans records, fabricates a user event, reads a transcript or changes hook trust. Reading a skill to answer a question still starts no delivery.

If identity is unavailable, follow startup troubleshooting with ordinary permitted tools; never ask the user to repeat the request as a command, replace host identity or bypass a denial. Explain the specific host integration failure if it blocks owned delivery.

Successful finish/publication releases the binding automatically ([task lifecycle](task-lifecycle.md)); no stop command, and closing a chat is not completion.
