# Veera 0.3.2 live qualification

On 2026-10-23, a fresh native Codex desktop chat completed an ordinary software request through the globally installed Veera workflow. It implemented a calculator function, updated tests/documentation, passed seven tests, obtained a real independent native review, reached `verified-local`, and automatically released its session binding. No activation command, remote configuration or publication was used.

## Two actual failures repaired

The existing Codex sessions directory was owned by `CodexSandboxOffline` and had inheritance disabled. A one-time operator repair used normal Windows UAC administrator consent and `icacls /inheritance:e` on that exact directory only. The saved before/after evidence confirms unchanged owner and explicit access entries. A subsequent ordinary-token probe successfully created, wrote, read and deleted its own temporary file. This was an environment repair; the plugin does not elevate or rewrite ACLs automatically. Version 0.3.1 already prevents the directory-creation defect from recurring.

The first fresh session then reproduced a second failure: Codex's canonical Bash hook reports chat cwd and omits execution workdir, so Veera rejected a valid command targeting its newly created worktree. The [upstream report](https://github.com/openai/codex/issues/32360) and [hook implementation](https://github.com/openai/codex/blob/main/codex-rs/core/src/hook_runtime.rs) describe this context limitation.

Version 0.3.2 preserves exact owner/state checks and known file-target protections without treating chat cwd as proof of canonical Bash execution location. Original execution arguments retain workdir validation when exposed. Relative patch paths keep their native chat-relative meaning. Native host permissions govern opaque shell/tool effects. Claude's cwd checks are unchanged. The shared contract now consistently describes automatic entry.

## Fresh native Codex result

- Chat: `01a167f7-d33c-75e2-8ffd-028db422eb5c`, “Veera 0.3.2 fresh-session end-to-end qualification”.
- Original: `C:/Users/VeeraDesktop/Documents/Codex/veera-e2e-223d4955/calculator-v032`.
- Owned task: sibling `calculator-v032-veera-calculator-mean-v032`, branch `veera/calculator-mean-v032`.
- Actual changes: `mean(values)` with empty-list rejection, preserved `total`, six new tests and README instructions.
- Verification: seven tests passed on fingerprint `946bb1246b98581434e9191a41454b7da6670fdee58a2360b714cbff66466d34`.
- Independent reviewer: `/root/independent_review`, invoked through native collaboration using the `veera_important` role. The host did not independently expose the actual runtime model; no stronger model claim is made.
- Controller status: `verified-local`; binding release was confirmed by the finish result and absence of the exact generated owner record.
- Dashboard: started before implementation. The real browser displayed the passing test count, completed status and rendered independent-review subdocument. Its process stopped after the terminal grace period while `.veera/dashboard.json` and task evidence remained.
- Original checkout stayed clean; no remote was configured and no publication occurred.

The delivery receipt is `C:/Users/VeeraDesktop/Documents/Codex/2026-10-23/veera-full-delivery-v032/outputs/delivery-receipt.json`. The earlier failed 0.3.1 qualification and its binding remain preserved, as does the separate BPA checkpoint/worktree; this maintenance did not adopt or execute those tasks.

## Claude Code limitation

A fresh native Claude Code process loaded 0.3.2 automatically from its configured local marketplace package. The hook session identity matched the fresh session. Its first model request returned HTTP 429 `usage_limit_reached`, with reset reported as 2026-10-26 at 07:00 Europe/Berlin. No permission denial was reported. Claude is updated, but complete model-driven delivery remains unverified until account capacity is available. Codex success is not represented as Claude success.

## Regression and installation checks

- Full Python suite: 245 tests, 242 passed, three platform skips, no failures, in 144.873 seconds.
- Cwd regressions failed before the fix and passed afterward, including retained foreign/nested/protected target, wrong owner and terminal-state denials.
- Eight targeted modules passed against each installed cache; runtime/skill files matched source. Actual installed hook-command fixtures passed on both hosts.
- Native Codex metadata reported both 0.3.2 hooks enabled/trusted, with no loading errors. Existing native approval configuration and hook definitions were preserved.
- Both Codex Build/Fix skills and the Claude marketplace manifest validated successfully.

Detailed local evidence is under `artifacts/`: `session-inheritance-repair-result.json`, `session-inheritance-normal-token-verification.json`, `codex-cwd-before.log`, `codex-cwd-after.log`, `final-v0.3.2-tests.log`, `install-verification-v0.3.2.json`, `host-hooks-installed-v0.3.2.json`, `fresh-v0.3.2-cleanup.json` and `fresh-claude-e2e-v0.3.2.jsonl`.
