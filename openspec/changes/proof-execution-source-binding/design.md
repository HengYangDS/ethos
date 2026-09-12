## Owner And Invariant

A Git commit identifies immutable content; a checkout and its index are separate
mutable inputs. Proof may name that commit only when execution observes matching
source and index. The existing proof adapter owns that decision. Native Git
observation supplies content facts; CLI reports the owner error rather than
implementing another source checker. Existing Facts and the proof plan carry the
necessary binding, and readers reject evidence lacking the required binding.

## Execution Boundaries

Compile the execution-source identity with the plan. Revalidate it immediately
before and after the gate bundle, before issuing a proof, and before publishing a
passing Attestation into the selected set. HEAD equality is necessary but not
sufficient. Reuse native isolated-index worktree projection and the real index
identity; observation failure is not an empty or clean result.

Exact-commit proof begins from committed source. Dirty exploratory verification
remains possible via the existing host observation plane; do not relabel it as
proof of HEAD. Non-ignored inputs belong to source; ignored generated output does
not alone invalidate source identity. Source drift never triggers automatic
restore, stash, discard or rerun against a different candidate.

## Evidence And Limits

A public CLI fixture with actual Git and native subprocess gates reproduces the
bug without monkeypatching proof or policy interpretation. Extend it to index-only
changes, policy changes, deletion, untracked source and pre-execution dirtiness,
plus unchanged input and ignored-output success. Verify the direct issuance and
selection boundaries, and keep exact-plan binding tests meaningful. On late
source failure retain completed native checks through the existing content-
addressed artifact owner, without issuing a passing Attestation or dropping the
diagnostic reference.

Pre/post observations are not a filesystem sandbox and cannot prove absence of
all transient malicious changes between samples. A hostile same-UID writer or
untrusted gate requires an independently isolated execution boundary. Do not
claim that a Lease, file lock, watcher or digest supplies such isolation. The
bounded repair closes the demonstrated persistent-drift path and makes its
source-equivalence guarantee explicit without inventing a universal executor.

## Delivery

Keep the already archived dependency repair. Complete this official Change in
the existing lane with actual RED, unique-owner repair, focused GREEN, static
checks, exact full proof and archive; then verify the archived exact candidate
and continue accepted/runtime/peer closeout. Retain previous proof as historical
observation, not proof of this new source contract.
