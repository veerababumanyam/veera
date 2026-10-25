---
name: start
description: Optional Veera identity diagnostic; Build/Fix captures current chat identity automatically and does not require this command.
disable-model-invocation: true
---

# Veera — optional start diagnostic

Build/Fix starts automatically from ordinary software task requests; explicit commands are optional. Never require a start message or ask the user to rephrase with a command. The trusted UserPromptSubmit hook captures the actual current chat identity without enrollment or project access. Lifecycle details: `docs/task-lifecycle.md` under the actual package root.

Use exactly `/veera:start` only when the user explicitly wants an identity/setup diagnostic. Report the real hook result, its `package_version` and any missing host prerequisite. Start alone does not begin a task, grant publication authority, or enroll a session. Do not invent IDs, inspect other sessions, alter native permissions or manufacture a bootstrap result. Retain actual identity/data-directory values only in the coordinator's context, and use the returned package root, interpreter, plugin-data location and host for later authorized task commands.

Hook trust/loading belongs to the host. If no bootstrap output arrived, follow `docs/startup-troubleshooting.md` under the package root and name the actual integration failure instead of adding a routine start step to every task.
