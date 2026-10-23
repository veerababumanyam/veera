# Automatic Veera model routing

Veera selects gpt-6.1-sol with medium reasoning for recognized routine findings-only briefs, and gpt-6-astra with high reasoning for consequential, mixed or uncertain work. User instructions take precedence. Classification uses conservative full-brief matching; consequential terms override routine terms. Each bounded item is classified anew, so subsequent routine work returns to Sol.

## Codex native integration

The Codex adapter adds no separate shell-approval requirement. Classifier execution and native delegation use the existing host permission policy and the frozen upfront user intent. The parent retains owner capabilities, task decisions and all writes; actual host denials remain binding.

Invoke `$veera:route` with a bounded brief. The installed skill runs `scripts/model_router.py --host codex --cwd CHECKOUT --task-file BRIEF.txt` to classify locally. It returns a dispatch descriptor; it does not launch another Codex process. The parent uses the native subagent tool with the selected role, waits for completion and returns findings. On hosts exposing explicit model/effort overrides, use those exact selected values with a fresh context instead of a role.

Install the native role templates globally with `python3 PACKAGE/scripts/install_codex_routing.py`. This backs up and preserves existing Codex settings, registers only veera_light and veera_important, and pins each role's model/effort. It refuses unmanaged name collisions and explicitly disabled subagent policy. It changes no parent model, sandbox, approval or other agent defaults. Newly created sessions load the roles. Roles must be available to the current host; missing native tools or disabled delegation blocks the item without a nested CLI fallback.

The old nested CLI implementation failed inside a Windows restricted shell because the child tried to initialize another Codex runtime under that shell's filesystem/network restrictions. Native subagent dispatch is performed by Codex itself. The shell performs local classification only, without authentication, network, private session access or process spawning.

Native subagents inherit the parent's permissions, approvals, provider and tool access. Findings-only behavior is cooperative: these role instructions do not create a separate read-only sandbox or restrict mutating connectors by themselves. Keep all writes, credentials, owner capabilities and task decisions in the parent. Do not use delegation to perform a denied operation. An owner must not share its capability or bootstrap identity. This policy does not authorize additional spending or release actions.

## Claude bridge

Claude's `/veera:route` continues to use the packaged, signed-in Codex CLI for OpenAI delegates, with explicit model/effort and a native read-only command sandbox. This requires the Claude host's existing permissions to allow it. A denied launch remains denied; no gateway or permissions bypass is installed. Claude-native models and coordinator selection remain unchanged. Claude-host validation was blocked by HTTP 429 weekly usage_limit_reached on October 22; that is independent of native Codex routing.

## DeepSeek Harness routing

The `veera-route` skill classifies the bounded brief with the same conservative matching and returns a DeepSeek selection: `deepseek-v4-pro` with high reasoning effort for important work, `deepseek-flash` with high reasoning effort for routine work. The coordinator dispatches one native `subagent` carrying the selected `provider`/`model`/`reasoning_effort`; the parent keeps all writes and owner capabilities. This requires the host subagent model selection setting (`subagent-model-selection-settings`, `enabled: true`) to list those exact routes — the profile patch ships it. When the current session's `subagent` tool does not expose those fields, report the required selection instead of claiming to switch the coordinator. No Codex child, gateway, or permission bypass is introduced. A required pro/flash selection that cannot be applied blocks the item rather than silently downgrading to the other model.

## Evidence and failures

Selection and dispatch are not completion. Wait for the native result and record selected role, model, actual child ID and completion. Verify the model from native runtime turn context for only the exact newly created child session when available. Never inspect other owners or accept a delegate's self-description as model evidence. If unavailable, report verification as unavailable. Do not downgrade required Astra work or silently substitute another model. Model policy does not waive independent review, correctness checks or task limits. The active coordinator/composer model remains controlled by the host.

Reference: [Official Codex subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Requirements analysis

For underspecified/consequential Build/Fix work, supply the requirements-analyst brief and relevant source pointers before planning. Codex uses the existing important native findings-only role; Claude can use the packaged native `requirements-analyst` under its selected Claude model. This requires no extra always-running service or model startup on unrelated prompts. Record actual delegation or coordinator fallback honestly, as described in [requirements analysis](requirements-analysis.md). Independent final review remains a separate obligation.
