# Tasks

## 1. Continuation

- [x] 1.1 Observe the accepted ref with its own state that separates a fast-forward from any other move; verify only a fast-forward keeps receipt progress observable, and that a rewritten, rewound or absent accepted ref still reports `retirement_operation_state_drift`.
- [x] 1.2 On an advanced accepted ref, fail closed before any remaining worktree or ref deletion, persist the accurately observed progress, and keep dry-run recovery free of progress writes; verify that a removal followed by an advance reports `partial_transition` with the removal completed.
- [x] 1.3 Derive receipt-invalidated continuations from current facts in one continuation owner; verify the advertised command reaches `retired` when accepted advances before apply, and in the divergent case after removal; verify it names the current accepted head in the absorbed case.

## 2. Verify

- [x] 2.1 Run strict OpenSpec validation, Ruff, ty, import-linter, the code-size measure and the retirement and lane-lifecycle unit tests; verify all 312 pass, with no unrelated tracked change.

## Workflow follow-up

- Prove the exact head, archive this Change, prove again, then land, close out, reinstall the hook runtime and publish to GitHub.
