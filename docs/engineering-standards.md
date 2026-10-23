# Veera engineering standards

Veera v0.1.4 shared guidance, applicable to the detected repository tech stack. Session-isolation/hygiene correction is untested; guidance and packaging tests are not evidence of application-level standards compliance.

## Applicability and authority

- Apply only standards relevant to the authorized task's language, changed boundaries and risks. Read the applicable sections before planning or reviewing; cite sections rather than copying this checklist into every handoff.
- Native/project instructions, repository conventions, frozen acceptance, permissions and the shared agent contract remain binding. These standards do not authorize migrations, dependencies, new services, extra verification budgets or broader audits.
- Discover the affected stack from manifests, lockfiles, toolchain/runtime configuration, existing modules and CI. In polyglot repositories apply each module's conventions; do not infer one language's rules for the whole repo. Inspect the relevant language/framework's official documentation at supported versions. UI and service guidance applies only when those surfaces are affected.
- Before contract lock, map relevant risks and observable criteria to proportionate checks. After lock, report newly discovered gaps to the coordinator without rewriting scope or weakening criteria. Not applicable, blocked and not run are distinct from passed.
- Follow the shared contract's Session isolation section: only the bound coordinator owner uses the CLI; specialists receive allowed task evidence and narrow permissions, never its capability. Actual host subagent inheritance is unverified, not authentication. No unrelated session discovery/contact, other projects, global settings or automatic adoption/repair of old runs. Specialists return routing needs to the coordinator; no re-delegation or all-agent fan-out.
- Preserve bounded attempts/repairs, task memory and independent review. Complete delivery is the verified task plus one confirmed authorized remote main push, not local main synchronization. Main checked out anywhere blocks publish before push without reading/altering that checkout; never detach, stash, merge or update-ref peers to unblock it. Local main refs/checkouts stay untouched; only the user may separately synchronize their own session.

## Correctness and domain models

- Represent domain concepts with types, explicit invariants and validated construction; make invalid states difficult to express. Validate untrusted input at boundaries and test meaningful edge cases and transitions.
- Use the stack's idiomatic domain types, enums/tagged unions, validated records/classes or schema-backed values for distinct identifiers, units and mutually exclusive states. In dynamically typed code, use the project's validation/type-hint conventions rather than assuming annotations validate runtime data. Avoid primitive confusion or boolean soup; do not add types without a real distinction.
- Handle owned closed state sets exhaustively using compiler/type-checker support or explicit transition tests. Avoid broad fallbacks that hide missing owned cases. External extensible states require a deliberate safe unknown-case fallback for forward compatibility.
- Make failures explicit using the project's error idiom: typed results, returned errors or specific exceptions with preserved causes. Distinguish domain failures from transport/storage errors and attach context at boundaries. Never silently discard errors, catch everything and claim success, or return success-shaped defaults on failure.
- Avoid unchecked casts, non-null assertions, unsafe indexing, unnecessary unwrap/expect, panic or fatal exits in recoverable paths. Production exceptions require a justified invariant and impact review; assertions in tests are appropriate. Input/network/storage failures are expected cases. Contain failures safely at FFI, worker, process and request boundaries as the stack requires.

## Boundaries and simplicity

- Separate API/transport validation and representation, domain rules, persistence mapping, and external integrations. Domain code must not depend on HTTP or ORM types; translate at the edges and keep side effects explicit.
- Follow existing dependency direction and repository file/module conventions. Separation is a responsibility boundary, not a mandate to add directories, crates, interfaces or services for a tiny change.
- Use KISS and YAGNI: the smallest clear solution to the actual requirement, not speculative extension points. Prefer cohesive functions/modules, explicit data flow and composition over unnecessary abstraction.
- Refactor only when needed for the authorized outcome or safe comprehensibility, with behavior-preserving checks. Do not mix adjacent cleanup into a fix or require an architecture rewrite as a completion gate.
- Use consistent, descriptive domain names, units and state terminology. Organize files by the repository's established responsibility/feature structure; avoid misleading generic helpers and broad renames unrelated to the task.

## Stack idioms, naming and execution safety

- Follow the detected language/framework's official API conventions and repository formatter/linter configuration for names, visibility, imports, ownership/lifetimes, async patterns and public contracts. Keep terminology and units consistent. Do not apply Rust casing, tooling or ownership patterns to other ecosystems.
- Follow existing feature/module layout, entry-point conventions and tests placement. Keep cohesive files with clear responsibilities; avoid generic dumping-ground utilities, circular dependencies, global mutable state and deep cross-layer imports. No mandatory folder template or file-size quota.
- Document public behavior, invariants, errors, side effects and relevant safety conditions; add useful examples/doc tests where proportionate. Explain non-obvious constraints rather than narrating obvious code.
- Use the repository's configured formatter, linter, type checker and test runner with the supported runtime/compiler versions and relevant feature/target matrix. Never install a new toolchain just to enforce this document. Report missing tools as prerequisites, not passed checks.
- Stack examples below are options to verify in the repository, not unconditional commands or required dependencies:

| Detected stack | Applicable idioms and existing-tool examples |
| --- | --- |
| Rust | Newtypes/enums, Result/?, justified unwrap/unsafe only; Rust API Guidelines, cargo fmt/Clippy/tests using the project's toolchain/MSRV/features. Avoid incompatible all-features or blanket restriction lints. |
| TypeScript/JavaScript | Discriminated unions and runtime input validation; handle rejected promises; project ESLint/formatter, tsc if configured, actual unit/browser runner. Avoid any/non-null escape hatches without justification. |
| Python | Domain dataclasses/models as appropriate, specific exceptions and context managers; project Ruff/Black or alternatives, mypy/Pyright if configured, pytest/unittest. No new validator for trivial internal data. |
| Go | Small domain structs/interfaces, explicit wrapped errors and checked returns; gofmt, configured vet/lint, go test and race tests where warranted; no panic for routine failures. |
| JVM / .NET | Domain types/records and enum/sealed states where supported, nullability and resource disposal; established Gradle/Maven/dotnet formatter/analyzer and test tasks. |
| Other stacks | Inspect native project commands and official language/framework guidance; never substitute another ecosystem's tools. |

- Minimize unsafe/native interop and dynamic escape hatches. Document necessary local safety obligations and verify affected boundaries; lint success is not safety proof.
- For async/I/O paths, define timeouts, cancellation behavior, cleanup and bounded concurrency/queues/resources. Keep blocking work off event loops/executors using established project facilities; do not add runtimes or unbounded tasks to hide latency.

## Operability and human-friendly errors

- For affected service paths, use existing structured logging, tracing/spans and useful metrics to explain failures and latency. Carry safe correlation/request IDs through boundaries; avoid duplicate error logging and noise. No new observability platform for an unrelated local change.
- Keep metric label cardinality bounded; do not label by raw user/request IDs or arbitrary errors. Logs/traces must not expose secrets, credentials or sensitive PII. Public errors must not expose raw stack traces or internal implementation details.
- Validate configuration early with secure defaults and actionable diagnostics. Use existing secret/config mechanisms; never hardcode credentials or silently fall back to insecure behavior.
- Distinguish liveness (process can continue) from readiness (can serve required work). Health responses reveal only necessary information; checks are cheap, bounded and side-effect-free, not mutations or intrusive dependency probes.
- Give users meaningful pending/failure explanations and a safe next action; include a safe correlation ID where useful while retaining root causes in restricted diagnostics. Do not swallow errors, report false success or retry forever.
- Retry only transient failures within existing authorization/attempt ceilings, with bounded backoff and cancellation. Ensure idempotency or deduplication before retrying side effects; reconcile ambiguous outcomes instead of repeating writes blindly.

## UI and loading behavior

- Follow the existing framework and design system, semantic controls, accessibility and responsive conventions. Define meaningful pending/loading, empty, success, error and retry states for affected interactions; preserve focus and accessible feedback.
- Use lazy loading/code splitting or deferred dependencies only for a measured benefit on the affected path, balanced against complexity, loading failures and user latency. Missing measurements mean benefit is unverified, not a reason for speculative dependencies or broad benchmarks.
- Use framework-appropriate error boundaries around recoverable rendering surfaces. Know their limits: asynchronous work and event-handler errors often require explicit handling outside those boundaries. Offer safe recovery without hiding failures or an endless reload/retry loop.
- Verify relevant viewports, keyboard/focus behavior and affected state transitions with the project's permitted rendered/browser evidence. Source inspection or a screenshot alone does not prove interaction or accessibility behavior.

## Frontend craft, central design and accessibility

- Central design system first: inspect shared tokens, components, typography, spacing/grid, icon family, illustrations, motion and chart themes. Reuse them across pages; no isolated colors, random radii, competing icon sets or one-off interaction patterns. If the system is missing/incomplete, propose the smallest approved shared addition before implementation, not an invented replacement platform.
- Aim for professional, emotionally engaging, expressive, illustrative, elegant, modern and intuitive UI with clear hierarchy and restrained visual confidence. Interpret the requested masculine direction as strong structure, confident typography and purposeful contrast where compatible with the brand/audience—not exclusionary gender assumptions or an automatic dark theme. Product purpose and existing brand take precedence over fashionable decoration.
- Avoid generic AI-looking output: no arbitrary gradient blobs, repetitive cards, excessive badges, empty hero copy, mismatched stock illustrations or gratuitous animation. Use app-specific content, meaningful states and intentional composition. "Beautiful" is evaluated against approved references and an explicit rubric, never a fabricated industry-best score.
- Prefer concise plain-language labels, scannable information, progressive disclosure and useful SVG/iconography over verbose prose. Use text where recognition or decision clarity requires it; icons must have accessible names and unfamiliar actions should retain visible labels. Decorative SVGs are hidden from assistive technology; sanitize untrusted SVG and do not embed executable markup.
- Tooltips and contextual help supplement—not replace—essential labels, instructions, errors or values. Show them on keyboard focus as well as hover; support touch through an explicit equivalent. Hover/focus content should be dismissible, hoverable and persistent as required; do not trap focus or make essential actions discoverable only on hover.
- Use purposeful hover, focus, selected, pressed and disabled feedback. Motion should explain state transitions, be lightweight and honor reduced-motion preferences. Avoid autoplay distraction, surprise navigation, jank or animations that impede input. Handle interrupted/loading interactions predictably.
- Establish a consistent type scale, readable line lengths, aligned baselines, spacing rhythm and clear content density. Verify long/short/localized text, empty data, overflow and zoom; do not rely on a single ideal screenshot. Responsiveness is content-driven across narrow, medium and wide viewports with appropriate touch targets, not merely shrinking desktop layouts.
- Use ECharts or the project's established visualization/flow-diagram library when data relationships, trends, processes or architecture genuinely benefit. Prefer existing dependencies; additions require compatibility/license/security/size review and authority. Do not use charts or diagrams as filler. Share central palettes/type/spacing and lazy-load heavy visualization modules only when justified.
- Charts and diagrams need meaningful titles, units, labels, legends and summaries; never encode meaning solely by color. Provide accessible text/table alternatives and keyboard-accessible controls where interactive. Tooltips must not be the only way to read values. Validate loading, empty, partial, error and dense-data states, resize/dispose lifecycle, and representative data; do not fabricate analytics.
- Default accessibility target is WCAG 2.2 AA, unless stricter project requirements apply. Plan affected criteria before lock: semantic structure, accessible names/roles, keyboard order/actions, visible non-obscured focus, contrast, non-color cues, text resizing/reflow, input labels/errors, target size/spacing, drag alternatives and accessible authentication where applicable. Check criterion-specific exceptions rather than blanket numerical rules.
- Minimum contrast generally follows 4.5:1 normal text, 3:1 qualifying large text and 3:1 necessary non-text controls/graphics, with applicable exceptions. Check real themes/states, not tokens alone. Honor reduced motion as a product requirement without mislabeling AAA-only criteria as AA. Use semantic native controls before custom widgets and preserve focus through dialogs/errors/loading.
- Before implementation, ground new/changed flows in actual central components and approved screenshots/mockups or scoped wireframes; enumerate interaction and responsive states. Before final review, inspect rendered screenshots and actual keyboard/touch/browser evidence, plus automated accessibility checks where available. Automated scans/screenshots alone do not establish WCAG conformance or excellent UX; report manual review gaps honestly.
- Do not add an always-on design committee or expand every fix into a redesign. PM locks task-relevant UX/accessibility criteria; designer guides visual/interaction choices, implementer builds with shared components, and independent reviewer evaluates actual evidence. Record reusable decisions in central task memory; preserve original acceptance, resource limits and one-final-push policy.

## Repository hygiene and resource ownership

- Plan task-owned temporary outputs, build artifacts, test fixtures and services before creating them. Record absolute paths/process or service identities, purpose, owner, retention need and cleanup method in task memory. Use the repository's established output/cache locations; never scatter binaries, logs or generated files through source folders.
- Inspect only the authorized task working tree before and after work, never peer checkouts or unrelated runs/projects. Keep only intentional task changes; distinguish generated outputs from handwritten source and pre-existing changes. An ignored, old-looking or unreferenced file is not proof of disposal safety. Do not infer orphan status from one text search: dynamic loading, manifests, packaging and external users may reference it.
- Before init, the bound owner reads only its own task/plugin documentation and writes only draft `.veera-artifacts/`, not source. Claude shell tools use applicable native approval; Codex uses existing host policy without an extra Veera ASK gate; global ListAgents enumeration is blocked. Owner unbind requires completed task state and removes only its exact routing file; do not automatically archive beforehand or delete state/evidence/worktrees.
- Workspace creates its own branch/worktree without shared `.git/info/exclude` or Git config changes. Only runtime-owned queries skip reserved UNTRACKED `.veera/` and `.veera-artifacts/` paths; tracked reserved source is rejected. Raw Git status may show bookkeeping: never edit shared ignores to hide it or put implementation there. Shared Git metadata for owned worktree/branch operations and a narrow coordination lock is inherent, not broader cleanup authority.
- Automatically clean only demonstrably task-created, exclusively owned, no-longer-needed temporary files/directories and obsolete outputs within the authorized workspace. Inspect targets immediately before removal; check resolved paths, symlinks, ownership and active consumers. Never follow a symlink outside task scope or run broad recursive deletion, `git clean -xfd`, global cache wipes or home/system cleanup.
- Remove obsolete task-owned binaries only after replacements are verified and no process/test/recovery step needs them. Keep required regression logs, screenshots, task memory, final evidence, lockfiles and rollback checkpoints under the existing retention rules. Task worktrees/branches remain preserved by Veera's release policy; cleanup does not authorize deleting them.
- Reuse valid authorized task-local build/dependency/browser caches. Prune exclusively task-owned entries only when stale/corrupt or required by an explicit storage budget, using a scoped mechanism within the owned workspace. Do not inspect, prune, repair or manage shared caches or another session's outputs. Leave unrelated old repository files untouched. Do not sacrifice reproducibility or trigger repeated expensive rebuilds to make folders look empty.
- Bound build/test workers, concurrency, output size, watchers and background services to available resources and project limits. Avoid simultaneous redundant builds. Stop only task-owned processes/services after their last consumer finishes, using recorded identities and graceful shutdown; never kill by a broad name/port pattern or stop the shared application instance.
- Filesystem deletion primarily reclaims storage, not RAM/CPU. Releasing memory, file handles, timers, subscriptions and CPU work requires lifecycle-safe disposal and stopping owned activity. Measure relevant resource pressure before claiming an improvement.
- Before final verification, perform permitted source/output hygiene, then rerun affected checks if cleanup changes inputs or generated artifacts. After success/failure, release owned transient resources while retaining required evidence and recoverability. Report removed items, retained caches/evidence and blocked cleanup honestly. No extra remote commit/push solely for cleanup; intentional tracked deletions belong in the task's one verified final delivery.
- If deletion exceeds the preceding authorized, proven-owned disposable-output conditions, ownership is uncertain, a path lies outside the owned workspace, or a shared consumer may exist, do not delete it. Ask the coordinator/PM to classify; required human approval cannot be supplied by an advisor. Never weaken the task's completion criteria or erase failed evidence to appear clean.

## Dependencies and reuse

- Prefer existing project facilities and trusted, maintained open-source libraries over reinvention when they fit the requirement. No gratuitous libraries for trivial logic, bespoke crypto/auth, or speculative updates.
- Before proposing an addition/update, consult current official stable documentation and project manifests/lockfiles for the exact API/version; assess maintenance, compatibility, MSRV/runtime constraints, feature interactions, license and known vulnerabilities. Attribute sources/version and retrieval date; report unavailable or stale research rather than calling a dependency current or safe.
- Use project-approved pinned versions/lockfile practices and minimal required features. Compare reuse with the maintenance/security cost of custom code; a library's popularity alone is not evidence of suitability.
- New dependencies and security updates still require applicable scope and approval. Report urgent out-of-scope findings to the coordinator; do not silently upgrade, install, fetch external services or transmit private data. Read-only specialists use supplied evidence and request missing research through the coordinator.

## Verification and evidence

- Map acceptance criteria to focused checks: normal behavior, invalid inputs, domain transitions, relevant boundary/integration failures, and regression reproduction for fixes. Add cancellation, retry/idempotency, security or UI-state cases where the changed risk warrants them.
- Inspect the project's prescribed test/static commands; choose proportional coverage before lock and run all frozen required checks through the existing coordinator-owned evidence mechanisms. Preserve exact selections, counts, exits, source identity and original output; do not duplicate verification loops.
- Refactoring needs behavior-preservation evidence. Never remove assertions, weaken expected behavior or blindly suppress lints to get green checks. Any justified narrow lint exception must explain the invariant/trade-off under project rules.
- Static checks cannot establish behavior or universal compliance. Report required blocked/not-run checks and missing evidence; keep unmeasured performance and unaudited dependency claims explicit. Independent review applies to the exact final candidate, not an earlier baseline.

## Role routing

Activate only concrete triggers through the coordinator, preferring project equivalents. This table adds engineering focus, not new mandatory fan-out or permission; existing material-decision consultation requirements remain intact.

| Role | Task-local focus |
| --- | --- |
| Requirements analyst | Before planning, inspect relevant code/domain evidence, derive observable requirements and prepare essential initial questions with options and recommendations; see requirements-analysis.md. |
| Build coordinator | Select applicable standards before lock; implement domain/boundary/error contracts and map feature criteria to focused checks. |
| Fix coordinator | Trace the failed invariant/boundary, preserve causal evidence and add targeted regression coverage; avoid adjacent rewrites. |
| Architect | On material model/interface/dependency choices, assess invariant ownership, separation and the smallest compatible design. |
| Advisor | On consequential ambiguity/blockers, compare evidence-backed reuse/remedy options and compatibility/authority costs within remaining limits. |
| Designer | On UI work, assess design-system, responsive/accessibility and pending/empty/error/retry states using actual references and browser evidence. |
| Performance | On concrete performance risks, evaluate supplied measurements, lazy-loading trade-offs, async blocking/cancellation and resource bounds. |
| Security | On changed trust boundaries, inspect validation, auth, unsafe/FFI risks, secure config, diagnostic redaction and dependency security evidence. |
| PM | Translate applicable quality/user-failure requirements into bounded observable criteria and verification reserves before lock; no new gates afterward. |
| Reviewer | Independently check applicable standards against changed source and original criterion-linked evidence; report substantive defects/gaps, not blanket compliance. |
| Memory steward | Retain only useful task-local standards decisions and evidence with source/version attribution; distinguish requirements, observed facts and recommendations, never store a compliance claim from guidance alone. |
