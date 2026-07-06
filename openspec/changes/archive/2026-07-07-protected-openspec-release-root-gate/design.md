# Design

The existing protected-branch scanner already reveals active carriers in
non-current protected branches. The missing invariant was not visibility; it was
transition strength. `ethos report` and `ethos openspec --lifecycle` may keep the
signal advisory because they are read models and do not authorize mutation of a
foreign protected branch. `ethos publish` is different: it makes a local
publication-readiness claim, so release-root active carriers are hard blockers.

The implementation adds a small reducer over the existing scanner:
`protected_branch_active_change_required_gaps`. By default it selects
`release_root` records. The publish command appends those gaps to its normal
readiness gaps and emits `data.release_root_open_spec` for UX/DX.

No new truth store, command plane, or ontology is introduced. The same Git tree
facts, branch-role policy, OpenSpec carrier names, and invalid-state taxonomy are
reused.
