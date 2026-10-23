# Veera 0.2.5 verification

This update retains the repairs documented in [0.2.4 verification](verification-v0.2.4.md), adds the requested Sol-medium setting and dashboard opening/address workflow, and prioritizes the measured runtime improvement in [performance](performance.md).

## Validation

- Full Python suite: **201 tests, no failures, two skipped** for Windows symlink privileges. Output: `artifacts/final-v0.2.5-tests.log`.
- Dashboard lifecycle: four targeted tests passed again after strengthening malformed saved-record handling. They cover automatic browser-launch invocation, headless operation, server reuse, live-address recovery, stale address rejection and external-address rejection. Browser opening is mocked at the OS boundary in these lifecycle tests; prior real-browser rendering checks are documented in 0.2.4.
- Dashboard JavaScript: 11 assertions passed; document script syntax check passed. No further visual redesign in this release.
- Routing: bootstrap, automatic classification and role installation tests passed; routine briefs require GPT-6.1 Sol with medium effort and role settings must match the policy. Astra remains high.
- Performance: two equivalent isolated before/after comparisons show median status reads around 9.0 ms becoming 0.84 ms; full hook subprocess latency including Python startup improves more modestly, around 7–9%. No model latency claim.
- Fresh state/contract validation, one-time soft/hard expiry persistence and absence of unchanged state writes have dedicated regression tests.

## Global use

The native plugin manager installs Veera in the user's global plugin cache and keeps it enabled, making the skills available across projects. Its normal role installer updates only the managed Veera role files and preserves unrelated Codex configuration. The requested Sol setting belongs to `veera_light`; the active coordinator is not silently switched. A new Codex chat loads the updated role/skill metadata.

Build/Fix skill orchestration starts and opens the local dashboard after task init and before implementation. The saved address can be retrieved through the new dashboard skill or `dashboard-info`. Bare library initialization does not spawn a browser or service. See [dashboard behavior](dashboard.md).

The tests use isolated local fixtures, not live owner data. No complete live model-driven production delivery or independent specialist review is claimed. Native host permissions and per-project instructions still apply.
