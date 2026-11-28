---
subject: ethos:decision:windows-support-removed
role: decision
state: canonical
decision_id: DR-0038
decision_status: accepted
date: 2026-11-26
relations:
  current_owner: ../../openspec/specs/distribution/spec.md
  updates: DR-0029
---

# DR-0038: ETHOS Supports macOS and Linux Only, and the Removal Lands Inside the Law Freeze

Purpose: record the owner's decision that ETHOS ends its support for Windows, his decision that the
removal lands before 0.2.0 although the law freeze holds, and the four pieces that stay one release
or longer with the condition that ends each.

See also: [DR-0029: The Release Candidate Gate Gains the Law, and Its Dates Become Earliest
Dates](dr-0029-release-candidate-gate-successor.md), whose law freeze this record makes one
exception to.

## Context

On 2026-11-25 the owner decided that ETHOS ends its support for Windows in its continuous
integration and every other part, and that no remnant stays. He set the platforms each Forge runs:
GitHub arm macOS, arm Linux and x64 Linux; GitLab arm macOS and arm Linux. Until a later Change adds
the macOS job, ETHOS's GitLab pipeline runs arm Linux alone. DR-0029 froze the law from the tag of
0.2.0-beta.11 to 0.2.0: a narrowing or a ruled defect fix passes; a new rule, or a supply move that
adds a gap, does not. The removal of a platform is neither a narrowing nor a ruled defect fix, so it
could land inside the freeze only by his word.

## Decision

- **The supported platforms are macOS arm64, Linux arm64 and Linux x64.** No release from the one
  that carries this record publishes a Windows archive; apart from the four pieces below, the
  product keeps one path, the POSIX one.
- **The removal lands before 0.2.0**, by the owner's decision of 2026-11-26: the freeze gives
  way for this one Change, `windows-support-removal`. Which weekly release ships it follows
  DR-0029's entry rule: the first whose cut finds it proven.
- **Four pieces stay**, each until the condition that ends it holds, by the owner's decision of the
  same day:

| Piece                                                                                                                             | It leaves when                                                                                                                                       |
| --------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| The launcher's drive-letter alternative                                                                                           | the release that ships the repair by which an activation writes the launchers of the runtime it selects (a Change of its own), or a later release    |
| The entry `nt` of the shipped hook declaration                                                                                    | no earlier than the next release, once ETHOS's own root and every governed repository the releasing host can read select this release or a later one |
| The reader's acceptance of `nt`                                                                                                   | once no governed repository the releasing host can read selects, or holds as its rollback, a runtime whose declaration has the entry                 |
| The entry `windows` of the repository paradigm's `leaving_platforms`, and its report `repository_paradigm_retained_step_platform` | no earlier than the next release, by the owner's decision in the Change that makes a retention record naming `windows` incomplete                    |

## Alternatives Rejected

- Landing after 0.2.0. The owner decided against it on 2026-11-26: the removal lands before 0.2.0.
- Removing the four pieces now. A changed launcher makes the product refuse its own rollback across
  the change (run on 2026-11-25); the readers of 0.2.0-beta.11 and 0.2.0-beta.12 refuse a
  declaration without `nt` (read, not run); a later reader meets the declarations of releases
  through this one when it activates a held rollback; and a tree that passes today is not refused
  without a report a release earlier (R14 of DR-0029). The owner kept them on 2026-11-26, as the
  release lead recommended.

## Consequences and Boundary

Four governed repositories (`architecture-publications` and the three film repositories) pin ETHOS
by the `http:ethos` table with rows for `windows-arm64` and `windows-x64` (read 2026-11-26). An
upgrade by the paradigm repair that moves the pin writes the release's bare entry, and the rows
leave with the table. What a bind does with a table that keeps the rows is not yet measured; the
Change measures it in its lane on copies of `architecture-publications` and `ethos-film`. If that,
or DR-0029's copies run, shows a new gap or refusal there, DR-0029 allows no tag until the
maintainer of the governed repositories has removed the rows, each in that repository's own lane.
That order is the design's; the owner named none.

A pipeline declaration that names the runner system `windows` no longer compiles against the common
CI model, and the model cannot report first. The census of 2026-11-25 found no such declaration
among the seven checkouts that compile against the common model; if DR-0029's copies run finds one,
DR-0029 allows no tag until the maintainer of the governed repositories changes it in that
repository's own lane. A tree the copies run cannot read meets the failure at its next bind.

A retention record that names the platform `windows` is reported, not refused, in this release. The
GitLab macOS job for ETHOS is a Change of its own.

## Evidence and Revisit

Decided by the owner. On 2026-11-25: Windows support is removed entirely, leaving no remnant in
ETHOS's current text, with the plan, its release and the platforms each Forge runs; ETHOS's GitLab
macOS runner is left to the release lead. On 2026-11-26: the removal lands before 0.2.0, and the
four pieces stay. On 2026-11-28: the accepted text that the Change retires, rewords and adds, the
two sentences of the product design contract and this record enter as he was shown them, each
with its Chinese meaning, including the deletions in two commits and the two effects that no
earlier release reported. The
census of the governed checkouts, the run and the readings are in the design of the Change
`windows-support-removal`. Revisit at each release: the first piece when a release ships the
activation repair; the second and third from `ethos/runtime/CURRENT` and `ethos/runtime/ROLLBACK`
under the Git common directory of ETHOS's own root and of each governed repository, read on the
releasing host by the maintainer of the governed repositories; the fourth when the owner
decides in the Change that makes a retention record naming `windows` incomplete.
