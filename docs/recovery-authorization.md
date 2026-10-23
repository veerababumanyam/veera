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


## Rebinding a frozen check to a new campaign

Use `rebind-check-inputs --root TASK --file REPORT.json` when historical campaign files must stay at their original paths and a finalized new campaign has permanent unique paths. Never archive-and-replace the old files, rewrite their embedded references, or reseal historical receipts. This command writes controller state only; it does not copy, move or rewrite any evidence file.

Only the two values of the existing `--manifest` and `--results` arguments may change. The controller derives the new check; the report cannot provide a replacement command. Check ID, kind, Python executable/flags, verifier path, count pattern, timeout, scope, criteria and performance acceptance remain identical. The new evidence must be a complete matching live matrix, but the command does not declare it verified or infer a performance win. The original verifier must run against it after recovery.

The owner prepares this exact report while active, then stops and uses the standalone recovery invocation:

```json
{
  "run_id": "CURRENT_RUN",
  "checkpoint_id": "CURRENT_CHECKPOINT",
  "expected_contract_hash": "CURRENT_CONTRACT_HASH",
  "check_id": "EXISTING_TEST_CHECK",
  "expected_check_hash": "CURRENT_CHECK_OBJECT_DIGEST",
  "expected_checks_hash": "CURRENT_STATE_CHECKS_OBJECT_DIGEST",
  "authorization_id": "ACTUAL_HUMAN_MESSAGE_REFERENCE",
  "authorization": "Actual authority for the necessary input-path update",
  "reason": "Preserve historical campaign evidence at original paths",
  "verifier": {"path": "bench/comparison/native_campaign.py", "sha256": "CURRENT_VERIFIER_FILE_HASH"},
  "prior_inputs": {
    "manifest": {"path": ".veera-artifacts/campaign-manifest.json", "sha256": "OLD_FILE_HASH"},
    "results": {"path": ".veera-artifacts/campaign-results.json", "sha256": "OLD_FILE_HASH"}
  },
  "inputs": {
    "manifest": {"path": ".veera-artifacts/final-campaign/manifest.json", "sha256": "NEW_FILE_HASH"},
    "results": {"path": ".veera-artifacts/final-campaign/results.json", "sha256": "NEW_FILE_HASH"}
  },
  "review": {
    "reviewer": "ACTUAL_SEPARATE_REVIEWER",
    "notes": "Evidence-backed assessment of input provenance and unchanged acceptance",
    "approved": true,
    "fingerprint": "CURRENT_SOURCE_FINGERPRINT",
    "prior_check_hash": "CURRENT_CHECK_OBJECT_DIGEST",
    "new_check_hash": "DERIVED_NEW_CHECK_OBJECT_DIGEST",
    "binding_hash": "BINDING_OBJECT_DIGEST"
  }
}
```

Use the object/file hashing conventions above. `expected_checks_hash` covers the entire current `state.checks` object. Derive the new check by deep-copying the old check and replacing only `argv[-3]` and `argv[-1]` with the new manifest/results paths. `binding_hash` covers exactly `{"verifier": report.verifier, "prior_inputs": report.prior_inputs, "inputs": report.inputs}`. The reviewer must assess these exact old/new specifications, source fingerprint and file pins, including the new campaign's own supervisor/build/raw-evidence provenance. Do not invent reviewer findings. The old input JSON bytes are pinned without trying to re-execute an obsolete historical build.

Sequence:

1. Finalize the new campaign at unique permanent paths. Preserve every old campaign file and receipt. Run the unchanged verifier directly against the new paths and retain its output as supplementary evidence; this does not satisfy the old frozen check.
2. If the current controller result for this check is failed, record an explicit bounded repair after that failure. Remaining repair allowance is required; the rebinding operation does not spend, reset or extend counters.
3. While active, checkpoint the current source, compute the report hashes and obtain the separate input-equivalence review. Stop without source or evidence changes, then invoke `rebind-check-inputs` with the normal owner/host arguments and no shell redirection.
4. Resume using already authorized remaining time (zero additional minutes when the existing deadline suffices), handle the existing replan requirement, and run the rebound check. A missing stdout count still fails; rebinding does not apply the count adapter.
5. For that fresh count-only failure, follow the separate bounded-repair, checkpoint, review and `correct-check-reporting` procedure above with the new paths. Resume, rerun all required checks and obtain fresh final review.

The task must be stopped v2 work with an exact current checkpoint and no running check or push attempt. Stale identities/results/hashes, replayed authorization, malformed or reused paths, missing files, a reporting-corrected check, and exhausted repair allowance fail closed. This intentionally does not rebind a check after its counting correction: select finalized evidence first.

Each `input_rebindings` receipt retains the complete prior contract/hash, prior/new check, new contract hash, prior checks/review, authorization, reviewer evidence and all file pins. The current contract hash changes because its two arguments change; all other contract fields remain identical. All checks/review invalidate. Status, checkpoint, deadlines, spent repairs, repair grants, blocker records and spend remain unchanged. Before and after fresh checks, and at finish/publication, the controller checks the new pins and all historical input pins at their original paths. A changed historical file blocks verification; an archive copy is not a replacement for the original reference. These checks preserve the input-file records, not a claim that obsolete historical binaries remain executable.
