---
name: start
description: Optional Veera identity diagnostic; Build/Fix captures current chat identity automatically and does not require this command.
disable-model-invocation: true
---

# Veera — optional start diagnostic

Build/Fix setup is automatic. Invoke `/veera:build <task>` or `/veera:fix <task>` directly; do not require a separate start message. The trusted UserPromptSubmit hook captures the actual current chat identity without enrollment or project access. Read `docs/task-lifecycle.md` under the actual package root for lifecycle details.

Use exactly `/veera:start` only when the user explicitly wants an identity/setup diagnostic. Report the real hook result and any missing host prerequisite. Start alone does not begin a task, grant publication authority, or enroll a session. Do not invent IDs, inspect other sessions, alter native permissions or manufacture a bootstrap result. Retain actual identity/data-directory values only in the coordinator's context.

Use the returned package root, interpreter, plugin-data location and host for subsequent authorized task commands. Hook trust/loading still belongs to the host. If the hook is unavailable, identify that actual integration failure rather than adding a routine start step to every task.
