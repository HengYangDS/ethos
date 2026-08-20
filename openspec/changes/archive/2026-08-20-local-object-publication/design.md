## Context

See `proposal.md` for motivation. The current executor already has useful
content-addressed requests, peer-local exact CAS, idempotent replay, and partial
effect Attestations, but its contract is fixed to proposal branches. Ref
classification, proof selection, and peer reconciliation are duplicated around
that executor. A separate identity-repair path deliberately reconstructs commit
objects. These incumbents prevent local Git from being the only product object
authority.

Git 2.55 and OpenSSH provide the necessary object storage, transport, ref CAS,
commit/tag signing, and signature verification. ETHOS must compile policy and
evidence around those standards rather than implement Git transport or
cryptography.

## Goals / Non-Goals

**Goals:**

- one typed model for a local Git object and its remote ref targets;
- one full-ref classifier for branches and annotated release tags;
- one exact proof selector shared by publish and pre-push;
- one request compiler and one Git executor for zero or more independent peers;
- exact commit/tag/peeled/tree/signature verification after each effect;
- destructive deletion of object replay, identity repair, and cross-peer
  reconciliation owners.

**Non-Goals:**

- product version-carrier migration;
- release-asset signatures, TUF metadata, in-toto provenance, or Sigstore;
- historical remote cutover execution;
- runtime, hook installation, profile migration, or GC;
- hosted Forge API status or account `Verified` interpretation;
- changes to AIGW or Proxy.

## Decisions

1. **Replace the proposal effect rather than wrap it.**
   `RemotePublicationTarget` and `RemotePublicationEffect` become a generic
   local-object publication contract. No proposal-only alias or compatibility
   reader remains. Existing request persistence and executor mechanics are
   retained behind the replacement contract.

2. **Classify the complete ref before consulting branch policy.**
   A new typed resolver accepts `refs/heads/...` or `refs/tags/...`, determines
   ref kind, then delegates branch names to `BranchRolePolicy` only when the ref
   is a branch. Annotated release tags are admitted from the declared release
   tag policy. Unknown or lightweight tags fail closed.

3. **Use an existing local object as the sole source.**
   The plan contains the source kind, object OID, peeled commit, tree, signature
   observation, and target set. Peer adapters receive only an exact source OID
   and target ref. No adapter can create a commit or tag.

4. **Delegate effects and signatures to Git/OpenSSH.**
   Remote absence is represented canonically as the repository's zero OID and
   compiled to `--force-with-lease=<ref>:`. Existing refs use an explicit old
   OID. A peer-local multi-ref request uses `git push --atomic`; unsupported
   atomic push fails rather than degrading silently. Git `verify-commit` and
   `verify-tag` consume the repository's OpenSSH allowed-signers projection.
   ETHOS records verifier version, principal, fingerprint, trust-root digest,
   and result but does not parse signatures or hold private keys.

5. **Bind proof into the publication plan.**
   The selected proof Attestation is not an outer readiness check. Its ID,
   repository Commitment, exact commit/tree, gate policy digest, and verdict are
   plan inputs. Pre-push resolves the same target and proof query; it does not
   independently call generic `proof_gaps`.

6. **Divergence is a failed observation, not a merge input.**
   Remove `ReconciliationObservation`, peer-head environment receipts, remote
   history merge requirements, and identity-repair suffix reconstruction. A
   target is current, exact-CAS eligible, or divergent. A future one-time
   destructive cutover must be a separate bounded command with an exact old
   OID; it cannot revive these standing paths.

7. **Separate Git object publication from asset trust.**
   Git/OpenSSH own commit and tag trust. A later atom will evaluate TUF for
   release-asset trust and in-toto/DSSE for build provenance. This Change adds
   no home-grown trust-bundle format and no online Sigstore dependency.

8. **Keep prepared ref intent valid until transaction closeout.**
   The short intent expiry applies only before Git enters the transaction. Once
   the exact ref, old and new OIDs, operation, and plan digest have advanced to
   `prepared`, wall-clock expiry cannot invalidate that active transaction
   while its hook is evaluating. Git `committed` or `aborted`, or the existing
   exact recovery path, owns terminal closeout; housekeeping removes only
   expired `issued` intents.

## Risks / Trade-offs

- **Large deletion surface** -> prove whole-repository reference closure
  immediately after deleting identity repair and reconciliation.
- **Single-peer partial success across several peers** -> retain independent
  peer receipts and idempotent replay; never claim cross-peer atomicity.
- **Git server lacks atomic multi-ref push** -> fail before claiming peer
  completion; do not split a peer's declared atomic set silently.
- **Signature output differs by Git/OpenSSH version** -> parse only stable
  machine-relevant fields and bind raw verifier status as evidence.
- **SHA-256 repositories use a different zero width** -> derive object format
  and zero OID from Git instead of retaining a SHA-1 constant.
- **Hook evaluation outlives issued-intent TTL** -> distinguish pre-transaction
  expiry from prepared transaction lifetime instead of increasing a timeout.

## Migration Plan

1. Add failing contract and bare-peer tests for full-ref classification,
   exact-object parity, proof binding, zero/one/two peers, and divergence.
2. Replace the proposal-only target/effect with the full-ref object model and
   route CLI and hook admission through it.
3. Extend the existing executor to commits and annotated tags, exact post-read
   parity, derived zero OID, and peer-local atomic requests.
4. Delete identity repair and cross-peer reconciliation code, commands,
   schemas, fixtures, rules, and normative requirements in the same Change.
5. Prove retired symbol and wording closure, run focused and full proof, then
   archive and close out through the public lifecycle.
