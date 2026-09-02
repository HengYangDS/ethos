## Context

See [proposal.md](proposal.md) for motivation and
[specs/repository-governance/spec.md](specs/repository-governance/spec.md) for
the observable contract. The existing linked-lane retirement path already owns
target selection, clean-worktree checks, accepted ancestry, exact ref CAS,
worktree removal, Lease transactionality, compensation, and postcondition
observation. Its remaining defect is that it treats every linked retirement as
an OpenSpec acceptance transition: it loads a proof Attestation, reconstructs a
Commitment, and always requires a valid Lease.

That dependency is false for a Lane already contained in accepted truth. The
operation changes no product tree and accepts no intent; it deletes a redundant
local projection whose content is already reachable from `dev`.

The canonical repository-governance and command-plane specifications also
retained the superseded model: linked retirement was named a generation-bound
effect, and Lease identity still included Lease ID, epoch, expected Git
coordinates, payload digest, and incarnation. Those fields contradict the
Product Design Contract's four-field Lease and make fresh Git facts subordinate
to historical coordination state. This Change therefore repairs the affected
Lease requirements as part of the same bounded model correction rather than
layering landed-retirement exceptions over the old authority.

## Goals / Non-Goals

**Goals:**

- reuse `lane retire landed` as the one linked accepted-residue path;
- make the Git ref deletion a Commitment-free repository effect;
- distinguish valid, expired, missing, and unknown Lease observations;
- keep valid foreign ownership, dirty state, non-ancestry, and coordinate drift
  fail-closed;
- preserve exact recovery and postcondition evidence.

**Non-Goals:**

- retiring dirty or diverged lanes;
- changing successor-based semantic absorption;
- adding a new command, registry, decision file, receipt format, or Lease field;
- weakening protected `dev` or `main` ref policy;
- inferring that every historical Lane is safe to delete.

## Decisions

### Treat landed retirement as a pure repository effect

`linked_retirement_plan` will compile the existing exact `GitEffect` with
`Commitment=None`. The plan remains bound to repository identity, execution
HEAD/tree, target ref update, accepted-ref assertion, policy, and observed
values. This matches the already established repository-effect boundary and
removes the unrelated proof lookup.

Alternative rejected: mint or recover a proof/Commitment for each historical
Lane. That would turn deletion into a false acceptance event and preserve the
obsolete carrier coupling this repository is removing.

### Replace the canonical requirement instead of retaining compatibility vocabulary

The OpenSpec delta removes the complete old `Linked Work Lane retirement has one
generation-bound effect` requirement, adds the complete replacement `Linked Work
Lane retirement has one exact effect` requirement, and modifies the complete
Lease-identity requirement. The replacement keeps Git HEAD/tree, selected proof,
package identity, and effect evidence in their native Facts or Attestations while
the Lease owns only lane ref, holder ref, positive generation, and expiry.

Historical archived Changes remain immutable evidence of the old model, but no
active requirement or current Lease contract retains Lease ID, epoch, expected
HEAD/tree, raw payload digest, or incarnation as Lease authority. The bounded
state-schema migrator may still read the obsolete five-column representation in
order to produce the four-field schema; it does not make those fields current.
Superseded retirement keeps its independently selected proof and transient
Commitment; that does not put either value inside the Lease.

Alternative rejected: modify only the landed branch of the implementation while
leaving the old canonical requirement in force. That would make the passing code
an undocumented exception and preserve two incompatible owners.

### Derive retirement authority from the observed Lease state

The existing Lease row remains authoritative only while valid:

| Lease observation | Admission | Transaction |
| --- | --- | --- |
| valid, invoking actor is exact holder | pass | re-observe and revoke the exact generation |
| valid, actor differs or is absent | block | no effect |
| expired | pass with non-empty actor and explicit authorization | re-observe and revoke the exact expired row |
| missing | pass with non-empty actor and explicit authorization | require absence inside the transaction |
| unknown | unknown/block | no effect |

Expired or missing state grants no reusable ownership. It merely allows the
accepted-root operation to remove a clean redundant projection under exact CAS.

Alternative rejected: reacquire or synthesize a Lease before deletion. That
would fabricate historical ownership and create unnecessary state solely to
delete it.

### Keep one effect and recovery path

The current sequence remains:

1. observe exact branch, worktree, cleanliness, accepted ancestry, Lease, and
   actor facts;
2. acquire the SQLite transaction and re-observe the expected Lease state;
3. compile and admit one Git ref deletion with an accepted-ref assertion;
4. remove the exact linked worktree;
5. execute the ref CAS and persist its effect Attestation;
6. commit Lease removal only after the terminal effect, or restore the worktree
   and roll back on failure;
7. report ref, worktree, and Lease postconditions.

No command-specific compatibility state or second cleanup framework is added.

## Risks / Trade-offs

- **Expired or missing Lease permits a different actor to clean residue** → the
  operation is limited to a named clean `work/*` ref already contained in the
  freshly asserted accepted HEAD, requires explicit authorization and actor,
  and performs deletion only.
- **Worktree removal precedes ref deletion** → retain the existing exact
  compensation path and fail closed if restoration cannot be proved.
- **Lease state can change after planning** → hold an immediate SQLite
  transaction and re-observe either the exact row or exact absence before the
  filesystem or ref effect.
- **A historical branch may contain meaningful work** → ancestry is mandatory;
  diverged lanes remain outside this Change and require separate semantic
  adjudication.

## Migration Plan

1. Add focused regression tests that demonstrate the current proof and Lease
   dead ends.
2. Remove proof/Commitment loading from the linked retirement plan.
3. Make Lease admission and transaction handling state-specific.
4. Run focused retirement tests and the repository proof ladder.
5. Archive and accept this Change, activate its immutable runtime, then use the
   public command to retire only freshly re-observed eligible residue Lanes.
