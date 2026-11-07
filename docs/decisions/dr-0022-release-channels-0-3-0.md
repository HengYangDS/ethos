---
subject: ethos:decision:release-channels-0-3-0
role: decision
state: canonical
decision_id: DR-0022
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/distribution/spec.md
---

# DR-0022: From 0.3.0, Builds Are Immutable and Stages Are Evidence-Gated Channels

Status: canonical rationale. The distribution specification owns current behavior.

Date: 2026-11-05.

Purpose: preserve why 0.3.0 separates a build's identity from its qualification, and why a declared
local clean-room venue counts once the journey is hermetic.

See also: [DR-0015: Release stages follow a declared journey scope](dr-0015-release-stage-scope.md),
[DR-0018: A historical artifact is judged by the attestation made when it was produced](dr-0018-historical-artifact-attestation.md),
[DR-0021: Release 0.2.0 declares three journeys](dr-0021-release-scope-0-2-0.md) and the
[distribution specification](../../openspec/specs/distribution/spec.md).

## Context

On 2026-11-04 the hosted macOS arm64 runners took no jobs for hours, during a declared platform
incident. The macOS journey of one alpha was cancelled three times, so the next beta's tag waited
for it, and the beta after that waited for the beta. Both builds were proven, landed and verified on
every other platform, and the same published archive passed the macOS journey locally. Only one
venue's capacity was missing, and it stopped the whole release line.

Three causes follow from DR-0015's rule. The version string carries a qualification, so an identity
exists only after its evidence. Evidence is bound to the release run's hosted leg, so an outage has
no substitute. Identities are serialized through qualification, so a later build waits for an
earlier one. Promoting a build to beta also re-versioned it, a copy of the same code under a new
version.

## Decision

The owner decided on 2026-11-05 to adopt release channels, called option C, for the 0.3.0 line.

- **Builds are immutable identities.** Each landed release is tagged and released at landing, and
  its release run attests its own journeys. The default scheme is `0.3.0-dev.N`. The scheme remains
  for the Change that implements this record to settle, and its design must check the default
  against the version authority.
- **`beta`, `rc` and `stable` are channel pointers.** A pointer moves to a build only when the
  build's attestations satisfy the channel's declared criteria. The criteria stay DR-0015's:
  hosted verification on every supported platform, the declared journeys on macOS and Linux and no
  defect in a blocking class for beta, 72 hours of adopter use for the release candidate, and 7
  days for stable. A move is reversible and carries a receipt. It is not a rebuild.
- **A declared local clean-room venue counts for qualification once the journey is hermetic.**
  Until then, local runs stay supplementary evidence. The hermetic journey is a prerequisite of
  the channels, which makes local and hosted runs equivalent.
- **0.2.0 finishes under DR-0015 and DR-0021.** The two models never mix on one line.
- **Qualification is read as recorded.** A channel move reads a build's attestations as DR-0018
  reads a historical one, and does not re-judge them under a later policy.
- **Supersession.** From 0.3.0 on, this record supersedes DR-0015's rule that the stage is part of
  the version and that a stage tag follows its evidence. DR-0015's criteria and its
  undeclared-journey rule stay in force.

## Alternatives Rejected

- **Keep the stage in the version (option A):** rejected because every external outage stops the
  line, as on 2026-11-04.
- **Tag at landing and publish as a draft until qualified (option B):** rejected because the stage
  stays in the identity, so promotion still re-versions a build.
- **Count only hosted runners:** rejected because a hermetic journey on a declared local venue is
  equivalent evidence, and a venue outage would again have no substitute.

## Consequences and Boundary

- An outage in one venue delays one qualification, not every later identity.
- Adopters gain a channel form beside exact build pins. Channel records need the signing and
  attestation care that releases have.
- Evidence lives as attestations instead of prose in a changelog entry.
- This record is rationale only. The Change that implements it designs the identity scheme, the
  channel record, the promotion command and the distribution specification deltas, and is reviewed
  as its own Change after the hermetic journey lands.
- Planning documents named DR-0018, then DR-0020, for this decision. Both numbers are taken, so
  this record takes the next free number.

## Evidence and Revisit

- The 2026-11-04 incident above, and the design draft that compared options A, B and C and recorded
  the owner's two decisions on 2026-11-05.
- DR-0018's attestation rule is the basis for reading a build's qualification as recorded.

Revisit when the hermetic journey lands, when the identity scheme proves incompatible with the
version authority, or when a venue other than hosted runners and a declared local venue is proposed.
Retire this record when the distribution specification states the channel model itself.
