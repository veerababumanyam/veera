# Model routing

The user preference in `model-policy.json` applies to Veera tasks in Codex. Read it at bootstrap and before classifying each substantial work item. User instructions for the current task override these defaults.

| Work | Model | Reasoning |
| --- | --- | --- |
| Discovery, summaries, docs, formatting, small routine edits, established checks, memory updates | `gpt-6.1-sol` | `low` |
| Architecture, security, permissions, migrations, difficult diagnosis, concurrency, production changes, final release review | `gpt-6-astra` | `high` |

Choose by consequence and uncertainty. A short security change is important; a long mechanical formatting task may be light. Mixed work uses Astra for the consequential portion and returns to Sol for routine follow-through. Do not automatically select max/ultra, run both models on everything, or escalate only because a check failed. Respect existing bounded-repair limits.

## Applying the selection

Model policy is not a runtime model switch. At an already-authorized delegation, explicitly pass the selected model and supported reasoning effort through the actual host tool. If the host requires a fresh context to override the model, supply the bounded task brief and source pointers rather than copying the full conversation. Preserve the existing specialist permissions and never share the owner capability. This policy alone does not authorize delegation, concurrent edits, independent sessions or spending outside the task.

For coordinator-owned important work, use the host's supported model selector when available. In a user-controlled Codex session, select the requested model with `/model` or the composer before that portion. Do not invent a tool, rewrite global defaults mid-task, restart the owner or report a successful switch without host evidence. If Astra is unavailable, report the prerequisite and keep only unrelated light work moving; do not silently downgrade important work.

The local installation provides opt-in `veera-light` and `veera-important` Codex profiles. Start a new light session with `codex -p veera-light -C CHECKOUT`; use `-p veera-important` for an important session. Profiles set the coordinator model and effort. Per-delegation selections still apply. Do not start a second session to adopt an already bound task.

For another installation, copy the two templates from `adapters/codex/profiles/` into your Codex home (normally `~/.codex/`), preserving their filenames. Review any existing files before replacing them. These opt-in profiles apply across projects and do not change the default model for unrelated sessions.

Claude-native agents keep their selected Claude model. Sol/Astra routing is only active on hosts that expose those model IDs. A separate supported provider mapping requires user configuration; this plugin does not create one.

## Evidence

Record the work item's classification and brief reason with its existing handoff or decision evidence. Record the actual model only when the host exposes it; otherwise mark it unverified. A model name in an artifact is not proof of independent review or a reason to waive acceptance checks.

References: [Codex subagent model controls](https://learn.chatgpt.com/docs/agent-configuration/subagents), [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

## Automatic execution (0.2.0)

Invoke `/veera:route` in Claude or `$veera:route` in Codex with a bounded read-only brief. Both installed plugins expose this skill globally. The runtime is `python3 PACKAGE/scripts/model_router.py --host codex|claude --cwd CHECKOUT --task-file BRIEF.txt`. `--plan` classifies without a model call.

The runtime applies risk-first deterministic classification. Recognized routine briefs select Sol; consequential terms, mixed tasks and unknown briefs select Astra. A failure never selects a cheaper fallback. It calls the packaged Codex CLI with explicit model/effort, read-only sandbox and no approval bypass. Claude requires an installed, signed-in Codex CLI for these OpenAI delegates; it does not impersonate a Claude-native model or install a gateway.

Every item has a fresh context and does not resume or adopt an existing owner. The receipt distinguishes selection from verification using only the exact newly created Codex session's native turn context. No model is allowed to assert its own identity as evidence. Tasks that need writes remain with the coordinator. The plugin cannot automatically change the active Codex/Claude chat model through a hook; this feature automatically switches delegate execution, not the composer selection.

Confinement: the native read-only sandbox constrains file/shell writes. The delegate inherits configured host tools/connectors; the read-only instruction for external services is cooperative, not enforced by this plugin. Review the bounded brief and use a host tool policy that disallows mutations when strict external confinement is required. Do not send this delegate authorization to mutate an external service.

Host validation on Windows: direct router execution verified both model choices in native Codex turn records. A nested invocation from a restricted Codex shell failed; the bridge does not relax that shell policy. Claude-host validation is pending because its account returned HTTP 429 weekly usage_limit_reached. Thus installation and direct runtime verification do not establish end-to-end availability in every host session. If the host exposes model-aware native delegation, use the router --plan result with that supported control under existing delegation authority. Otherwise report the unavailable integration; never launch outside a denied sandbox to work around it.
