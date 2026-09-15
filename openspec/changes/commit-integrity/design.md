## Boundary

This Change closes commit integrity: who is declared, what was signed, which
policy judges an integration, and how incorrect objects are repaired. Identity,
cryptographic trust, transport and Forge attribution remain distinct claims.

## Admission

The tracked commit policy may constrain author and committer identity separately.
Absent constraints add none for generic adopters. Present malformed declarations
fail closed. The existing compiler and object/range validator own all decisions;
remove the mutable `ethos.pushIdentityPolicy` consumer rather than carry it as
another policy source. Native Git supplies prospective identities and performs
signature verification against the protected external trust anchor.

An exact integration range is judged by its trusted prestate policy and any
candidate constraints. A candidate cannot authorize its own unsigned or
misattributed introduction by deleting policy. Missing policy before initial
adoption imposes no retroactive requirement on unrelated history. Git hooks,
generated commits and public CI admission call the same owner.

Generated commit admission derives both policies from the exact parent and target
tree, not a mutable checkout. Replay retains trusted-baseline constraints even if
the candidate supplies no policy. Local native hooks must distinguish a rejected
raw commit, rejection after `--no-verify`, and a successful signed proposal push.

## Repair

Extend the existing signature repair, not a parallel lifecycle. A request names
exact old object identities, expected author/committer values and replacements,
selected refs, actor and reason. Readiness only observes. Before application,
verify a recoverable Git bundle and its manifest. Preserve message/tree/time and
all non-selected identity fields; map parents in their original order. Re-sign
changed objects with current authorized keys and retain original signatures as
historical evidence. Do not describe a new repair signature as an original one.

Bind original-to-replacement mappings to existing Attestation results. Validate
the mapping against actual objects, not its claimed digest alone. Existing exact
Git CAS owns local updates; stale refs reject, completed effects are not replayed,
and unknown signing/publish outcomes require observation. Old proof remains
historical; re-entry derives a fresh proof/runtime and each peer's actual state.
Archived intent may follow only validated repair provenance with matching bytes.

Recovery verifies the bundle by isolated native extraction and object-closure
validation. A no-effect same-key request rejects before signing. On an interrupted
history attempt, the existing object database supplies exact signed payloads;
native trust validation admits reuse and ambiguous matches reject. Only missing
objects are created. No additional durable progress carrier is needed. Historical
result consumers re-derive source policy and permitted refs instead of accepting
internally consistent reissued coordinates. These checks do not claim protection
against a writer sharing the operator's OS identity.

## Execution Order

1. Preserve exact historical evidence and public negative probes.
2. Close policy, actual verification and all direct admission consumers first.
3. Extend repair and provenance, exercising native interrupted/replay scenarios.
4. Run focused and packaged tests; freeze for current full proof and acceptance.
5. Apply the explicit historical selection, reprove/rebind and publish exact OIDs.

## Verification

Valid signed identities pass. Missing/forged/untrusted signatures, wrong identities
and self-weakened policy reject at the owning boundary. Check ordinary commit,
index policy, generated commit, bypassed message hook, exact CI range, no-policy
adoption and unrelated old history. Repair tests distinguish identity-only,
signature-only, merged DAG, stale CAS, altered content, missing backup, interrupted
signing, lost acknowledgement, proof currentness and partial peer publication.

The preserved public probes are observations of `hook commit-range`, not claims
that full proof or protected publication were bypassed. Historical identity
counts do not establish incorrect cryptographic ownership of every old key.
