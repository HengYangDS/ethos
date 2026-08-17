# Tasks

- [x] **1. Reproduce the adopter parser regression.** Run current source and
  package runtimes against the exact AIGW/Proxy profile and Commitment shapes.
- [x] **2. Bound branch-role compatibility.** Validate and discard only the
  deployed transition declaration in the loose reader while strict mutation
  parsing remains closed.
- [x] **3. Project terminal-v1 planning facts.** Add a read-only repository
  projection with exact bytes and legacy digest identity, and no v2 proof or
  mutation authority.
- [x] **4. Prove fail-closed boundaries.** Cover malformed transition values,
  unknown v1 fields, and continued rejection by the strict Commitment loader.
- [x] **5. Productize package acceptance.** Add the deployed adopter reader
  shape to source-hidden wheel install smoke and assert installed `status` and
  `plan` behavior.
- [x] **6. Verify real adopters read-only.** Run source runtime `status/plan`
  against AIGW and Proxy and prove their worktrees and Commitment hashes do not
  change.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| repository-governance:Adopter reader compatibility is bounded and non-authorizing | 1 | `tests:real-adopter-reader-reproduction` |
| repository-governance:Adopter reader compatibility is bounded and non-authorizing | 2 | `tests:branch-role-transition-compatibility` |
| repository-governance:Adopter reader compatibility is bounded and non-authorizing | 3 | `tests:terminal-v1-read-only-plan` |
| repository-governance:Adopter reader compatibility is bounded and non-authorizing | 4 | `tests:compatibility-negative-boundaries` |
| repository-governance:Package-only runtime proves deployed adopter reader shapes | 5 | `local-install-smoke:adopted-reader-compatibility` |
| repository-governance:Package-only runtime proves deployed adopter reader shapes | 6 | `receipts:profile-compat-source-adopter-probes-v2` |

After Task 6 completes, close this Change only through the governed lifecycle:
commit the complete overlay; run exact-HEAD full proof; archive the proven
Change; run full proof on the archive HEAD; land and close out that exact HEAD;
retire the owner lane; then rebuild and probe the accepted package-only runtime.
Those are post-task effects evidenced by immutable receipts, not tasks that may
be checked before the effects occur.
