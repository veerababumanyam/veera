# Veera

A new, standalone Claude Code plugin for bounded **Build** and **Fix** delivery. Fix includes diagnosis, remediation, regression testing and independent review. Veera provides skills and specialist contracts, a Python run controller, safety hooks and a live local HTML dashboard. It does not modify or depend on your existing gauntlet skills.

## Install for your Claude Code user

```bash
claude plugin install veera --marketplace veerababumanyam/veera --scope user
```

Start a new Claude Code session, then invoke `/veera:start` followed by a separately authorized `/veera:build` or `/veera:fix` request. User scope makes the plugin available across your projects; only explicitly bound sessions activate task controls. Codex adapter files are included but are not automatically installed or trusted by this command. See the host-pilot limitations below before relying on unattended delivery.

## Host integration update (0.1.5)

- Claude: explicitly submit `/veera:start` alone. A UserPromptSubmit hook returns the actual host session identity and plugin-data location to the owner's context only; it does not enroll, create a worktree or authorize publication. Start/Build/Fix are manual-invocation skills.
- Routing now uses host-provided `CLAUDE_PLUGIN_DATA/veera-v1/claude/sessions`, not the replaceable plugin directory. CLI children must receive the same actual data-directory environment if not inherited. Missing data fails before workspace creation; no silent production fallback.
- Upgrade migration is explicit and limited to one quiescent owner: `python3 scripts/ownership.py --session-id ID --root TASK --legacy-file EXACT_FILE` with the configured persistent environment. It validates owner/task identity, creates exclusively, rejects conflicts and preserves the source. Never bulk migrate or keep both old/new writers active.
- Hook error policy: unknown/unbound input returns no-op without project access; failures after exact owner-record classification deny. Host-level process startup failure/timeout uses `onFailure: continue` to avoid breaking unrelated sessions. Native host permissions/sandbox remain essential: this cannot guarantee fail-closed ownership if the interpreter never starts.
- Codex: a separate adapter lives in `adapters/codex`, with `$veera:start`, portable skills and a trusted-hook template. It uses `VEERA_HOST=codex` and a separate persistent namespace. Codex's unsupported ASK is converted to DENY; known exec commands and patch targets are normalized, unknown mutating tools denied. No trust/sandbox bypass flags or global configuration changes are used.

**Real pilot status:** the Claude CLI invocation returned a blocked result (no usable bootstrap context and contract Read permission denied); no denial was bypassed. The Codex invocation failed authentication with HTTP 401; no credentials were read/copied or retry launched. Consequently real end-to-end delivery remains **blocked**, not verified. See `docs/verification-v0.1.5.md`; local adapter tests are not a substitute for trusted host loading and permissions. Installing/authorizing hooks or credentials is a user-owned prerequisite, not something this plugin can self-approve.

## Session and project isolation (0.1.4 onward)

**Breaking safety change:** Veera hooks no longer discover runs from cwd/ancestor directories. An unbound host session is a no-op before any cwd, Git or run-state access—even in the same checkout as a Veera task. A bound session may operate only in its recorded task root, not another project or nested repository. Direct read/write tool targets are checked; arbitrary shell requires host approval because a shell is not a path sandbox.

All root-based CLI operations require `--session-id ACTUAL_HOST_ID --capability-file OWNER_FILE`; `workspace` needs the actual session ID and creates the owner routing file, while `doctor` is independent. The CLI validates ownership before reading contracts/reports or touching task state. Use the actual host-provided ID; never invent one or assume an undocumented environment variable. If the host does not expose it, setup is blocked until supplied through a supported mechanism. A fresh session must not adopt an old run automatically.

Routing is host-persistent `${CLAUDE_PLUGIN_DATA}/veera-v1/<host>/sessions/<hash-of-session-id>.json`, read by exact key only; no session enumeration, cross-project context store or global settings updates. Treat this owner file as private. Only the coordinator uses it; do not distribute controller authority to subagents. Shared host IDs do not authenticate individual agents, and same-UID code can bypass file-based controls. Use native host permissions/OS isolation for that boundary. No claim of adversarial sandboxing or independently verified host-session inheritance.

Run the owning session in the returned task worktree before preparation. Owner-bound pre-init operations may read task files and write draft evidence, not arbitrary source changes. `unbind --root TASK --session-id ID --capability-file FILE` removes only the current completed task's routing record, retaining all work/evidence; blocked tasks are not automatically unbound. Do not archive before unbinding; archive removes completion state needed by unbind.

Workspace setup no longer writes shared `.git/info/exclude` or Git config. Only untracked reserved `.veera/` and `.veera-artifacts/` paths are excluded in Veera's own queries; raw Git status may show them. Tracked files in reserved directories are rejected. Never edit shared ignore settings to hide bookkeeping from peers. Creating a linked worktree necessarily creates its task branch and Git administrative entry; that explicit operation and the repository coordination lock are the limited shared administration effects.

**No automatic local main synchronization.** If main is checked out anywhere in the repository, publish blocks before pushing without inspecting or changing that checkout. Veera will not detach, stash, merge, reset, update-ref, clean or stop anything owned by another session. When main is unoccupied, a verified task can make its one explicitly authorized remote main push; local main and all other checkouts remain unchanged. Any local synchronization is a separate owner decision. This supersedes older automatic clean-main fast-forward behavior.

## Stack-aware engineering standards (0.1.3)

Build/Fix and all specialist roles reference `docs/engineering-standards.md`. Discover the actual repository stack, supported versions, manifests/lockfiles, design system and CI checks first. Apply correctness, explicit error handling, separation of concerns, KISS/YAGNI, naming/module conventions, documentation, observability and secure configuration using that stack's idioms—not Rust tools in non-Rust projects.

UI work includes purposeful lazy loading, accessible pending/empty/error/retry states, framework-appropriate error boundaries and safe human-readable errors. Prefer existing maintained open-source libraries and current compatible stable releases; inspect licenses, security status and compatibility before adding/upgrading. Do not invent custom replacements, force ecosystem migrations, or add unused infrastructure. Requirements become applicable task acceptance checks, not a promise that generic guidance proves compliance. See the shared standard for role-specific responsibilities and evidence expectations.

### Frontend quality

The shared standard now makes the central design system the default: expressive, elegant, professional layouts; purposeful illustrations/SVGs/icons; concise copy; consistent typography/alignment; responsive interaction states; accessible tooltips and hover/focus/touch feedback. The requested masculine visual direction is interpreted as confident structure/typography where brand-appropriate, not an automatic theme or exclusionary audience assumption. Avoid generic decorative AI-looking output. Use ECharts/flow/illustrative diagrams when the application needs them, with central theming, accessible summaries/table alternatives and measured loading impact. WCAG 2.2 AA is the default target, with actual keyboard/browser/manual evidence in addition to automated checks. This is guidance for application work, not a redesign or accessibility certification of Veera's current dashboard.

### Repository hygiene and resources

Skills now require task-owned artifact/process inventories and scoped cleanup of disposable outputs. Preserve peer files, shared caches, lockfiles, worktrees, evidence and recovery checkpoints. "Old", "ignored" or "not found by search" does not prove a file is orphaned. Use bounded builds/watchers, graceful cleanup of owned processes, and valid cache reuse; never globally delete caches or kill processes by name. Disk cleanup is not a substitute for releasing memory/CPU activity. This update adds agent guidance, **not an automatic deletion daemon or new cleanup command**. Existing permission checks remain in force.

## Requirements and loading

Linux/macOS with Python 3.10+, or native Windows with Python 3.12+, Git and a supported Claude Code/Codex host. Windows uses byte-range locks and a kill-on-close job for verification children. No Python/npm dependencies or network installation are required. Use a trusted, isolated application checkout or worktree; preserve existing work. The controller requires the Git checkout root and refuses submodules/oversized fingerprint inputs rather than silently omitting them.

```bash
claude --plugin-dir /home/veera/veera --effort medium
```

Then use `/veera:build <feature>` or `/veera:fix <problem>`. Loading is session-local; no global installation is performed. Use the absolute path wherever you place this plugin. For Codex, follow `docs/model-routing.md`: Sol for light work and Astra for important work, through supported native model controls. Claude retains its selected native model. The plugin does not bypass permissions or change global model defaults.

## Central task memory and managed blockers (0.1.2)

Memory is centralized **per task**, within the existing `.veera/state.json`; not shared globally across customers/projects. The `memory-steward` role reads the task context and relevant evidence, then returns a compact update proposal. The coordinator imports it; the steward has no source/state-write, release or permission authority. Activate it at substantial handoffs, decisions or recovery points, not as an always-running agent. All roles receive the same task/context revision plus their narrow assignment.

- `context --root TASK`: compact goal/criteria/scope, current fingerprint, indexed memory summaries/freshness, blocker status and remaining limits.
- `context-item --root TASK --id ID`: retrieve one full source-linked record on demand.
- `context-import --root TASK --file PROPOSAL.json`: atomic coordinator import with task/contract identity, expected revision, expected code fingerprint and idempotent proposal ID. Stale/concurrent/cross-task updates fail without partial writes. Changed evidence is marked stale during retrieval.

Proposal shape: `{run_id, contract_hash, expected_revision, expected_fingerprint, proposal_id, steward, items:[{id,summary,kind:"fact"|"hypothesis"|"decision",text,sources:[{path,sha256}]}]}`. Source paths are relative to the task; source hashes must match. Runtime records timestamps, revisions and update history. Default limits: 100 items, 20 per import, 2000 characters per record, 500 proposal receipts. Update existing facts rather than accumulating transcripts. Store no secrets/customer data; basic sensitive-path/token detection is defense in depth, not a complete redaction system. Memory is evidence, never authority. Identity labels are attestations, not authenticated provenance.

### Blocker workflow

`blocker --root TASK --file OP.json` maintains canonical blockers by normalized family+target, not changeable error prose. Every operation supplies the actual `run_id`.

1. `open`: `{family,target,criteria:[IDs],evidence:[{path,sha256}]}`. Families: test, build, dependency, integration, runtime, requirement; permission/authentication/human-decision go immediately to human-required.
2. `attempt`: `{id,action,hypothesis,evidence}` records intent **before** acting; returns an attempt ID. Do not execute an unrecorded retry.
3. `result`: `{id,attempt_id,outcome:"failed"|"candidate-fix"|"ambiguous",evidence}`. Pending/ambiguous attempts count; duplicate reports do not reset counters. Ambiguous outcomes remain `reconciliation-required`; use `reconcile` with `{id,attempt_id,outcome:"failed"|"candidate-fix",evidence}` and new observed-state evidence before retry or resolution. No refunded attempt.
4. After at most **three** attempts (or a stricter contract limit), the affected blocker becomes escalated; unrelated eligible work remains available. Coordinator obtains actual Advisor and Architect analysis, then PM decides.
5. `decision`: `{id,owner:"pm",consulted:["advisor","architect"],choice:"alternative"|"prioritize-independent"|"human-required",plan,evidence}`. One bounded independent alternative may be selected per task, within the existing scope/deadline/global repair budget. Selection is not a fourth retry, does not resolve the blocker, and cannot reset counters. No unlimited escalations or new tasks to evade ceilings.
6. `resolve`: `{id,evidence}` requires current passing checks for the affected criteria. Final independent review must be refreshed. Unresolved blockers gate both finish and publish.

Actual human-only issues use `blocker-human-resolve --root TASK --file REPORT.json` with `{run_id,id,authorization,evidence}` after real approval; the host hook asks for confirmation. It invalidates verification and does not create credentials/permission or waive acceptance. Agent labels and JSON cannot grant authority.

Global repair default is now three; explicit older contracts retain their lower ceiling. At a v2 global ceiling the runtime records escalation rather than treating it as voluntary task completion. A PM decision with source-linked consultation evidence is required; it never increases the repair counter allowance. Every unresolved acceptance criterion still prevents delivery.

### Remote activity and GitHub Actions

Only the final controlled `publish` performs a remote write. No intermediate task-branch/tag pushes, PR creation, status/check posting or workflow dispatch are part of Veera's workflow. Local worktrees/commits and fetches do not trigger GitHub push workflows. The existing persisted at-most-one-push journal is unchanged. One push can still trigger multiple configured workflows/jobs; billing and Actions limits depend on repository configuration and cannot be guaranteed by this plugin. Do not suppress required CI to save cost. See `docs/research-task-memory.md` for sources and rationale.

## Full delivery, not partial results (0.1.1 onward)

Every new CLI task requires a Veera-owned linked worktree created from a clean checkout at exactly local `main`. No unrelated topic commits are included. Publishing additionally requires a configured authorized remote, Git identity, and an existing supported version file. Veera will not invent a remote, initialize your project, or bypass protected-branch requirements. The plugin folder itself is not an application repository.

The default **30-minute target is soft**: expiry marks a PM/Architect/Advisor replanning decision and work continues. It does not kill a check or voluntarily abandon the feature. The separate **120-minute hard safety ceiling** (or stricter project/user limit), command timeout, permissions and cancellation remain binding. There is no honest guarantee against outages or human-only blockers. Incomplete work stays isolated and must never be called DONE or published as a partial feature. No automatic renewal or lowering acceptance criteria.

Full DONE is: complete agreed implementation → integrate latest main in task worktree → patch bump → final tests and independent review → `ready` → one confirmed non-force remote publication → `complete`. `ready` is explicitly NOT DONE. Local main and peer checkouts are not synchronized or modified. Failed/ambiguous remote publication stays recorded and must not be retried automatically.

For an explicitly nonpublishing task, freeze `"delivery_mode": "local-verify"` in the contract **before init** and omit `release` entirely. The default remains `"publish"`. Local verification retains the owned-worktree, scope, behavior checks, positive test counts, current fingerprint, independent review, blocker and time gates. Implement, verify, review, then `finish` returns the terminal status `verified-local`: the local contract is satisfied, but nothing is published and no version bump or main integration is claimed. `release-prepare`, `release-reconcile` and `publish` are prohibited. This mode cannot be selected after init to rescue an incomplete release task. Preserve its worktree, evidence and session binding; automatic `unbind` and `archive` remain restricted to `complete` published tasks (and existing legacy completion semantics).

### Release rules

- `release-prepare --root TASK` commits only scoped task changes locally, fetches configured remote/main, integrates main in the task worktree, and bumps the explicit version file once. It clears old verification. Use it before final tests, never after review without revalidation.
- Only plain `x.y.z` → `x.y.(z+1)` is supported, based on integrated main. JSON `version`, a plain version file, or a literal `version` under an explicit `[workspace.package]` table in `Cargo.toml` is supported. Cargo support requires Python 3.11+ and changes only the version literal, preserving comments, line endings and other formatting; duplicate, dotted/inline, inherited and complex version forms are refused. Coupled manifests/lockfiles, prereleases and custom version schemes need a project-specific adapter; do not select one file and leave coupled versions inconsistent.
- `finish --root TASK` validates all final evidence and enters `ready`, not `complete`.
- `publish --root TASK` rechecks source/visual evidence, version and latest main, commits the verified task, journals intent, invokes exactly one plain non-force push, confirms the remote tip, and leaves local main and other checkouts untouched. No unrelated branch merges, no deletion of worktrees, no reset/force push. Any failed or ambiguous push is preserved; no automatic retry.
- Checked-out main blocks publication regardless of cleanliness; Veera does not inspect its files or change its state. Moved main or changed evidence also blocks publication. The repository lock coordinates Veera publishers only, not arbitrary external Git clients. No peer checkout or local main ref is ever updated by publish.
- If main advances **before any push attempt**, `release-reconcile --root TASK --reason TEXT` restores the uncommitted version increment, integrates current main, bumps again against that main, and requires all final checks/review again. It consumes the existing repair budget; never resets it. Conflicts require explicit resolution inside the task worktree.
- Scoped ignored/untracked application inputs are rejected upfront rather than silently omitted from the published tree. Evidence stays ignored; application inputs must be deliberately tracked before the task.

### Safe continuation

If `workspace` created the task worktree and metadata but owner enrollment failed, first resolve the reported host prerequisite through authorized means. The same original owner may then repeat the exact `workspace --root ORIGINAL --task SLUG --session-id ID` command. Recovery accepts only the unchanged recorded original/base, clean linked task worktree, matching Git registration/branch/HEAD and absent task state/binding. Current main may have advanced independently; recovery preserves the recorded base and never changes main or peers. Changed identity, source, refs, symlinks or an initialized task are refused. It enrolls exclusively and returns `recovered: true`; never manufacture metadata, replace another binding or use this path to retry a continuing denial.

`checkpoint --root TASK --reason TEXT` persists an exact source fingerprint and checkpoint ID. `resume --root TASK --file REPORT.json` requires `{checkpoint_id, authorization, reason, additional_minutes}`. It preserves original start/history/repair counters, invalidates prior checks and rejects stale checkpoints or any prior push attempt. A new hard-time allowance requires actual user authorization (host hook asks); JSON text itself is not proof of approval. Routine soft-target replanning uses `decision`, not resume or a fresh run. Legacy v1 saved runs retain their original semantics; the public CLI creates only v2 worktree/release runs.

## Delivery contract

The PM owns scope and budget decisions. The Architect assesses dependencies and implications; the Advisor proposes smaller alternatives. They consult on material tradeoffs, not every tool call. Their decisions are recorded; the controller enforces the frozen user-authorized envelope. PM can reprioritize work and allocate remaining time, but cannot silently increase the deadline, scope or repair ceiling. New authority requires a human decision, not agent consensus.

Every run freezes a contract before implementation, with scope, measurable criteria, required check commands, non-goals and a maximum of three repairs by default. UI contracts require local visual references and a visual evidence check. Store pre-init plans/contracts and later review/decision artifacts under `.veera-artifacts/`, excluded only by Veera's own task queries and never containing secrets. This directory is for evidence only, not application code. Do not change shared Git exclusions/configuration. Run state itself lives in `.veera/`; reserved tracked source is rejected rather than hidden.

Example contract (replace the command with the application's real selected tests):

```json
{
  "scope": ["src/discount.py", "tests/test_discount.py", "VERSION"],
  "non_goals": ["No deployment", "No unrelated refactoring"],
  "criteria": [{"id": "C1", "text": "Valid discounts apply and invalid discounts are rejected", "checks": ["discount-tests"]}],
  "checks": [{"id": "discount-tests", "argv": ["python3", "-m", "unittest", "tests.test_discount", "-v"], "kind": "test", "count_pattern": "Ran (\\d+) test", "timeout_seconds": 120}],
  "ui": false,
  "max_repairs": 3,
  "release": {"remote": "origin", "branch": "main", "version_file": "VERSION", "push_authorized": true}
}
```

A check uses an argument array, never `shell=True`. Commands are trusted project code, not sandboxed. Inspect scripts before authorizing execution; an argument array does not make a malicious script safe. Test count extraction must match the real runner's summary; zero/missing counts fail closed. For static checks use `kind: static`. For visual checks use `kind: visual` with `artifacts: [".veera-artifacts/screens/after.png"]`; the command must generate fresh nonempty artifacts. File presence proves capture, not visual quality: the designer/reviewer must inspect them.

```bash
# ID must be the actual host session ID, not a guessed environment variable.
python3 /home/veera/veera/scripts/delivery.py workspace --root /path/to/app --task discount-fix --session-id ACTUAL_HOST_ID
# Use the returned task root and capability_file; run from that task root.
python3 /home/veera/veera/scripts/delivery.py init --root /path/to/app-veera-discount-fix --mode fix --request "Fix discount validation" --contract /path/to/contract.json --minutes 30 --hard-minutes 120 --session-id ACTUAL_HOST_ID --capability-file RETURNED_OWNER_FILE
python3 /home/veera/veera/scripts/delivery.py dashboard --root /path/to/app-veera-discount-fix --session-id ACTUAL_HOST_ID --capability-file RETURNED_OWNER_FILE
```

The dashboard prints a random, loopback-only capability URL. Run the server in a host-tracked background task if continuing in the same session. It shuts down 60 seconds after a terminal run state. It reports real events, budget, checks, repairs, decisions and stale activity. Stop cancels controller-managed checks and prevents further hooked execution; it cannot revoke an already-running external tool/model request. Do not publish the dashboard URL or its contents.

### Controller commands

Append `--session-id ACTUAL_HOST_ID --capability-file RETURNED_OWNER_FILE` to every root command below. They are mandatory, including reads/status. `doctor` needs no ownership arguments.

- `phase --root ROOT --name plan|implement|verify|review`: ordered phase transitions.
- `check --root ROOT --id CHECK`: run the frozen command, bounded by its timeout and the remaining deadline. Kills the process group on timeout/cancel; caps captured output.
- `fingerprint --root ROOT`: current code identity for the independent reviewer.
- `review --root ROOT --file REPORT.json`: record `{reviewer, fingerprint, approved: true, criteria: [IDs], notes}`.
- `decision --root ROOT --file DECISION.json`: record `{owner: "pm", consulted: ["architect", "advisor"], decision, reason}`.
- `repair --root ROOT --reason TEXT`: enter a bounded new implementation attempt; provide a changed hypothesis or new evidence.
- `finish --root ROOT`: require all check evidence and the review to match current code, no scope drift, and an unexpired budget.
- `stop --root ROOT --reason TEXT`: stop without claiming completion.
- `status --root ROOT`: inspect saved state, refreshing deadline status.
- `doctor`: local prerequisite report; not an application or model test.

A run cannot be reset by invoking init again. Archive a verified completed run with `archive --root ROOT` before intentionally beginning a separately authorized task. Incomplete/blocked runs cannot be archived by this command; they require explicit human disposition of saved state. Do not archive/re-init to renew an unfinished task's budget. Failed commands remain recorded. No automatic scheduler, nested model loop, hidden retries or production deployment.

## Safety and evidence boundaries

**Enforced by controller:** contract checksum, phase order, repair ceiling, absolute deadline on managed checks, serialization, captured execution results, code fingerprints, scope drift detection, and required evidence before finish. State is local and mutable by its owner: checksums detect accidental modification, not a malicious user rewriting both data and hashes.

**Defense-in-depth hooks:** direct file-tool scope restrictions, protected settings/secrets/run state, terminal-state execution stops, and common dangerous command patterns. Hooks do not parse every shell language, sandbox subprocesses, enforce network policy, or stop arbitrary already-running host tools. Claude Code permissions and the host sandbox remain the security boundary. Never use bypass-permission modes. Hooks activate only for the explicitly bound host session. Unbound sessions do not inspect or mutate project state; bound sessions are restricted to their recorded task root. Arbitrary shell requires host approval, not a promise of sandbox enforcement.

**Fingerprint coverage:** tracked and non-ignored repository files plus ignored files within the explicit frozen scope. Include any ignored application configuration/input that affects acceptance in that scope. Ignored dependencies/build products outside scope, external services, environment variables and fixtures are not attested; reviewers must validate those separately. Evidence-directory exclusions must never conceal application code.

**Agent responsibilities, not proof by themselves:** standards research, architecture quality, meaningful acceptance criteria, independent reviewer identity, PM consultation, and visual assessment. Review identity is an attestation, not authenticated provenance. Required human approvals, legal/product decisions and human UAT cannot be supplied by agents. Passing automated acceptance is not deployment authorization.

Continue eligible authorized work without routine "shall I proceed?" pauses. Stop at a real permission denial, unresolved human-only decision, budget ceiling, user stop or verified done state. Never lower gates to fit the budget.

## Context and prompting

Optimize unnecessary context, not necessary reasoning or evidence: keep the system/project brief stable, put changing task state after it, reuse the same specialist session for follow-ups, and send file references plus changed facts rather than full transcripts. Use targeted impact maps and local search before broad reads. Store raw test logs once and return bounded summaries with evidence paths; read full failure details when necessary. Batch independent lookups; do not respawn agents to answer questions the current context already settles. Before compaction save the exact task/worktree, criteria, decisions, latest code identity, remaining budget and next action; revalidate stale facts on resume. Do not shrink context by dropping security requirements, negative test cases or independent review.

Use a small stable repository/decision packet with source references and a separate changing checkpoint. Reuse existing sessions for focused follow-ups, read targeted files, invalidate stale facts, and use available context for relevant evidence rather than dumping entire repositories. "Think carefully" means check assumptions and alternatives at consequential decisions and return concise reasons, not hidden chain-of-thought. Prompt caching is host/provider-managed: this plugin makes no cache-hit, token-cost or context-size guarantee. The dashboard displays unknown telemetry as unknown. No automatic embeddings or cross-project memory.

## Verification and limitations

```bash
python3 -m unittest discover -s /home/veera/veera/tests -v
node --check /home/veera/veera/web/app.js
claude plugin validate /home/veera/veera --strict
python3 /home/veera/veera/tests/browser_smoke.py
```

Runtime tests use disposable Git repositories and local subprocesses, not production applications. Browser smoke testing uses installed Chrome headless, including a screenshot; it is not a full accessibility audit. See `docs/verification-v0.1.4.md` for current results and remaining gaps; earlier verification documents preserve previous version records. No real-application autonomous delivery, PM/Architect/Advisor behavioral comparison, universal security guarantee or industry-leading performance claim is implied by runtime unit tests.

## Local v0.1.6 installation repair

The `.codex-plugin/plugin.json` manifest selects `adapters/codex/skills` and `adapters/codex/hooks.json`; Claude retains its own manifest and hooks. Codex commands are `$veera:start`, `$veera:build`, and `$veera:fix`. Review and trust the installed Veera hooks through `/hooks`, then submit `$veera:start` as a standalone prompt. Bootstrap returns actual host identity, persistent data directory, installed package root and Python executable. Installing does not grant hook trust. Start the session in the intended Git checkout. Native Windows requires Python 3.12+ for nonblocking pipe reads.

## Model management (v0.1.7)

Codex bootstrap includes the Sol/Astra policy in `docs/model-policy.json`. GPT-6.1 Sol with low reasoning handles light work; GPT-6 Astra with high reasoning handles consequential work. See `docs/model-routing.md` for classification, native model controls, opt-in profiles, unavailable-model behavior and Claude limitations. Policy injection is not automatic coordinator switching.

## Automatic Sol/Astra routing in Codex

After installing the plugin, run `python3 PACKAGE/scripts/install_codex_routing.py` as an explicitly authorized setup step (PACKAGE is the installed Veera directory). It registers the two personal roles and the actual Python interpreter without changing parent permissions or model defaults. Open a new Codex session and invoke `$veera:route` with a bounded findings-only brief. Veera classifies the item and dispatches native Sol low or Astra high subagents, then waits for results. The shell never starts a nested Codex process. See `docs/model-routing.md` for scope, evidence and Claude bridge limitations.
