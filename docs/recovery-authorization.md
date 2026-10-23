# Explicit recovery authorization

Only the existing owner uses these commands with the normal `--root`, `--session-id`, `--capability-file`, and, when needed, `--host codex --plugin-data` arguments. Approval references record actual human authorization; they cannot authenticate it or override native permission controls. Never edit state or owner records manually.

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
