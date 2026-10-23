# Veera 0.2.6 verification

This release adds the [automatic task lifecycle](task-lifecycle.md) and [requirements analysis](requirements-analysis.md), including a researched upfront interview and internal decision handling after implementation starts. It retains the measured runtime improvements and Sol-medium routing from 0.2.5. No further dashboard visual redesign is included.

## Source validation

- Full Python suite: **216 tests, no failures, two skipped** for Windows symlink privileges, in 151.546 seconds. Output: `artifacts/final-v0.2.6-tests.log`.
- Nine discovery tests cover answered options/free-text questions, unresolved questions, recommendations, evidence and acceptance/check references, missing project evidence, duplicate IDs, bounded records, persistence, contract tampering, legacy compatibility, escaped HTML and additive updates.
- Sixteen amendment tests include a public CLI amendment that preserves the original brief/history, rejects missing traceability and adds requirements/checks without granting time or resuming work.
- Forty Git delivery tests include successful public CLI finish/publish releasing only the owner's binding, preservation of artifacts, and creation of the next task in the same fixture session. Failure cases retain ownership; publication is not repeated after cleanup errors.
- Host adapter and Windows platform tests cover direct Build/Fix identity bootstrap, aliases, ignored lookalikes/mentions, missing host data and no fixture enrollment or project writes by bootstrap.
- Dashboard JavaScript: 11 assertions passed; document script syntax check passed. Requirements HTML uses the existing escaped record renderer and document allowlist.
- Codex Build/Fix skill validation passed. Claude-native frontmatter and the new analyst's read-only tool declaration were checked; the native Claude plugin manifest validator reports no errors/warnings. The Codex-only skill validator is not a validator for Claude's supported `disable-model-invocation` field.
- The initial full run caught a missing explicit engineering-standards document pointer in the new analyst role. The pointer was fixed, all seven affected contract checks passed, and the full suite above then passed. The initial log is retained as `artifacts/initial-v0.2.6-tests.log`.

## Installation verification

Use the native plugin managers for the user's global Codex and Claude Code installations. The installation evidence is recorded in `artifacts/install-verification-v0.2.6.json`, with package hash comparisons and actual installed hook command checks against disposable fixtures. Installed discovery, adapter and runtime-performance tests exercise the installed copies, not just the source checkout. Native plugin listings establish installed/enabled status; plugin metadata alone does not prove a live model-driven task.

A new Codex chat and a restarted Claude Code session load updated metadata. Build/Fix receives identity directly, so a separate start message is no longer required for each task. The start skill remains an optional diagnostic. Ordinary unrelated prompts do not enroll tasks.

## Evidence limits

The controller validates record shape, traceability and integrity. It cannot prove research quality, truth of source summaries, genuine user consent or actual agent consultation merely from text fields. Interview behavior and specialist decisions are skill/agent instructions. A complete model-driven production delivery and behavioral comparison of PM/Architect/Advisor were not run in this maintenance session. No independent specialist review is claimed here.

Lifecycle tests use isolated Git repositories, session registries and local remotes. Fixture identities are not live host enrollment. Hooks do not change native permissions; actual denials remain binding. No host trust changes, remote source publication, peer cleanup or source-worktree deletion is part of this release.
