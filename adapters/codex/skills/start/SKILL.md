---
name: start
description: Optional Veera identity diagnostic; Build/Fix captures current chat identity automatically and does not require this command.
---

# Veera — optional start diagnostic

Build/Fix starts automatically from ordinary software task requests; explicit commands are optional. Never require a start message or ask the user to rephrase with a command. The trusted UserPromptSubmit hook captures the actual current chat identity without enrollment or project access. Lifecycle details: `docs/task-lifecycle.md` under the actual package root.

Use `$veera:start` only when the user explicitly wants an identity/setup diagnostic. The plain command and a leading desktop skill link are supported, including surrounding whitespace. Report the real hook result and its `package_version`. Start alone does not begin a task, grant publication authority, or enroll a session. Do not invent IDs, inspect other sessions, alter native permissions or manufacture a bootstrap result. Retain actual identity/data-directory values only in the coordinator's context, and use the returned package root, interpreter, plugin-data location and host for later authorized task commands.

Hook trust/loading belongs to the host. If no bootstrap output arrived, follow `docs/startup-troubleshooting.md` under the current installed package root now instead of adding a routine start step to every task. With ordinary permitted native tools run `scripts/codex_compat.py --host-status --cwd PROJECT`; it reads package capabilities and native hook metadata without creating a chat or changing trust. Report capabilities as package declarations even when activation is unverified; do not declare them unavailable or tell the user to repeat start alone. Missing context is not missing trust: recommend native hook review only when the host reports untrusted/modified hooks. Distinguish a stale version/link from a process failure. Use current installed skill metadata, not an old cache path quoted in the error; explain a one-time reload only if the chat is stale. Missing actual host identity still prevents owner enrollment.
