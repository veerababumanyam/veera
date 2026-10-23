# Runtime performance

Measured on Windows with Python 3.14.7 on 2026-10-23. These measurements cover local controller overhead, not model inference, network latency or full delivery time.

## Status writes were the measured bottleneck

Every `status()` call previously serialized, flushed and replaced the whole run state, even when nothing changed. This path is used by the owner guard before tool execution and by status polling. Profiling identified these repeated writes as a substantial cost.

`status()` now persists only a real soft/hard-deadline transition. It still takes the task lock, reads fresh state, validates the frozen contract hash and checks deadlines every time. No authorization, permission or state cache was introduced. All normal mutations retain durable writes.

| Local measurement | Before median | After median | Samples per comparison |
| --- | --- | --- | --- |
| Status read | 9.00–9.06 ms | 0.83–0.84 ms | 100 |
| Owned hook handler, existing Python process | 15.11–16.06 ms | 6.74–6.75 ms | 100 |
| Full hook subprocess, including Python startup | 79.26–81.27 ms | 72.19–75.36 ms | 25 |
| Native route classification | 0.287–0.292 ms | 0.288–0.302 ms | 100 |

Two before/after comparisons used the same isolated Git task with 51 events, three warmups and the same sample counts. The repeated baseline used installed 0.2.4. The large status/handler reduction was repeatable; full-process improvement was smaller because Python startup remains. Routing was already inexpensive and was left unoptimized. No inference-speed claim follows from changing Sol reasoning effort to medium.

## Reproduce and guard

Run `python tests/benchmark_runtime.py --output artifacts/performance-current.json`. Use `--package ABSOLUTE_INSTALLED_PACKAGE` to compare an installed version with the same fixture. The benchmark creates and removes its own temporary task and routing registry; it does not access live owner records or invoke models.

`tests/test_runtime_performance.py` prevents unchanged reads from reintroducing disk writes, verifies deadline transitions persist exactly once, and checks that subsequent reads still reject contract tampering. Timing values are recorded instead of enforced as brittle wall-clock assertions on shared machines. Retain before/after JSON and its cumulative profile under local `artifacts/` for future comparisons.

Optimization ledger: conditional status persistence **kept** after repeatable improvement and correctness checks. No caching or router rewrite was attempted because it was not supported by the measurements. Live production latency remains to be observed during actual use.
