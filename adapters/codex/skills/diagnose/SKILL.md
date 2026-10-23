---
name: diagnose
description: Explain Veera package and Codex compatibility failures without starting the delivery controller or requiring bootstrap.
disable-model-invocation: true
---

# Diagnose Veera without activating it

Use ordinary permitted native tools for this read-only diagnostic request. Do not invoke start/build/fix, enroll a workspace, inspect session registries or request an owner capability. This skill is an alternative for investigation and planning, not for executing a denied operation.

Resolve the package root from this skill's location. Read `adapters/codex/README.md`, especially Supported behavior and unavailable operations. If a native shell command is permitted, run the package's `scripts/codex_compat.py` with an available Python 3.12+ interpreter. This diagnostic reads only package files, makes no writes and never invokes the delivery controller. Do not fabricate environment variables or bootstrap identity. If shell execution is denied, stop that action and report the documented limitation without retrying it through a different tool.

Compare the user-provided error to package files and the host's exposed facilities. Distinguish missing Python, missing files, unsupported tools, missing trusted bootstrap and approval incompatibility. Do not read unrelated chats, owner records or private host configuration. Do not install dependencies, change hook trust, modify permissions, start agents or change source as part of diagnosis.

Return confirmed findings, remaining uncertainty, package version/path, the next supported step and checks actually performed. `files-present` is only a package check, not proof that hooks loaded or that a real task works. Native approval and sandbox controls remain binding. Veera does not add an interactive approval gate on Codex. Actual host permissions and controller ownership/state validation remain in force; diagnostic output itself grants no new authority.

For missing startup context, follow `docs/startup-troubleshooting.md` and use `scripts/codex_compat.py --host-status --cwd PROJECT` when permitted. This explicit option performs a bounded native metadata query; it starts no chat/model and changes no trust or settings. Return package capabilities even when activation is unverified. Distinguish trusted hooks with missing context, stale cached versions, unavailable metadata and actual review-required status; do not send the user into a repeated start/trust loop.
