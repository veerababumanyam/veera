---
name: start
description: Explicitly bootstrap this owner's Veera session identity and persistent data environment without enrollment or task execution.
disable-model-invocation: true
---

# Veera — Start

Guidance package 0.1.5; first-probe candidate, untested and not installed by these files.

The user must submit exactly `/veera:start` as a standalone prompt. The configured Claude `UserPromptSubmit` hook, not this Markdown, performs bootstrap and returns the actual host-provided `session_id` and configured persistent `CLAUDE_PLUGIN_DATA` to this owner's context only. Do not treat a mention, arguments, an ordinary prompt or a build/fix invocation as implicit start. Do not invoke another tool to manufacture bootstrap output.

Read `${CLAUDE_PLUGIN_ROOT}/docs/agent-contract.md` sections Authority and ownership and Session isolation. Follow native/project instructions and permissions. Bootstrap does not enroll a session, create a workspace, inspect task state, migrate a legacy record or authorize implementation/release. Do not scan sessions or inspect unrelated projects.

If actual hook output, host identity, trusted hook configuration or the configured persistent absolute data directory is unavailable, report the prerequisite and stop. Never invent an ID or session-ID environment variable, guess from cwd/history, fall back to plugin-local storage or expose bootstrap values to specialists, logs or public output. Retain actual returned values only in the owner's context.

For subsequent separately authorized work, CLI children may need the actual returned `CLAUDE_PLUGIN_DATA` explicitly carried into their environment; hook child environment need not propagate. Claude uses `VEERA_HOST=claude` by default. Ownership lives at `${CLAUDE_PLUGIN_DATA}/veera-v1/claude/sessions/<sha256 session_id>.json`; start must not create a binding. Do not set global configuration or change permissions.

Return only bootstrap success or the specific missing prerequisite without echoing identity/data-directory values into shared artifacts. On success, wait for a separate authorized `/veera:build` or `/veera:fix` task. Neither start nor skill metadata proves the hook is installed, loaded or tested.
