## 1. Reconcile the source binding

- [x] 1.1 Reproduce the failure with the actual-source export regression and architecture projection gate; confirm both identify `repository_governance` digest drift.
- [x] 1.2 Review the archived canonical scenario against existing graph semantics; confirm no graph entity, relation, authority or target claim changes.
- [x] 1.3 Refresh only the repository-governance source digest and verify all other graph content and canonical source bytes are unchanged.

## 2. Verify the maintenance change

- [x] 2.1 Run the projection test module, including actual-source export and stale-source rejection, and verify all cases pass.
- [x] 2.2 Run strict OpenSpec validation and verify the no-spec-change marker is accepted with no spec delta files.

Head-bound full proof, official archive and proof of the archived HEAD are
required transition preconditions. Their immutable results remain outside this
source task list so recording success cannot invalidate the verified snapshot.
