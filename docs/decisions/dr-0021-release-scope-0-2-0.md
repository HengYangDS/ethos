---
subject: ethos:decision:release-scope-0-2-0
role: decision
state: canonical
decision_id: DR-0021
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/distribution/spec.md
---

# DR-0021: Release 0.2.0 Declares Three Journeys and Narrows DR-0015's Hosts

Status: canonical rationale. The distribution specification owns current behavior.

Date: 2026-11-07.

Purpose: preserve why 0.2.0 declares macOS arm64, Linux x64 and Linux arm64 journeys, why Windows
x64 and the Homebrew channel are conditional or deferred, and which of DR-0015 stays in force.

See also: [DR-0015: Release stages follow a declared journey scope](dr-0015-release-stage-scope.md),
[DR-0006: Proof trust boundary](dr-0006-proof-trust-boundary.md), the
[distribution specification](../../openspec/specs/distribution/spec.md) and the `rc-plan` and
`dr-0015-successor` OpenSpec Changes.

## Context

DR-0015 declared 0.2.0's journeys on macOS arm64, Linux x64 and arm64, and Windows x64, and left
GitLab-hosted CI, GitLab publication and the Homebrew channel undeclared. A review on 2026-11-07
found that the declaration outran the evidence. The Windows suite has never run in full, and the
journey refuses Windows. The pipeline declares no Linux arm64 journey leg although DR-0015 names the
platform. A Homebrew formula that delegates to the host's existing Mise owner was proposed, with no
installation yet tried. The GitLab CI component has no hosted journey.

Twenty releases in eleven days also left each adopter a pin bump per release, which put DR-0015's
72-hour candidate clock out of reach. The owner decided the scope on 2026-11-07, directly or under
delegation the same day, after an expert committee reviewed the release path.

## Decision

This record supersedes DR-0015's declared journeys for 0.2.0 and nothing else.

- **Declared for 0.2.0:** journeys from installation through Mise from the GitHub release to
  release on macOS arm64, Linux x64 and Linux arm64.
- **Windows x64 is not declared for 0.2.0.** It becomes a 0.3.0 focus. Its archives stay optional
  legs checked by smoke and inventories, its full suite runs non-blocking and timed, and the release
  entry names it not qualified.
- **Homebrew is declared for 0.2.0 only if both checks pass:** a macOS installation spike, and a
  brew leg that delegates to the host's Mise and covers install, test, upgrade, rollback,
  uninstall and the refusal on a host without Mise. Otherwise it moves to 0.3.0, because only
  fixes land after the release candidate.
- **The GitLab CI component is not qualified for 0.2.0.** GitLab publication stays undeclared.
- **The release candidate gate applies.** It requires the release-candidate items of the committee
  resolution, and the 72 hours run on one frozen beta. They start only after that beta's journeys
  pass on every declared host and its golden-path journey passes, and they count from the last
  landed adopter bump. During the soak only exceptions that D19 admits land: a defect that blocks
  a landing, corrupts an installation or admits a wrong proof.
- **Releases batch weekly under D19.** Every engine release waits for the weekly batch unless it is
  such a defect fix.
- **In force from DR-0015:** the stage rule (alpha, beta, release candidate, stable and their
  evidence), the naming of an undeclared journey as not qualified, adopter acceptance as the
  adopter's own, and tag immutability. DR-0022 changes the stage rule from 0.3.0 on.

## Alternatives Rejected

- **Qualify Windows before the release candidate:** rejected because it delays the candidate by at
  least one round of Windows triage on a suite that has never run, for a platform no adopter uses
  yet.
- **Declare Homebrew unconditionally:** rejected because no installation has been tried, and a
  formula that owns a second Mise would split the role.
- **Qualify the GitLab CI component:** rejected because no hosted journey exists, which repeats the
  intranet-environment gate that DR-0015 removed.
- **Keep DR-0015's four platforms and mark Windows failing:** rejected because a declared journey
  that cannot pass blocks the release candidate and misdescribes the product.

## Consequences and Boundary

- Windows users have no 0.2.0 journey claim. The release entry says so by name.
- Homebrew's place in 0.2.0 is decided by evidence, not by this record. A failed spike or leg moves
  it to 0.3.0 without a new record.
- The release candidate arrives one to two weeks later than the owner's own criteria alone. The
  CLI authorization of the candidate is stated as caller-asserted. An approval principal that the
  executing agent cannot reach is deferred to a DR-0006 successor.
- This record adds no checker. Release preparation applies the scope, and the distribution
  specification delta carries its wording.

## Evidence and Revisit

- The committee's resolution holds the release-candidate gate, the declared hosts and the owner's
  decisions of 2026-11-07. Release 0.2.0-beta.6 locked and installed through Mise's `github:`
  backend on macOS with provenance verification. Linux and Windows installs were not run.
- D19 in the architecture realization design states the weekly batch.

Revisit when the Windows suite passes in full, the Homebrew checks have run, or a GitLab-hosted
journey exists. Retire this record when the distribution specification states the declared journeys
and the conditions above itself.
