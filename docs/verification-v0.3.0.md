# Veera 0.3.0 automatic entry verification

Ordinary UserPromptSubmit messages now receive actual runtime context. The coordinator interprets intent and chooses Build/Fix for software tasks; questions, opt-outs and delegated findings do not enroll a task. Claude's explicit-only Build/Fix frontmatter was removed. Existing commands remain supported.

For desktop tool-created chats that start with delegated input, an unbound session's actual PreToolUse event can supply identity when the installed Build/Fix skill is read. The fallback adds no permission decision and cannot replace an owned guard denial. Existing hook definitions and trust records are unchanged.

Automatic startup grants neither enrollment nor publication. New automatic work defaults to local verification. Existing task scope, state, deadlines and completion cleanup are preserved.

## Validation

The new automatic-entry regressions failed on 0.2.7 (17 errors in the initial seven-test run), reproducing missing identity for ordinary requests and skill reads. The revised suite covers natural requests, continuations, multilingual text, questions/opt-outs, unsupported commands, actual identity requirements, unbound skill-read recovery, unrelated tools, delegate recursion and preserved owned denials. Fixture tests never impersonate a real session.

- Full Python suite: **235 tests, no failures, two platform skips**, in 123.446 seconds. Log: `artifacts/final-v0.3.0-tests.log`.
- Build/Fix skill validation passed on both adapters, and native Claude marketplace validation passed. Windows validation used Python UTF-8 mode for the Unicode skill text.
- Both global installations report **0.3.0**. Installed-copy checks matched 101 packaged files, passed five affected test modules per host and executed the installed Windows hook commands with disposable fixtures. Native Codex reports both hooks trusted/enabled with no loading errors; host configuration and both hook definitions were unchanged.

## Actual fresh sessions

| Entry | Observed result |
| --- | --- |
| Codex CLI, ordinary request to add a calculator function | Automatically selected Build and read 0.3.0 guidance without a Veera command. The fresh session was read-only, so it ran the original test and proposed the change without saving it. |
| Codex desktop tool-created chat, same ordinary request in another disposable project | Automatically selected Build. The real PreToolUse skill-read event supplied the new chat's identity, and the coordinator attempted its owned workspace command with that identity. Enrollment was denied at the host's existing persistent ownership-record path. No implementation proceeded. |
| Codex CLI, ordinary question about the calculator | Answered the question, changed no files and made no delivery-controller call. |
| Claude Code, ordinary request to add the function | Native hook events confirmed successful automatic bootstrap from 0.3.0 with an identity matching the fresh Claude session. The model request then hit the account's weekly usage limit (HTTP 429). |

Automatic activation is verified. **A complete model-driven delivery is not verified in this environment**: Codex's persistent ownership-record access denial and Claude's account limit remain. The desktop test preserved the denial, and no filesystem permissions, owner records or host security settings were changed. These are separate from the repaired command-only startup requirement.

Detailed evidence: `artifacts/install-verification-v0.3.0.json`, `artifacts/host-hooks-installed-v0.3.0.json`, the `fresh-*-auto-v0.3.0` logs and `fresh-codex-question-v0.3.0` logs. The test application was outside the Veera repository; no source fixture was enrolled as a fabricated real session.

Host behavior follows the official [Codex hook contract](https://learn.chatgpt.com/docs/hooks) and [Claude skill invocation controls](https://code.claude.com/docs/en/skills), checked on 2026-10-23. PreToolUse additional context uses the actual host event, not a fabricated prompt or a permission bypass.
