# Upfront intake and uninterrupted delivery

Veera gathers required information and user-delegable authorization at the beginning, then lets the orchestrator manage the work. PM owns ordinary delivery decisions; Architect assesses consequential design choices; Advisor compares alternatives. Roles never impersonate the user or grant native permissions.

## Initial interview, before execution

Follow [requirements analysis](requirements-analysis.md) first: research the application and domain, then ask only consequential unresolved questions. Offer two or three choices, a recommended choice with evidence and tradeoffs, and room for a custom answer. Essential follow-ups stay in this discovery phase; implementation begins only after they are resolved. Record the interview and plan in `contract.discovery` and decision limits here.

1. Read the user's request and available authorized project context. Reuse information and consent already supplied. Do not ask the same question twice.
2. Establish the desired outcome, repository, scope, exclusions, acceptance checks, delivery mode, budget, allowed integrations and publication destination if publication is requested. Inspect host capabilities before enrolling: do not start a plan that depends on unsupported approval/tool paths.
3. Separate necessary missing information from routine implementation choices. A written spec that answers the product questions leaves no interview: record it as a known input and its gaps as assumptions. Choose reasonable defaults for reversible low-impact details, documenting assumptions. PM may settle priorities within the agreed goal; Architect and Advisor handle technical tradeoffs within the existing scope and ceilings. The orchestrator retains task ownership and native tools.
4. If essential information or user-delegable authorization is still missing, present a concise consolidated interview covering the unresolved items and concrete effects. If an answer exposes a new essential contradiction, resolve it now before implementation. Use existing evidence instead of asking for credentials or secrets in chat. Silence is not consent. Permissions that the host requires at action time cannot be prepaid by this question.
5. Capture the actual user request/reference, allowed actions and limits, delegated decisions, known inputs and assumptions in `contract.intake`. Read it back before init and include it in the existing frozen contract. No second database, session scan or new permission store.

## During execution

Consult the frozen intake first. Continue already-authorized eligible work without repetitive confirmations, preference questions or routine status approval. Do not treat recorded authority as expiring merely because a turn, specialist, context window or phase changes. Resolve routine uncertainty internally. Material choices still require actual consultation when the shared contract calls for it; do not invent a specialist's participation.

Record decisions and evidence through existing task mechanisms. Intake does not enlarge frozen scope, release permission, budgets, repair counts or access to other projects. It does not authorize changing the intake after lock; existing contract checksums protect it. Legacy tasks without intake remain valid and show “not recorded”; never infer consent or silently migrate them.

If a new essential human-only decision or unexpected denial appears, block only the affected action and continue independent eligible work. Preserve the exact blocker and checkpoint. Consolidate indispensable issues in the blocker/outcome report; do not launch a mid-implementation preference interview. Do not claim the blocked portion complete. Do not repeatedly ask for an approval the host cannot represent. Hard ceilings still stop the task.

## Unattended runs and the small lane

When the request says nobody will answer, Veera asks nothing and never waits: it researches the answer, takes the evidence-backed reversible default, records it as an assumption in the report and continues. Silence still grants no new authority: publication, destructive operations and other human-only actions remain blocked and are reported. On the small lane (one bounded, unpublished defect) `contract.intake` is optional; the request itself is the recorded intent and the frozen contract still bounds scope, checks and time. An unattended run does not end user-stopped over its own tooling: when a frozen check turns out defective (a test file that does not exist, a runner the environment lacks) or a case of the issue needs one more file, the coordinator records the evidence with `correct-contract` and carries on. A Build run whose suite passes but whose frozen `count_pattern` reads no tests likewise re-reads it through a corrected pattern instead of stopping. Human-only decisions, denials and the hard ceiling still stop it.

## Native approval boundary

User-intent records and specialist decisions capture delegated authority; they do not change the host's permissions. Veera adds no extra interactive approval gate on Codex. `amend`, `resume` and `blocker-human-resolve` may use the actual recorded upfront authorization when its scope covers the operation; the controller still validates owner identity, checkpoint, limits and state. With a host policy that allows execution without prompts, Veera does not manufacture a prompt requirement. If the host itself denies an action, do not evade it or change host settings. The orchestrator continues independent eligible work and reports only indispensable new user decisions.

## Frozen record

All fields below are required when intake is present. Use actual user evidence and project values; the example is a schema illustration, not authorization. Lists are bounded to 30 entries and text to 2,000 characters. `open_questions` must be empty at init. Do not store passwords, tokens, private keys or owner capabilities.

```json
{
  "version": 1,
  "user_request_ref": "Reference to the actual user request",
  "authorized_actions": [
    {"action": "Edit and test the requested component", "scope": "Explicit project and files", "evidence": "Actual user message reference"}
  ],
  "delegated_decisions": [
    {"topic": "Routine implementation choices", "owner": "orchestrator", "limits": "Within frozen scope and existing permissions"},
    {"topic": "Delivery sequencing", "owner": "pm", "limits": "Preserve all acceptance criteria and ceilings"}
  ],
  "known_inputs": [
    {"name": "Delivery mode", "value": "local-verify", "source": "Actual user instruction"}
  ],
  "assumptions": [],
  "open_questions": [],
  "escalation": "block-affected-work",
  "native_approval": "required-where-applicable"
}
```

Each `authorized_actions` entry has exactly `action`, `scope`, `evidence`; each `delegated_decisions` entry exactly `topic`, `owner`, `limits`, with `owner` one of `pm`, `architect`, `advisor`, `orchestrator`; each `known_inputs` entry exactly `name`, `value`, `source`. `assumptions` holds plain strings. `escalation` must be `block-affected-work` and `native_approval` `required-where-applicable`.

The dashboard's **Intake & approvals** document displays this exact record. Its presence does not claim that a native approval was obtained. Controller validation rejects missing/unknown fields, unresolved questions and any attempted approval-policy override.
