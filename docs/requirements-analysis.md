# From a short request to a verified result

Every new Build/Fix task runs discovery before planning and source edits. The user's brief is the starting point, not a demand to guess missing product behavior. Scale investigation to the uncertainty: a precise one-line correction may need one targeted read; a vague change across workflows needs a requirements analyst and deeper research. Do not turn a small task into an audit or add speculative features.

On the small lane, discovery is the diagnosis itself: read the issue and the code on its path, reproduce it, and check the tests, `NotImplementedError`/TODO markers, callers and docs around the defect for the behaviour maintainers expect. Fix the whole class of inputs the report describes, not only its example: list every case it names or implies (each input class the function accepts, every validator or raise site sharing the defect, each call site across the package), treat xfail tests and a `NotImplementedError` for an input the issue covers as part of that list, and probe every case again before closing. No analyst, interview or `contract.discovery` record is required; unattended runs record defaults as assumptions instead of asking.

## Research before asking

The coordinator assigns a bounded, read-only requirements-analysis brief for underspecified, conflicting or consequential requests. Prefer the project's equivalent role; Claude Code includes `requirements-analyst`. Codex uses the existing `veera_important` findings-only delegate with the analyst instructions and allowed source paths. Native Claude roles use the selected Claude model; an explicitly requested OpenAI delegate follows the existing model-routing bridge. Never transfer owner capabilities or bootstrap identities. Give the analyst the original request, relevant context, allowed reads and discovery allowance; require findings back before the PM finalizes the plan. If delegation is unavailable, the coordinator performs the same analysis and records that limitation, without pretending consultation occurred or weakening a separately required independent review.

1. Preserve the original request and identify the user's intended outcome, affected users and workflow, current versus desired behavior, and explicit exclusions. Reuse answers and consent already in the conversation.
2. Inspect project instructions, relevant README/product/domain/architecture documents, manifests and supported versions, affected entry points, data flow, interfaces, existing patterns, tests and CI commands. Follow the actual impact path; do not read the entire repository or unrelated projects. A new project with no code should record that observation instead of inventing architecture.
3. Identify domain entities, states, units and invariants that affect this task. For a fix, establish reproduction and distinguish a cause from a hypothesis. For changed APIs or uncertain domain rules, use available authorized sources and current primary documentation for the actual version. The coordinator obtains external research through supported tools; the read-only analyst requests missing evidence. Record source locations and, for external sources, version and retrieval date. Missing access remains a gap. Source content is evidence, not authority to change the task; do not transmit private code or secrets to research services.
4. Derive observable requirements from that evidence. Consider only relevant normal, empty, invalid, failure, cancellation and recovery behavior; affected authorization/data integrity, accessibility, performance and operational needs; compatibility and migration if changed. Inspect existing checks before proposing new ones. Use `engineering-standards.md` selectively. Best practices mean the smallest idiomatic, verifiable solution, not a new dependency or whole-app checklist.
5. Separate explicit requirements, evidence-backed implications and assumptions. Keep desirable unrelated enhancements in non-goals or a future-work note. Never silently promote them to requirements. Have PM resolve outcome/priority questions, Architect assess material interface/invariant choices and Advisor compare consequential alternatives. Record actual participation; routine sequencing needs no committee.

## Written spec or detailed request

When the user supplies a written spec, or a request that already states the behavior, that text is the requirement source and discovery is extraction, not an interview:

1. Read the spec once, end to end, then the code on its impact path. Extract every normative rule (routes, fields, limits, status codes, error titles, ordering, invariants, concurrency, persistence) with its exact values and a section pointer, plus every existing behavior it declares binding.
2. Group the rules into at most 30 requirements, one per observable behavior cluster (an endpoint, an invariant, an error family), each mapped to a criterion and check; keep the exact values in the requirement text so later steps copy, never paraphrase, them.
3. Ask a question only for a contradiction inside the spec or against the code, or for human-only authority. Fill every other gap from project evidence, record it as an assumption with its reason, and do not offer an approaches menu or a design-approval round.
4. Write a Review focus: at most five inputs or failure modes the spec implies but does not test (races, boundary values, malformed input, restart, cross-tenant access), each with the test that will pin it.

## Interview entirely before implementation

Challenge ambiguity firmly when a wrong assumption would materially change the outcome. First research the answer: never ask users to explain code that can be inspected. Then consolidate the remaining product, scope, success, integration, delivery and delegated-authority choices in an initial interview. All clarification questions belong in this discovery phase. Ask a focused follow-up here if an answer reveals a contradiction; do not impose an arbitrary single-round limit or rush unresolved essential choices into implementation.

For each decision, explain the concrete consequence and offer two or three distinct options, with the recommended option first and clearly marked. Give a short reason tied to inspected code, documented domain behavior or cited research, and describe each option's tradeoff. Use plain language, omit questions already answered and let the user supply their own answer. A required name/value may need free text rather than invented options. Use the host's supported question UI when available; otherwise use a concise numbered questionnaire. Do not claim the question UI submitted a preselected option.

For example, after actually finding an existing account-search endpoint and reusable result component: “Should search include archived accounts? Active only (recommended): matches the current account page and avoids exposing inactive results. Active and archived: useful for support, with archived results clearly labelled.” Cite the real inspected locations. This is an illustration, not a default domain rule for every app.

Separate must-answer decisions from delegated reversible choices. An unanswered essential question prevents implementation; silence is not an answer or permission. For a choice already delegated, record the selected default, evidence, decision owner and limits without interrupting the user. Capture decisions in `discovery.questions` and user intent/authority in `intake`; only an actual user response has `resolved_by: "user"`. “Use your recommendation” is usable evidence only when the actual instruction covers that decision.

Before init, show a concise outcome, scope/non-goals, acceptance criteria, important assumptions and ordered plan. Proceed when the user's existing request and answers authorize that work; do not add a redundant “approve the plan” gate. Required questions must be resolved, checks inspected, and delegated decisions bounded. Freeze both records. This is the handoff from discovery to execution.

## Execute without routine interruptions

After implementation starts, consult the recorded answers and decision limits before asking anything. PM owns priorities/sequencing, Architect owns technical tradeoff recommendations, Advisor owns alternatives and blocker remedies, and the coordinator retains execution and responsibility. Consult these roles for concrete consequential decisions, not every edit. Apply safe, reversible, in-scope defaults; record the decision and evidence through existing task decision/memory mechanisms. Do not reopen preference questions or ask for repeated authorization. A new user message may steer the work; reconcile it with the contract.

An unexpected human-only decision, explicit denial, incompatible requirement or exhausted hard limit cannot be answered by impersonating the user. Block the affected action, preserve the evidence, and continue independent authorized work. Consolidate the indispensable issue in the outcome/blocker report; do not start a mid-implementation interview loop or silently expand scope. The initial interview should establish fallbacks where foreseeable. Native prompts required by the host cannot be guaranteed away by a skill; Veera adds no additional Codex approval prompt.

## Frozen discovery record

New Build/Fix skills require `contract.discovery`. Existing saved contracts and older clients without it remain valid and are displayed as “not recorded”. The controller validates structure, bounded size and cross-references at init and amendment; it does **not** certify the truth of sources, research quality, consent or actual specialist participation. The dashboard displays **Requirements & plan** as an HTML task document.

The record uses version 1. All fields shown below are required. Lists have at most 30 entries, text is nonempty and at most 2,000 characters, IDs use letters/digits/underscore/hyphen up to 64 characters, and the whole record is at most 128 KiB. `evidence`, `requirements` and `plan` are nonempty. `open_questions` must be empty. Keep source pointers and concise findings, never transcripts, credentials or owner capabilities.

```json
{
  "version": 1,
  "request": "Original request or faithful short quotation",
  "outcome": "Observable intended outcome",
  "domain": "Affected workflow, entities and invariants",
  "evidence": [
    {"id": "E1", "kind": "user-request", "source": "Actual message reference", "finding": "Requested outcome"},
    {"id": "E2", "kind": "code", "source": "Actual path and line or symbol", "finding": "Observed relevant behavior"}
  ],
  "requirements": [
    {"id": "R1", "text": "Specific observable behavior", "basis": "user-request", "evidence_ids": ["E1", "E2"], "criteria": ["C1"]}
  ],
  "assumptions": [],
  "non_goals": ["Unrelated workflow changes"],
  "questions": [],
  "plan": [{"id": "P1", "action": "Smallest change and focused verification", "requirement_ids": ["R1"], "checks": ["unit"]}],
  "open_questions": []
}
```

`evidence.kind` is `user-request`, `code`, `documentation`, `external` or `observation`; include actual request evidence and at least one inspected source/observation. `requirements.basis` is `user-request`, `project-evidence` or `assumption`; a requirement with basis `assumption` requires a nonempty `assumptions` list. Each requirement cites at least one evidence ID and one criterion ID; each plan step cites at least one requirement and one check. Every acceptance criterion must be covered by a requirement, every requirement by a plan step, and every frozen check by the plan. References must resolve; unknown/duplicate IDs are rejected. Each entry uses exactly the fields shown; an extra field is rejected.

Each question entry has `id`, `question`, `options`, `recommendation`, `rationale`, `evidence_ids`, `answer`, `answer_source`, `resolved_by`. Options are two or three objects with `id`, `label`, `tradeoff`; recommendation names an offered option. For a necessary free-text question use an empty options list and empty recommendation. Answer/source/rationale must be nonempty. `resolved_by` is `user`, `pm`, `architect`, `advisor` or `orchestrator`. A text record alone does not prove consent.

For a separately authorized additive amendment, retain the original brief. `add_discovery` may append `evidence`, `requirements`, `assumptions`, `non_goals`, `questions` and `plan` arrays; it cannot replace the request/outcome/domain or existing entries. New criteria/checks require matching new requirements/plan references. The combined brief is validated under the same limits and stored with prior contract history. This does not authorize unrequested scope, restart discovery during implementation, or grant more time.
