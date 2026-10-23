# Diagnose startup without a start/retry loop

Missing bootstrap context is a symptom, not evidence that hooks are untrusted. Check the current installation and actual native status before recommending a remedy. These diagnostics use ordinary host-authorized tools and do not depend on the delivery controller.

## Supported invocation

Codex accepts plain `$veera:start`, `$veera:build <task>`, `$veera:fix <task>` and `$veera:dashboard`, including hyphen aliases. A leading desktop skill link with the matching label and Veera skill path also works. Surrounding whitespace is ignored. Link targets may refer to an older Veera cache version; they are parsed only as an invocation hint, never read or executed. The running trusted hook supplies its own current package path/version and actual host session identity.

Quoted examples, Markdown code, explanatory mentions, unrelated or external links, mismatched skill names and traversal paths do not activate. Claude's native slash-command behavior is unchanged. A separate start message is unnecessary for Build/Fix.

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

No package check or native metadata response creates a session binding or proves a hook ran for this user message. Delivery still needs actual host-provided bootstrap identity. A fixture can reproduce parsing and process behavior but must never be presented as the user's real identity or used to enroll their task. If a chat retained an obsolete version, explain one reload/new-chat step and then use the requested Build/Fix command directly; do not impose a repeated start-only conversation.
