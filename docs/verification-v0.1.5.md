# Veera v0.1.5 host integrations

## Scope and identity

Staged under `/home/veera/veera`, baseline `artifacts/baseline-0.1.4.zip` preserved. No active user configuration changes, hook-trust bypass, credentials migration, unrelated session/project access or external Git publication. User authorized one scoped pilot per host without a monetary cap; this did not authorize permission/authentication bypasses.

Candidate manifest: `artifacts/candidate-v6-sha256.json`, aggregate `c6d43a267c4fcd671a5d75330e78aaab36d2cf2673ba9bf54506027ccd31517a`. Artifacts, session data, bytecode and verification documents excluded. Claude Code 2.1.307, Codex CLI 0.153.0, Python 3.12.3, Git 2.43.0 on Linux.

## Implemented and locally tested

- Exact explicit Claude `/veera:start` UserPromptSubmit bootstrap: actual hook session ID/data location to owner context, no enrollment/writes. Near-match prompts ignored. Start/Build/Fix manually invoked.
- Host-persistent routing under `CLAUDE_PLUGIN_DATA/veera-v1/<host>/sessions`; absent configuration refuses setup; explicit test injection only, no production fallback.
- Exact one-owner legacy migration, owner/workspace validation, exclusive destination, idempotent identical retry, original preserved. Old owner must be quiescent; not enforced against arbitrary same-UID writers.
- Owner-aware hook handling: unknown/unbound malformed input does not interfere; exact-owner failures explicitly deny. Host-level process startup/timeout uses continue to avoid global interference; native permissions remain necessary.
- Separate Codex adapter: `$veera-start`, distinct namespace, exec normalization, patch target validation, unsupported ASK translated to DENY, malformed owner inputs denied. Trusted hook configuration is a prerequisite, not installed by these files.

`python3 -m unittest discover -s /home/veera/veera/tests -v`: **102 passed**, 8.434 seconds, exit 0; `artifacts/unittest-v6.log`. Seven host-adapter tests cover exact trigger, no writes, missing persistence, owner/unbound failures, malformed JSON, namespaces/migration, unsupported ASK and malformed Codex tool input. Remaining tests preserve existing runtime/isolation/engineering checks.

`claude plugin validate /home/veera/veera --strict --json` and `.../skills --strict --json`: passed, exit 0; `artifacts/plugin-validation-v6.json`, `skills-validation-v6.json`. `node tests/test_web.js`: six assertions passed; `artifacts/web-test-v6.log`. These are static/local checks, not live hook certification.

## Real host pilot results — BLOCKED, not completed

Identical disposable calculator repositories/local bare remotes prepared by `harness-probe` under `artifacts/host-pilot/{claude,codex}`. Initial implementation subtracts instead of adds; both positive/negative tests genuinely failed before execution. Plan/invocations/raw setup output: `artifacts/host-pilot/plan.json`. That setup document records the baseline label, not the later candidate identity above.

Claude actual command: `claude --plugin-dir /home/veera/veera --setting-sources project --effort medium --permission-mode dontAsk --tools Read --output-format json -p /veera:start`, cwd the disposable Claude repo. Host exit 0, 4.752 seconds; result explicitly BLOCKED because usable bootstrap context was missing and contract Read denied. No bypass/retry. Model label reported by the configured host was `gpt-6-astra`, not evidence of an Anthropic-model run. Reported cost about $0.03681, basis unknown; do not infer total/provider billing guarantees. Raw `claude/bootstrap.stdout.json`, `bootstrap.stderr.log`, `bootstrap-result.json`.

Codex actual command: `codex exec --ignore-user-config --ephemeral --sandbox read-only --json -C <codex fixture repo> <scoped prerequisite prompt>`. Exit 1, 14.630 seconds; HTTP 401 missing authentication. CLI itself retried/reconnected and fell back transports; coordinator did not launch another attempt or access credentials. Raw `codex/pilot.stdout.jsonl`, `pilot.stderr.log`, `pilot-result.json`.

Independent post-run assessment by `harness-probe`: `artifacts/host-pilot/assessment.json`. Both fixture repositories/file hashes, detached HEAD, local main and local remote main remain at `0abdd20d4f65ab100b1bfa08b4b3eee4736a64af`. Both acceptance tests still fail in each repo; VERSION stays 0.0.1; no delivery worktree exists. Task delivery was **not run**. Fixture preservation passed. Host integration effectiveness is **inconclusive**.

The missing live prerequisites cannot be safely self-approved: Claude trusted hook loading/context and contract-read permission, plus Codex authenticated provider/trusted hooks. A successful full delivery pilot remains necessary after actual user setup. Do not present blocked pilot results or unit-test success as completed cross-host integration.

## Review, sources, limitations

`harness-proposer` designed the integration correction; `harness-composer` staged entry skills and Codex guidance; `harness-probe` prepared and independently assessed fixtures without model calls; coordinator executed the two host invocations and local tests; `harness-critic` reviewed adapter code. Critic found Codex trigger documentation mismatch and malformed owned tool input escaping denial; fixed and added targeted regressions. Final narrow critic verdict: accept-for-tested-scope for these two corrected defects. Explicitly not acceptance of live-host integration; no additional local execution requested for closure.

Official sources consulted: https://code.claude.com/docs/en/hooks ; https://code.claude.com/docs/en/skills ; https://learn.chatgpt.com/docs/hooks ; https://learn.chatgpt.com/docs/build-skills ; https://learn.chatgpt.com/docs/agent-configuration/agents-md . Installed CLI help inspected for supported flags; no guessed Codex local-plugin loader or trust bypass used.

Engineering correctness/boundaries/KISS/stack-native idioms/operability guidance remains unchanged. Same-UID authentication, host trust, live skill invocation and model behavior are not established by adapter tests. Migration is not a universal transactional upgrade manager. Status: **locally tested staged candidate; real host end-to-end checks blocked; no active promotion**.
