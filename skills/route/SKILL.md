---
name: route
description: Automatically select Sol for routine read-only tasks and Astra for consequential or uncertain read-only tasks, and execute through packaged Codex.
disable-model-invocation: true
---

# Veera automatic model routing

Resolve scripts/model_router.py against ${CLAUDE_PLUGIN_ROOT}. Read docs/model-routing.md. This explicitly requested route authorizes one read-only Codex delegate; Claude uses the same Codex bridge. Keep all writes and Veera owner capabilities in the parent. Do not send owner identity, capabilities, secrets or the full conversation. Do not route a denied operation through a delegate.

Write the user's bounded brief to a temporary UTF-8 task file in the authorized workspace. Execute the absolute router script using its --task-file, --cwd and --host claude arguments. The router classifies automatically: known routine tasks use gpt-6.1-sol/low; consequential, mixed or unknown work uses gpt-6-astra/high. No manual tier selection is needed. Each invocation is a fresh read-only delegate. Remove the temporary brief after completion. Return the response and selection receipt. Failed or unavailable required models block this item; never downgrade or retry automatically.

This executes the selected model for the delegate. It cannot change this host's active coordinator model. Actual model verification is reported separately from the requested model. Tasks requiring writes stay with the owning coordinator and its native model controls.

Confinement: the native read-only sandbox constrains file/shell writes. The delegate inherits configured host tools/connectors; the read-only instruction for external services is cooperative, not enforced by this plugin. Review the bounded brief and use a host tool policy that disallows mutations when strict external confinement is required. Do not send this delegate authorization to mutate an external service.
