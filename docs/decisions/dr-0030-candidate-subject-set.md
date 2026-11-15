---
subject: ethos:decision:candidate-subject-set
role: decision
state: canonical
decision_id: DR-0030
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/distribution/spec.md
---

# DR-0030: The Candidate's Subject Set Is Read From Trees, and a Frozen Repository Is a Waiver

Status: canonical rationale. The distribution specification owns current behavior.

Date: 2026-11-15.

Purpose: preserve which governed repositories the release candidate's condition counts, why that
count is never a number in a record, and the one waiver the owner granted with the set.

See also: [DR-0029: The release candidate gate gains the law, and its dates become earliest
dates](dr-0029-release-candidate-gate-successor.md), whose rule for a later waiver this record
follows and which it does not edit; [DR-0026: The 0.2.0 release candidate gate is recorded with
three waivers](dr-0026-release-candidate-gate.md); and the `release-predecessors` OpenSpec Change.

## Context

DR-0029 lets the candidate be cut when every subject is bumped to the frozen beta and 72 hours
have passed since the last bump. It does not say which governed repositories are subjects. The
archived `rc-scope-plan` design counts them as eleven adopter pins.

On 2026-11-15 that number was wrong in both directions. One governed repository is frozen on its
runtime by its own stated status and takes no release. Two repository families are under repair
and cannot pass a proof yet. Other governed repositories exist only on a forge, where the
releasing host reads no tree. A condition that counts a fixed number of them never reads true.

The owner decided the set and the waiver on 2026-11-15. DR-0029 requires that a later waiver is a
successor record that names it.

## Decision

- **The set.** The candidate's condition counts a governed repository that the releasing host can
  read, that is inside the support window and that takes the release. A repository takes the
  release by selecting a runtime of the release line, with or without a tracked pin. The
  distribution specification defines the window.
- **A reading, never a number.** The count is read from the repositories' trees by the read that
  the `release-predecessors` Change adds. No record states the count of subjects as a number.
- **The waiver.** One governed repository is frozen on its runtime by its own stated status. It is
  a waiver that names a shape and a runtime: one benchmark repository, on the 0.2.0-beta.10 line.
  The condition does not count it.
- **Under repair.** Two repository families under repair migrate in their own lanes. They are no
  prerequisite of the candidate or of the older selector form's retirement.
- **Only on a forge.** A governed repository that exists only on a forge is not classified until
  its maintainer says whether it takes the release.

## Alternatives Rejected

- **Count a fixed number, the archived scope plan's eleven:** rejected because the number includes
  repositories that take no release or cannot yet pass a proof, so the condition can never read
  true, and because a number in a record is wrong on the day a repository joins or leaves.
- **Count every governed repository:** rejected because the releasing host cannot read a
  repository that exists only on a forge, and because a frozen repository or one under repair
  would hold the candidate for a reason that no release removes.

## Consequences and Boundary

- The count exists only on a host that reads the trees, at the time it reads them. Two readings
  on two days may differ, and neither is a record.
- The waiver changes only what the candidate's condition counts. The frozen repository's release
  stays one that later releases upgrade from while its last landed bump is inside the support
  window.
- A repository under repair, or one that exists only on a forge, becomes a subject when the
  releasing host can read it, it takes the release and it is inside the support window. This
  record admits none of them and sets no date for them.
- This record names no repository, adds no checker and no rule for a governed repository, and is
  not edited after acceptance. A later waiver or a change of the set is a successor record that
  names this one.

## Evidence and Revisit

- The owner's decision of 2026-11-15, which the proposal of the `release-predecessors` Change
  states.
- The reader's count of that day, relayed by the release lead and not measured again by that
  Change: 13 readable trees, all selecting the 0.2.0-beta.10 runtime; by form, 7 with the older
  table form, none with a bare pin and 6 with no pin. It is the reading of one day. It is not
  the count of subjects and fixes no number.
- The frozen repository's status was relayed by the session that owns that repository.

Revisit when the frozen repository states another status, when the maintainer of a repository that
exists only on a forge answers, and when the first read on the releasing host differs from the
relayed reading. Retire this record with DR-0029, when 0.2.0 has shipped.
