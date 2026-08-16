# Design

## Authority

The accepted `lane repair-identity` implementation remains the sole owner. The
operation is `derive -> immutable receipt -> exact-CAS apply`; no ref, Lease,
SQLite, or runtime pointer is edited manually.

The receipt validator already computes the complete gap set shared by dry-run
and apply. A gapless dry-run therefore projects `verdict=pass` and
`state=ready_to_repair_identity`; any gap remains blocking. No second validator,
authorization surface, or compatibility path is introduced.

## Exact coordinates

- Baseline: `8840e35d282e6d9ea4c32652c3d03491e3d52e16`
- Pre-repair accepted HEAD: `1be1bd2004ab00a54521dfc91bf6aa1c22293c7f`
- Defective commit: `3c74858530ed13fd1e548363daa9d1876e803f3b`

The receipt must preserve each commit tree, message, author, committer, and
linear parent order while replacing only commit identity through the repository
signing policy. Apply must re-read the Work Lane Lease, exact HEAD/tree, proof,
and every affected ref before mutation.

## Acceptance

After apply, every commit after the baseline verifies against repository trust;
the governed train refs converge on the receipt's desired HEAD; the rewritten
HEAD receives fresh full proof. Normal archive, land, accepted closeout, lane
retirement, and package-runtime rebuild remain separate evidenced effects.
