## Context

See `proposal.md`. The existing `archive-change` command already owns official
archive execution, exact commit, Lease advancement, post-observation, and
Attestation. The missing case is a crash or bounded break-glass cut after the
archive commit but before those terminal local effects. Recovery and rebind
previously derived overlapping archive facts, while proof used a generic plan
error action.

## Goals / Non-Goals

**Goals:**

- Classify the exact committed archive post-image once from Git and the current
  Lease-bound Commitment.
- Reuse `archive-change` for recovery; do not create a rebind receipt for a
  physical carrier relocation.
- Give proof and rebind callers one exact, copyable continuation.
- Reject any candidate that is not the direct, byte-identical, archive-only
  successor of the Lease-bound HEAD.

**Non-Goals:**

- A second lifecycle or recovery state machine.
- Replaying OpenSpec during committed-postimage recovery.
- General maintainer break-glass, publication, or lane-start repair.

## Decisions

### One Git-fact classifier serves recovery and routing

The archive recovery owner derives the previous HEAD, exact changed path set,
valid dated archive carrier, byte-identical relocation, and official archive
path closure. Recovery consumes the resulting immutable tuple; rebind and proof
ask only whether that exact tuple exists and obtain the existing public command.

Alternative rejected: independently scan archives in proof and rebind. That
would recreate the ambiguity and let readers disagree with the effect owner.

### Archive relocation is not semantic Commitment rebind

Moving unchanged Commitment bytes from the active carrier into the official
dated archive changes physical location, not intent. Rebind derivation therefore
returns `archive_recovery_required` and the `archive-change` command instead of
minting a competing rebind receipt.

Alternative rejected: teach generic rebind apply to finish archives. That would
give two commands ownership of the same Lease and Attestation transition.

### Public state remains verdict-derived

The top-level CLI state remains `blocked` for a blocking verdict. The precise
domain state remains in `data.state`, and the top-level `next_action` projects
the owner's command. This preserves the common result-envelope contract while
retaining typed recovery detail.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `command-plane:Commitment rebind failures are directly actionable` | `2.2` | `test_rebind_derivation_recognizes_the_exact_archived_carrier`, `test_archive_recovery_derivation_fails_closed_for_nonexact_targets` |
| `command-plane:Proof Command State Semantics` | `2.3` | `test_prove_names_exact_archive_recovery_for_a_stale_lease` |
| `repository-governance:Lifecycle effect finalization authorizes exact transition paths` | `2.1` | `test_committed_standalone_archive_recovers_lease_attestation_and_proof` |

## Risks / Trade-offs

- [Risk] A similarly named historical carrier is selected → require one valid
  dated carrier and exact byte/path closure.
- [Risk] A later commit is mistaken for the archive effect → require the target
  to be the direct child of the Lease-bound expected HEAD.
- [Risk] Proof and rebind drift again → both consume the same recovery helper
  and producer-to-consumer tests assert the public projection.

## Migration Plan

1. Preserve regression tests for the observed stale-Lease archive cut.
2. Introduce the shared classifier and route recovery, proof, and rebind to it.
3. Run focused and full gates, then archive and land through the existing public
   lifecycle.
