# Veera 0.2.7 startup repair

## Confirmed cause

The Codex bootstrap parser recognized plain commands but ignored a leading desktop skill link such as `[$veera:start](.../0.2.5/adapters/codex/skills/start/SKILL.md)`. The reported error also cited the obsolete 0.2.5 cache path while the native plugin manager listed 0.2.6. The old instructions incorrectly treated missing output as grounds to request hook trust and another start-only message.

A native Codex 0.163.0 `hooks/list` query for this project reported both Veera hooks enabled and trusted, with matching existing hashes and no loading errors. Trust was not the confirmed cause. The official [hook contract](https://learn.chatgpt.com/docs/hooks) and [plugin packaging documentation](https://developers.openai.com/plugins/build/plugins) were consulted for the supported input, output, environment and trust behavior.

## Repair

- Recognize leading Codex skill links and surrounding whitespace, including valid older Veera cache paths. Treat the target only as an invocation hint; never load or execute it.
- Keep quoted/examples/unrelated/external/traversal links inactive and continue requiring actual host identity/data. Return the running package version in bootstrap output.
- Add opt-in native hook inspection to `codex_compat.py --host-status --cwd PROJECT`. It initializes a short-lived metadata process and calls only `hooks/list`; it creates no chat/model/delivery or trust/config changes.
- Replace the automatic trust/start retry prescription with [startup troubleshooting](startup-troubleshooting.md). Package capabilities remain readable even when activation is not verified.
- Preserve existing hook definitions and native trust records. Claude's slash-command behavior is unchanged.

## Validation

- The new regression suite failed against the old parser, reproducing the reported linked-command failure. After the fix, all five invocation tests pass.
- Six host-diagnostic tests cover trusted, disabled, modified, missing and mismatched hooks, rejected/malformed metadata, foreign plugin filtering, unavailable executables, bounded timeout cleanup and the exact read-only request sequence.
- The actual Windows hook command accepts the old-version linked-start fixture, with no enrollment or writes in its disposable data directory.
- Full Python suite: **227 tests, no failures, two Windows symlink tests skipped**, in 157.069 seconds. Log: `artifacts/final-v0.2.7-tests.log`.
- Dashboard JavaScript: 11 assertions passed. Codex Build/Fix/Start skill validation and native Claude manifest validation passed. No dashboard behavior was changed.
- Installed-copy verification is recorded in `artifacts/install-verification-v0.2.7.json`; the original linked-start prompt is used against the installed Windows hook command. Native status is rechecked from the installed package after the supported global update.

Native metadata verifies current configuration, not the reload state of an already-open chat. Installed hook execution tests use disposable fixtures and do not claim a model-driven production delivery. Existing chats that retain obsolete skill context may need one reload/new chat; there is no requirement for a separate start message on each Build/Fix task.
