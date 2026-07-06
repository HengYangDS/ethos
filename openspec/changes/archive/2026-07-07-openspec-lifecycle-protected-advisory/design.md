# Design

The repair keeps one scan as the source of truth: repository OpenSpec audit owns
the protected-branch active-carrier read model, and the OpenSpec adapter reuses
that function. `ethos openspec --lifecycle --json` now returns
`advisory_gaps` and `lifecycle.protected_branch_residue` while preserving
`required_gaps` for current-checkout lifecycle failures only.
