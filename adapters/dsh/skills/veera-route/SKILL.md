---
name: veera-route
description: Automatically select deepseek-v4-pro with high effort for important work or deepseek-flash with high effort for routine work in DeepSeek Harness, and dispatch a native subagent with that model.
---

# Veera automatic model routing (DeepSeek Harness)

Resolve `scripts/model_router.py` against the package root (`$VEERA_ROOT`, else `C:/Users/VeeraDesktop/Desktop/veera`) and read `docs/model-routing.md`. An explicitly requested route classifies one bounded read-only brief; the parent keeps all writes and owner capabilities. Do not send owner identity, capabilities, secrets or the full conversation. Do not route a denied operation through a delegate.

Write the bounded brief to a temporary UTF-8 task file, then run:

`python scripts/model_router.py --task-file <brief> --cwd <dir> --host dsh`

The router classifies automatically: important work (consequential or uncertain) selects `deepseek-v4-pro` with high reasoning effort; routine work selects `deepseek-flash` with high reasoning effort. It returns a `subagent` dispatch carrying `provider`, `model` and `reasoning_effort` — start that child with the returned values (findings-only; the parent keeps writes). If the current session's `subagent` tool does not expose `provider`/`model`/`reasoning_effort`, the host subagent model selection setting is not enabled for this session: report the required selection and ask the user to enable it, never silently substitute one model for the other. A required model that cannot be applied blocks the item.
