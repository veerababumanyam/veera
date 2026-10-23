# Explicit recovery authorization

Only the existing owner uses these commands with the normal `--root`, `--session-id`, `--capability-file`, and, when needed, `--host codex --plugin-data` arguments. Approval references record actual human authorization; they cannot authenticate it or override native permission controls. Never edit state or owner records manually.

In a stopped Codex run, invoke the controller as a standalone command, including PowerShell's `&` when needed. Do not append redirection, pipelines or shell chains: those are deliberately outside the recovery exception. The controller persists its own receipts. A successful recovery operation can still return exit code 1 with state JSON when the task remains `blocked` or `budget-exhausted`; inspect its recorded receipt before retrying.

## Additional global repair rounds

`extend-repairs --root TASK --file REPORT.json` accepts exactly:

```json
{
  "run_id": "CURRENT_RUN",
  "checkpoint_id": "CURRENT_CHECKPOINT",
  "expected_contract_hash": "CURRENT_CONTRACT_HASH",
  "expected_limit": 3,
  "expected_repairs": 3,
  "additional_repairs": 20,
  "authorization_id": "ACTUAL_HUMAN_MESSAGE_REFERENCE",
  "authorization": "Actual approval for twenty additional global repair rounds",
  "reason": "Remaining authorized work"
}
```

The task must be stopped v2 work, with a matching current source checkpoint, no running check or prior push attempt. Stale counters/hash/checkpoint, duplicate authorization IDs, unknown fields and nonpositive/noninteger additions fail without writing. Never reuse one human authorization under a new ID.

The frozen base contract remains unchanged. Append-only `repair_extensions` receipts record the previous and effective limits, spent rounds and full authorization. Effective allowance is the original ceiling plus these grants: base 3 plus 20 becomes 23, with 3 already spent. Existing failed checks, logs, blocker attempts, per-blocker/per-piece limits and spend remain intact. Review is invalidated. This does not resolve any blocker or resume work.

Time is separate. The grant leaves the deadline unchanged. Apply it first, then the owner uses `resume` with the authorized `additional_minutes` and a matching `time_plan`. A positive extension uses `max(current_time, existing_deadline) + additional_minutes * 60` at successful resume, so an expired run receives the full new allowance at that point. Failed validation saves no new deadline. No stopped time is deducted from the new allowance before resume. Time alone never grants repair rounds.

The existing additive `amend` operation still cannot change repair ceilings or acceptance. Claude requests its usual native approval for this authority-sensitive operation; Codex passes through to existing host policy and controller validation.

## Correcting a verifier's missing count

`correct-check-reporting --root TASK --file REPORT.json` supports one declarative adapter, `verified-json-matrix`. This is a counting correction, not permission to change the frozen command, test kind, timeout, criteria, performance requirements or scope. The original Python verifier must already accept `verify --manifest RELATIVE_PATH --results RELATIVE_PATH` (optionally Python `-B`). Its unchanged execution remains responsible for all substantive evidence validation. A complete valid comparison matrix does not imply a performance win.

The owner must have a current failed result with exit code 0, zero count, no capture/source-change error, and the same source fingerprint as the stopped checkpoint. Record an explicit bounded `repair` after that failure; the correction itself never spends, resets or extends a counter. Remaining global repair allowance is required. For a newly optimized source, produce a fresh failure at that source instead of reusing an old failure. Obtain a separate review that explains why the original pinned verifier checks every counted matrix row and why the adapter preserves acceptance. Actual human authorization must cover the reporting correction.

Prepare hashes and the report while the task is active: failed check, bounded repair, checkpoint, independent equivalence review and report, then stop and invoke the correction as a standalone command. Stopping preserves the checkpoint. This avoids asking the stopped-state guard to execute a hashing script; do not loosen the guard to prepare recovery inputs.

The report has exactly these fields (hashes use lowercase SHA-256):

```json
{
  "run_id": "CURRENT_RUN",
  "checkpoint_id": "CURRENT_CHECKPOINT",
  "expected_contract_hash": "CURRENT_CONTRACT_HASH",
  "check_id": "EXISTING_TEST_CHECK",
  "expected_check_hash": "CHECK_OBJECT_DIGEST",
  "expected_result_hash": "CURRENT_FAILED_RESULT_OBJECT_DIGEST",
  "log_sha256": "RAW_FAILED_LOG_HASH",
  "authorization_id": "ACTUAL_HUMAN_MESSAGE_REFERENCE",
  "authorization": "Actual reporting-correction approval",
  "reason": "Original verifier validates the matrix but emits no count",
  "adapter": {
    "kind": "verified-json-matrix",
    "verifier": {"path": "bench/comparison/native_campaign.py", "sha256": "FILE_HASH"},
    "manifest": {"path": ".veera-artifacts/campaign-manifest.json", "sha256": "FILE_HASH"},
    "results": {"path": ".veera-artifacts/campaign-results.json", "sha256": "FILE_HASH"}
  },
  "review": {
    "reviewer": "ACTUAL_SEPARATE_REVIEWER",
    "notes": "Evidence-backed equivalence assessment",
    "approved": true,
    "fingerprint": "CURRENT_SOURCE_FINGERPRINT",
    "check_hash": "CHECK_OBJECT_DIGEST",
    "adapter_hash": "ADAPTER_OBJECT_DIGEST"
  }
}
```

Object digests use the controller's existing `digest`: SHA-256 of Python `json.dumps(value, sort_keys=True).encode()`. File and log hashes cover raw bytes. Never invent a review or reuse an authorization under a new ID. Evidence paths are canonical task-relative paths, with no links, nested projects or protected state/credential paths; each pinned file must be nonempty and at most 8 MiB. The verifier must be included in the source fingerprint. The manifest and results paths must exactly match the frozen arguments.

The adapter expects a shared nonempty `campaign_id`, `results.live: true`, and a manifest with distinct nonempty `engines`, distinct positive integer `concurrencies`, and positive integer `repetitions`. The count is derived from their Cartesian product, with zero-based repetitions. Results must contain exactly one `runs` row per `(engine, concurrency, repetition)`, with no missing, duplicate or additional keys. This is a live-case count, not a fabricated stdout/unit-test count; there is no literal expected count in the report.

The controller appends the complete authorization, review, prior check specification and failed result to `reporting_corrections`, retains the original log/events, and invalidates checks/review. The task stays stopped and its deadline, contract, counters, blockers and spend remain unchanged. Use the existing separately authorized resume path, then rerun every required check and obtain fresh final review. Check execution validates all pins before and after the unchanged command, and records the derived count only for exit 0 with complete capture and unchanged source. `finish` and publication revalidate the pins and correction receipt. Changed evidence, stale receipts or command failure cannot pass. Apply this to finalized campaign evidence: this command cannot silently rebind an already corrected check to new campaign files.
