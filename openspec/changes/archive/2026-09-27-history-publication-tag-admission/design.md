## Context

See [proposal.md](proposal.md). A completed history repair already carries a
validated old-to-new commit mapping and the exact local refs replaced by its
Git effect. The current publisher recognizes only a peer whose old OID equals
the repaired local ref's former tip. A peer at an older mapped OID falls into
ordinary range validation and fails the current commit-subject policy. The
remote transition uses the same too-narrow exact-tip test.

Native pre-push classifies `refs/tags/*` as a release publication but passes
its OID through a commit-peeling range and proof path. This admits a plain
commit OID as a tag even though the release publisher requires a signed
annotated tag.

## Goals and Non-Goals

- Admit only a peer OID present in a verified repair mapping, for a target ref
  included in that repair's exact ref effect, when the proposed commit descends
  from the verified replacement tip.
- Apply the same relation at commit-range, accepted-topology and remote-CAS
  planning boundaries. Continue checking every forward commit after the
  replacement under both baseline and proposed policies.
- Require native pre-push to validate the tag object itself and the existing
  accepted release-source contract, not merely its peeled commit.
- Do not change the historical commit messages, claim that a peer was already
  published, permit an arbitrary non-fast-forward update, or weaken proof,
  accepted-effect, signer trust, version or remote-drift requirements.

## Decisions

### Reuse completed repair provenance, not remote history inference

Extend the existing repair observer with a ref-scoped mapped-peer relation.
It validates the immutable repair effect and mapping, then requires the peer's
old OID to be an exact mapping key. The replacement tip, not the mapped peer
commit, is the forward-validation baseline: every rewritten commit was already
checked by the repair effect, while later commits remain newly introduced.
The relation is read-only and does not turn remote advertisements into
authority. Reject unrelated or ambiguous repairs rather than comparing trees
or accepting a caller-provided mapping.

### Keep each publication boundary independent

Commit-range admission and remote transition consume the same validated
relation. The accepted branch still requires the current candidate head and
current repository-transition proof and accepted-effect provenance. Each peer
must advertise its exact expected OID; a failed or changed advertisement
blocks that peer's CAS. An unchanged peer remains eligible without a rewrite.
Do not broaden the local ref-repair helper, which has a stricter meaning.

### Reuse the native release-tag source owner

Pre-push validates a tag update through the existing release-tag source
contract: annotated object kind, trusted tag signature, exact tag name,
committed SemVer and accepted-source provenance. An absent peer tag can be
created; an identical peer tag is an idempotent no-op; a different peer tag
cannot be replaced. Ordinary branch and proposal pushes retain their current
admission path.

## Risks and Trade-offs

- A large mapping may be read more than once during a multi-peer preview.
  Keep the existing immutable repair observer as the single verifier and
  measure before adding caches that might obscure current trust or ref state.
- A peer can lag far behind the original repaired tip. A verified mapping
  proves historical identity only; current accepted proof and peer CAS still
  determine whether the newer content may be published.
- The native hook and the explicit publisher have different entry points.
  Regression tests exercise both against real Git objects and include a plain
  commit under a tag ref, not a mock-only tag classification.

## Migration Plan

Land and install the accepted ETHOS change before retrying the adopter's
publication. Re-run exact-head proof and publication preview against freshly
observed peer refs. The adopter's protected-branch rewrite remains a separate,
explicitly authorized and observed operation; no source migration is needed.
