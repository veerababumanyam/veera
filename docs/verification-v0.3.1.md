# Veera 0.3.1 Windows storage verification

Veera used `mkdir(mode=0o700)` for session enrollment, migration, task state and archive directories. Since Python 3.13, Windows gives this mode a protected user/administrator-only DACL. This removes inherited entries, potentially excluding the host's execution identity. The behavior is documented in [Python's mkdir reference](https://docs.python.org/3.14/library/os.html#os.mkdir).

The shared storage helper now uses ordinary Windows directory creation, preserving inherited host-managed access. POSIX directories retain `0700`; ownership records retain exclusive creation with `0600`. Existing permissions, session identity, ownership checks and actual host denials are unchanged. The plugin does not repair ACLs or select an alternate registry.

## Reproduction and validation

The new Windows regression exercised actual enrollment, migration, state and archive creation in disposable directories. Before the fix, all five directory locations had protected DACLs and failed the inheritance assertion. After the fix, all five locations and the ownership record inherited access. Additional tests confirm unchanged existing ACLs/content, exclusive enrollment, preserved migration sources and propagation of directory/record write denials without retry or redirection.

- Full Python suite: **240 tests, no failures, three platform skips**, in 127.537 seconds. One skip is the POSIX mode check on Windows; the other two require unavailable Windows symlink privileges. Log: `artifacts/final-v0.3.1-tests.log`.
- New storage regression: four passing tests and one POSIX-only skip. Logs: `artifacts/storage-permissions-before.log` and `artifacts/storage-permissions-after.log`.
- Dashboard JavaScript: 11 assertions passed. Native Claude marketplace validation passed. `git diff --check` passed.
- Installed-copy validation is recorded separately in `artifacts/install-verification-v0.3.1.json`: packaged-file comparisons, targeted test modules and execution of the actual installed Windows hook commands using isolated fixtures. These fixtures are not live host session identities.

## Existing blocked task

The reported task's checkpoint records failed session-record creation, denied ACL inspection and unsuccessful inheritance/ownership repair attempts. It preserves the original pre-init worktree and the user's local-verification choice. This maintenance work did not alter that checkpoint, task source, database or owner records.

The directory-creation defect is reproduced; the ACL of the existing inaccessible live directory could not be inspected, so its exact cause is not independently established. Installing 0.3.1 does not restore access to an existing denied directory. Normal authorized Windows administration must restore the required access before the original owning session can recover the same worktree.

The [0.3.0 fresh-session evidence](verification-v0.3.0.md) establishes automatic routing and documents the Codex persistent-directory denial and Claude account limit. This patch does not claim a new successful end-to-end model-driven delivery or retry the unchanged live denial. No native permission settings, trust hashes or ACLs were changed by the repair.
