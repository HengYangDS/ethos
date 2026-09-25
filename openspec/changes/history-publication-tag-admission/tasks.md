# Tasks

## 1. Reproduce

- [x] 1.1 Add a real-Git test with a peer at a mapped historical commit below the repaired old tip; verify current pre-push and publication preview reject it.
- [x] 1.2 Add a native pre-push test passing a plain commit OID to a declared release tag; verify the installed hook currently accepts it.

## 2. Repair

- [x] 2.1 Add one validated ref-scoped mapped-peer repair relation and verify missing, wrong-ref, unrelated, ambiguous and tampered evidence is rejected.
- [x] 2.2 Use that relation at commit-range and remote transition; verify repaired history is not rescanned and a violating forward commit still blocks.
- [x] 2.3 Enforce annotated, trusted, exact-name and version-matching tag objects in native pre-push; verify valid tag creation and identical no-op remain allowed while divergent tags block.

## 3. Verify

- [x] 3.1 Run focused real-Git hook and two-peer publication tests, including proof, accepted-effect and candidate-head negative cases.
- [x] 3.2 Run strict OpenSpec validation, repository format/lint and the complete affected test scope; verify no unrelated tracked files or foreign lanes changed.
