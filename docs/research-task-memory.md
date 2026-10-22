# Task memory and recovery design research

Sources inspected for v0.1.2 design (public documentation; no private project data sent):

- Anthropic, Effective context engineering for AI agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  - Structured persistent notes support long-running continuity; keep goals, progress, dependencies and discoveries outside the transient conversation.
  - Compact histories while preserving decisions and unresolved problems. Compression can lose details that later matter: retain pointers to original sources and inspect them on demand.
  - Scoped subagent work and concise results reduce redundant context; bigger context windows are not a guarantee of relevance or perfect recall.
- GitHub, Events that trigger workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
  - Push workflows depend on configured events and branch/path filters. Local commits/worktree operations do not cause remote push events.
  - One final push can trigger multiple workflows/jobs. A single-push policy reduces intermediate triggers but does not guarantee one Actions run or a billing ceiling.

Design application: one task-scoped memory section in Veera's existing locked state, not a global vector store or external service. Maintain a revisioned index and source-linked items; compact handoffs reference records rather than copying transcripts. A dedicated memory steward proposes updates; the coordinator validates and imports them. Neither notes nor agent identities grant authority. No automatic cross-project retention, embeddings, background memory refresh or private-data publication.

Recovery application: distinguish ordinary engineering failures from human-only permission/product/security decisions. Track stable blockers, nonduplicated evidence and bounded attempts. Escalate exhausted technical attempts to actual Advisor/Architect consultation and a PM-owned decision without resetting prior history or weakening acceptance. Keep independent eligible work moving; never claim full completion with unresolved blockers.

These are design recommendations, not measured token savings or model-behavior guarantees. Existing source, runtime checks and application-specific instructions remain authoritative.
