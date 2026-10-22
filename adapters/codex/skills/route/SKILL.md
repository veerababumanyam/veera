---
name: route
description: Automatically route routine findings-only work to Sol and consequential or uncertain work to Astra through native Codex subagents.
disable-model-invocation: true
---

# Veera native model routing

Resolve the package root from this installed skill location or trusted Veera bootstrap. Read docs/model-routing.md. An explicit route request authorizes one bounded findings-only delegate. Keep owner capabilities, identity, full conversation, writes and decisions in the parent. Never delegate a denied operation.

On Windows use the trusted bootstrap `python_executable` if available. Otherwise read the public installer metadata `$CODEX_HOME/veera-routing-runtime.json` (default `~/.codex/veera-routing-runtime.json`) for the actual `python_executable`, and invoke that absolute interpreter. Do not assume `python3` is on the restricted shell PATH. This file is public runtime configuration, not ownership state. If missing, report installation incomplete.

1. Use the supplied UTF-8 brief file, or write a bounded brief in authorized workspace scratch space. Run `python3 PACKAGE/scripts/model_router.py --host codex --cwd CHECKOUT --task-file BRIEF.txt`. This is local classification only: it never starts nested Codex. It returns `dispatch_required`, selection and a dispatch descriptor.
2. Use the exposed native subagent tool. On Codex CLI pass the descriptor's `agent_type` (veera_light or veera_important), `message` and `fork_context=false` to `spawn_agent`. The globally installed role pins model and effort. On a host exposing explicit model/effort instead, pass selection.model and selection.reasoning_effort with fresh context (fork_turns="none"). Do not inherit full history or substitute another model. Native tools must be available and delegation allowed; otherwise report that prerequisite and stop.
3. Wait for the native delegate result using the host's wait tool. Do not report dispatch_required as successful execution. Return its findings and selected role/model. Mark actual model unverified unless native runtime evidence confirms it; an agent's claim about its own model is not proof.

Run `scripts/install_codex_routing.py` only as part of an explicitly authorized installation to register the two global roles. If roles are missing in an existing session, use a new session after installation; never edit defaults mid-task or launch a nested CLI from a restricted shell.

Subagents inherit the current sandbox, approvals and tools. Findings-only behavior is an instruction, not a separate read-only sandbox or connector restriction. Retain native permission boundaries. The active coordinator model is unchanged. This route automatically selects the delegate's execution model, not the composer model. On failure stop this item; never fall back, loosen permissions or route around a denial.
