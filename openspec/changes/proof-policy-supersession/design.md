## Context

See [proposal.md](proposal.md). Proof admission already validates each current
same-HEAD record's plan, artifact, statement, source intent and canonical
policy, then selects the required floor. Its global integrity reducer currently
includes `proof_attestation_repository_policy_mismatch`. Consequently an
older, internally consistent policy record vetoes a newer matching proof.
The reproduced adopter has two immutable pass records for one exact commit:
the new record's plan and policy digest match the current resolver, but the
older record's different policy digest causes publication to block.

## Goals and Non-Goals

- Treat a policy mismatch as insufficient current applicability, not evidence
  corruption, while retaining it as the specific gap if no current proof is
  available or an old record is explicitly selected.
- Preserve global integrity vetoes for broken plan/envelope/artifact binding
  and current same-policy contradictions.
- Keep the canonical policy, source intent, proof floor and exact-head checks
  unchanged. Do not delete, expire, rewrite or silently reissue old evidence.

## Decisions

### Separate applicability from integrity at the existing reducer

The per-record evaluator continues returning the policy mismatch for an old
record. The global integrity reducer excludes only that mismatch because it
reports a different internally bound policy rather than malformed evidence.
The existing floor selector then admits only matching canonical policy
records. If no matching record exists, it reports the old-policy mismatch.
All other integrity gaps retain their existing cross-record veto, including
`proof_policy_digest_stale` when an envelope disagrees with its own plan.

This is narrower than picking the newest timestamp or excluding all stale
records. Timestamps and record order do not establish current policy, and an
invalid old record does not become harmless merely because another proof
passes.

### Keep replay at the public adopter boundary

Owner-level tests use two complete same-HEAD records with different internally
bound policies, then test no current proof, explicit old selection, tampering
and same-current conflict. After acceptance and installation, replay the
adopter's exact-head proof and read-only publication preview while retaining
both immutable records. Only a current product result can qualify the fix.

## Risks and Trade-offs

- Historical policy records remain visible in the same set. Consumers must
  apply current-policy selection, not count all pass records as current proof.
- A test-created old policy can be internally consistent yet not issued by
  current public proof creation. The installed adopter replay covers the real
  upgrade transition without making the test depend on host-specific paths.

## Migration Plan

Run the focused red/green cases, strict OpenSpec and the full ETHOS quality
floor; accept and install the source through the owned Work Lane. Re-prove the
adopter's exact source under the installed product and re-run read-only
publication with the old record preserved. Ref publication remains separately
authorized and is not implied by proof selection.
