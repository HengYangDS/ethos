# Design

The OpenSpec shape audit now scans configured protected branch trees through Git
rather than through checked-out files only. It records branch, semantic role,
change id, and gap string for every `openspec/changes/<id>/...` carrier outside
`archive/`.

Current protected-role checkouts continue to produce required gaps via the
existing active-carrier rule. Residue in another protected branch is emitted as
`advisory_gaps` under `protected_branch_residue`. This keeps small signals
visible without confusing stale local release-root history with current accepted
truth.

The implementation adds no new truth store and no new command plane. It reuses
branch-role policy and Git tree inspection.
