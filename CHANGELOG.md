## 0.3.2 — 2026-10-23

- Fix the live Codex worktree startup failure: canonical Bash events report chat cwd and omit execution workdir. Stop treating that field as proof of execution location; preserve actual owner/state validation, known file-target scope checks and native permissions. Check effective workdir when the host supplies the original execution arguments.
- Allow absolute, scoped file operations from projectless chats while retaining foreign/nested/protected target denials. Keep Claude's cwd checks unchanged. Reconcile shared automatic-start guidance with the installed Build/Fix entry behavior.

## 0.3.1 — 2026-10-23

- Preserve inherited host access when creating Windows session, task-state and archive directories. Python 3.13+ interprets Unix-style `0700` as a protected Windows DACL; Veera now leaves Windows directory access to the parent ACL while retaining private POSIX modes.
- Cover enrollment, migration, archives, unchanged existing permissions and propagated host denials with regression tests. Existing inaccessible directories still require host-authorized access restoration; the update does not rewrite ACLs, relocate registries or adopt blocked tasks.

## 0.3.0 — 2026-10-23

- Start Build/Fix automatically from ordinary task requests in Codex and Claude Code; explicit commands remain optional. Follow-ups reuse the current task, and questions or opt-outs do not enroll one.
- Enable Claude's automatic Build/Fix selection. New automatically routed work defaults to local verification unless publication was requested.
- Recover actual identity through the existing PreToolUse hook when a tool-created desktop chat reads the installed Build/Fix skill without a prior user-prompt event. Preserve existing hook definitions, trust and guard decisions.

## 0.2.7 — 2026-10-23

- Recognize Codex desktop skill links and surrounding whitespace, including stale Veera cache links, while retaining host-provided identity and using the running package version.
- Add an opt-in, read-only native hook-status diagnostic. Missing context no longer means capabilities are unavailable or hooks necessarily require trust.
- Replace repetitive start-only recovery guidance with evidence-based startup troubleshooting. Existing hook definitions and trust settings are unchanged.

## 0.2.6 — 2026-10-23

- Add researched requirements discovery, a read-only requirements analyst, and an upfront interview with evidence-based options and recommendations before planning. PM/Architect/Advisor handle eligible decisions internally after implementation starts.
- Validate frozen discovery traceability and append-only amendments; display requirements and the plan in the existing HTML dashboard.

- Direct Build/Fix and dashboard commands receive host identity in the same prompt; the separate start command is optional.
- Successful public CLI completion automatically releases the current chat's task binding while preserving worktrees and records. Incomplete work retains recovery state. Cleanup errors never trigger another publication.

## 0.2.5 — 2026-10-23

- Avoid unchanged state rewrites on the status/guard hot path while preserving fresh integrity, ownership and deadline validation; repeatable local measurements are in `docs/performance.md`.
- Build/Fix starts the live dashboard before implementation, opens it in the browser, and provides its saved address on request through `dashboard-info` and the dashboard skill.
- The dashboard retains a validated per-task address and reuses one server; stale URLs are not presented as live.
- Routine GPT-6.1 Sol routing now uses medium reasoning effort in policy, role and profile configuration.

## 0.2.4 — 2026-10-23

### Fixed
- Codex follows existing native permissions without Veera's extra interactive approval gate. Controller recovery reuses actual recorded authorization while retaining owner, checkpoint, scope, state and evidence validation.
- No import-time host namespace mutation; protect Codex settings, permit adapter documentation reads, and normalize every hook decision consistently.
- Correct terminal stop controls and distinguish missing timing from measured values.

### Added
- Validated, frozen upfront intake for user consent, project inputs, assumptions and delegated internal decisions.
- Independent package diagnosis without requiring Veera delivery bootstrap.
- Redesigned live dashboard with responsive navigation and safe HTML task/handbook documents, search and linked subdocuments.

## 0.2.2

### Fixed
- Codex model routing now dispatches native Sol/Astra subagents instead of launching a nested CLI inside the restricted shell. Adds a safe global role installer and preserves parent permissions.

## 0.2.0

### Added
- Automatic risk-first Sol/Astra execution for bounded read-only delegates, available in both hosts through the route skill. Includes native model receipts, failure handling and a Codex bridge for Claude. Active coordinator model selection remains controlled by the host.

# Changelog

## 0.1.7 â€” 2026-10-22

### Added
- Native Codex manifest selecting the Codex skills and hooks, including a Windows hook command.
- Sol/Astra task-routing policy: GPT-6.1 Sol for light work and GPT-6 Astra for important work.
- Portable light/important Codex profile templates. Profiles remain opt-in; the policy does not itself switch an active coordinator's model.
- Bootstrap context includes the installed package root and Python executable. Codex bootstrap also provides its model-routing policy.

### Fixed
- Native Windows runtime compatibility: file locking, bounded pipe capture, and verification-child cleanup through Windows jobs. Windows requires Python 3.12 or later.
- Windows path comparisons and shell-path parsing, plus UTF-8 documentation checks.
- Codex skill discovery and namespaced start trigger; the legacy `$veera-start` bootstrap trigger remains accepted.

### Activation
- Install and enable Veera in user scope to make it available across projects. Start each task in its intended Git checkout.
- Codex hooks require native trust review before live bootstrap. An installation or test fixture does not establish a live session's identity.
- Claude-native agents retain the selected Claude model; the GPT routing policy applies to Codex.
