## Context

The existing `prove` path uses one root for three distinct duties: reading the
Work Lane's authority, observing the executable source and running gates.
That coincidence is valid for a clean lane but fails when an official archive
is staged. Its index and worktree must remain untouched until the archive
effect, while the current policy still requires fresh checks of the committed
pre-archive HEAD. A detached checkout can supply those bytes, but a proof
issued *from* that checkout has no original lane Lease.

## Decision

Add one optional `--execution-root` to the existing proof operation, only for
an executed, full, exact-HEAD repository proof. The caller prepares a native
detached Git worktree; ETHOS validates it rather than cloning source or
inventing a second checkout manager. The flag identifies an execution
resource, not another intent, policy, actor, Lease or Attestation owner.

The authoring root continues to supply the repository identity, current
actor/Lease generation, committed Change, HEAD/tree, policy and persistent
Attestation set. Resolve intent from the exact committed tree when a carrier
is selected; do not reinterpret the staged archive as accepted intent. The
carrier must resolve to a different registered worktree in the same Git
common directory, be detached at the same HEAD/tree, and have no tracked or
untracked source drift. Gate execution and its source rechecks use only that
carrier. Issuance and persistence use only the original root.

Before execution, capture the original HEAD, Lease, staged index and working
content through the existing Git/source observers. Recheck them, and the
carrier's source, after checks and immediately before issuance. On mismatch,
retain completed diagnostics and issue no passing proof. A timeout or lost
acknowledgement is UNKNOWN until the existing effect and Attestation stores
are observed. Normal proof without the flag retains its current path and cost.

## Rejected Alternatives

- Reset, stash, reverse or replay the staged archive: changes the user's
  protected authoring state and risks lost effects.
- Re-sign previous checks: the stronger policy has obligations those checks
  never executed.
- Prove from a detached or different Work Lane as the authority: its Lease and
  intent do not match the original lane's archive admission.
- Copy policy or proof records into a new execution service: creates a second
  authority without solving exact source and effect-time freshness.

The accepted product already used 49,898 of 50,000 ELOC. A ponytail review
removed duplicate carrier source observation, yet this independent proof
boundary still exceeds the remaining 102 ELOC. The user explicitly allowed a
55,000/55,000 product/test ceiling when semantic reduction was insufficient.
Change only the product ceiling in the native source-budget declaration; retain
the existing test ceiling, 500-ELOC file cap, 95% coverage, strict lint/types,
and full proof. The extra capacity is not a target or a substitute for deletion.

The first exact-HEAD proof blocked when the `secrets` gate's per-worktree native
cache redownloaded Gitleaks until the existing 180-second supply deadline. The
same locked archive already existed in another checkout. The native materializer
will default to one cache under the Git common directory; explicit CI cache
selection retains precedence. Its existing archive checksum, executable version,
unsafe-path checks, atomic replacement and per-identity lock remain authoritative.
The cache belongs to the repository lifetime, not to any single worktree; no
foreign or active cache is deleted to make this proof pass.

## Verification

First reproduce the public staged-archive failure and preserve its eight-path
postimage. Positive tests require new gate execution, exact proof selection
from the original lane and unchanged staged/working content. Negative tests
cover foreign common-dir, attached/wrong/dirty carrier, stale original Lease,
and mutation of either root during checks. Then run the affected tests, one
exact-source full proof, installation and read-only adopter handoff. Do not
call a local host-only observation or a partial gate run accepted proof.
The staged archive Git effect may advance while reporting `repair_required`
until the archived HEAD receives its own fresh proof; replay then recognizes
the existing effect. Do not mistake pre-archive proof for archive completion.
The exact proof, archive, integration, runtime installation and adopter handoff
are post-task lifecycle effects, not tasks that must falsely pre-certify
themselves to make the accepted intent provable.
