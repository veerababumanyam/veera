# Veera 0.2.4 verification

Verified locally on Windows with Python 3.14 and Chromium on 2026-10-23. This repair uses ordinary host tools; it does not require Veera to bootstrap its own maintenance.

## Approval failure and architecture

The old adapter converted Veera's mandatory ASK decisions into denials because Codex hooks cannot request that approval. This made eligible recovery and ordinary execution fail even when the host permitted them. The owner explicitly revoked that extra policy during this repair.

Codex now uses the host's existing permission policy. Veera's controller still validates task ownership, frozen contract, recovery evidence, checkpoints and limits. Direct patches retain path validation. Shells and opaque tools are governed by the host; Veera does not claim to sandbox their effects. Claude's approval policy is unchanged. Unexpected legacy ASK results still produce a valid denial rather than an unsupported hook response.

Upfront intake is an optional, validated section of the existing frozen contract. It records user intent, supplied information, assumptions and delegated decisions. Skills require new tasks to capture it and reuse applicable authorization. Legacy tasks remain readable without inferred consent. Roles resolve eligible decisions internally; this record cannot grant native permissions or fabricate specialist participation.

## Executed checks

| Check | Result |
| --- | --- |
| Full Python suite | 194 tests completed successfully; two symlink tests skipped for Windows privilege restrictions. |
| Dashboard JavaScript | 11 assertions passed, including escaping, measured counts, terminal stop behavior, missing timing and disconnect handling. |
| Document script syntax | Passed. |
| Real controller recovery | Isolated owned task amended and resumed with recorded authorization, using the actual Windows interpreter and no extra Codex hook approval. |
| Hook process and bootstrap | Exercised in subprocess fixtures; valid schema, namespace isolation, invalid state denial and capability reporting verified. |
| Document endpoints | Token and run binding, bounded reads, escaping, missing records, catalog links and traversal rejection verified. |
| Browser | Live status, safe request rendering and HTML task/handbook documents verified against a disposable local fixture. |
| Responsive layout | Actual browser viewports of 320, 768, 1024 and 1440 pixels had no horizontal page overflow. Keyboard document navigation focused the selected heading. Search, empty results and ordinary anchor navigation checked. |
| Repository hygiene | Whitespace check passed; no references to the removed external workflow remain. |

The initial headless screenshot runner uses window dimensions, which do not guarantee the same content viewport on Windows. Responsive conclusions above come from explicit browser viewport overrides and DOM width measurements. Smooth scrolling was removed to make anchor navigation immediate and predictable.

Local evidence is retained in `artifacts/final-python-tests.log`, the browser smoke output, and `artifacts/dashboard-desktop.png`, `artifacts/dashboard-documents.png`, `artifacts/dashboard-mobile.png` and `artifacts/dashboard-mobile-documents.png`.

## Limits of this verification

These are source, subprocess, controller and real-browser fixture checks, not a claim of a complete production model-driven delivery. The read-only diagnostic reports package integrity and declared capabilities; it deliberately does not claim live hook activation. Native hook trust/loading belongs to the host. Existing owner data and host permission settings were not changed. No independent specialist review is claimed.

Install the candidate through the configured local marketplace with the normal native plugin update command. Verify the installed manifest and file hashes against this tested source; do not patch the plugin cache or manufacture hook trust.
