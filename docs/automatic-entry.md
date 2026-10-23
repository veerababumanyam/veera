# Automatic entry for ordinary requests

The installed UserPromptSubmit hook supplies actual session identity for ordinary messages in Codex and Claude Code. This is lightweight context, not enrollment or a judgment that every message is a task. Interpret the current user request and conversation as a coordinator; do not use a verb checklist. Short bug reports, natural-language requests and continuations need no special command.

1. For a requested software change, select Build for new or changed behavior, or Fix for a defect. Read the matching skill from `adapters/codex/skills/` on Codex or `skills/` on Claude, under the returned package root. Continue in this turn without asking the user to invoke a command or approve routine activation.
2. Reuse an existing owned task and captured answers for follow-ups. Check only this session's exact binding. Do not create a new task, renew a budget or expand scope merely because another message arrived. Genuine new work begins after the previous task completed and released its binding.
3. Answer informational questions and perform requested read-only investigation without enrollment, a worktree or a dashboard. A quoted example, status question, greeting or reference to a skill is not a request to execute it. Respect an explicit opt-out or another selected workflow. Findings-only delegates must not enroll or run Veera workflows; only the user-facing coordinator owns delivery.
4. For new automatically routed work, use `delivery_mode: "local-verify"` unless the user has actually requested publication. Capture existing consent and essential requirements up front. Automatic routing does not authorize a push, release, deployment, destructive operation or external message. Existing native denials remain binding. Discovery, tests, review and completion requirements still apply.
5. Veera's own maintenance uses ordinary host-authorized package tools. Do not make repairing the plugin depend on its delivery workflow.

Use the actual `session_id`, `plugin_data`, `host`, `cwd`, `package_root` and `python_executable` from the hook. The bootstrap's `requested_action: "auto"` is a routing invitation, not a Build/Fix classification. `enrolled: false` describes the hook's lack of enrollment side effects; it does not assert that the session has no pre-existing task.

Some desktop tool-created chats start with delegated input rather than a UserPromptSubmit event. The existing PreToolUse hook can supply the same actual identity when an unbound coordinator reads this installed package's Build/Fix skill. This fallback only adds context, never allows a tool or overrides a guard decision. It does not scan records, fabricate a user event, read a transcript or change hook trust. A skill merely being read to answer a question still must not start delivery.

If actual identity is unavailable, follow startup troubleshooting with ordinary permitted tools. Do not ask the user to repeat their request using a command. Explain the specific host integration failure if it prevents owned delivery; never replace the host identity or bypass a denial.

Successful finish/publication still releases the task binding automatically as described in [task lifecycle](task-lifecycle.md). No manual stop command is required, and closing a chat does not count as completing a task.
