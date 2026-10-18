---
subject: ethos:decision:comparative-correction
role: decision
state: canonical
decision_id: DR-0014
decision_status: accepted
relations:
  current_owner: ../governance/adopter-boundary-and-retirement.md
---

# DR-0014: Comparative Correction

Status: canonical rationale. The adopter boundary contract owns current behavior.

Date: 2026-10-18.

Purpose: preserve why a replacement may drop an incumbent finding that evidence outside the
candidate shows false, and why that correction never weakens the non-regression rule.

See also: [Adopter Boundary And Retirement](../governance/adopter-boundary-and-retirement.md),
[DR-0006: Proof trust boundary](dr-0006-proof-trust-boundary.md), and the
`quality-evidence-admission` OpenSpec Change.

## Context

Comparative assurance lets a replacement execution substrate take over from an incumbent only when
the replacement is equal or stricter: it must preserve every incumbent blocking gap. That rule
catches a replacement that silently loses an obligation, but it has no outcome for an incumbent
finding that is itself wrong.

An adopter report, issue 1 in the ETHOS GitLab project, described such a finding. The product's
isolated Ruff fallback ran without the subject's declared Python target, so it judged at the
checker's default target. Real-Ruff regressions confirmed that the default changes target-sensitive
findings such as the import classification of a standard-library module. Task 11.9.2.2 of the
`quality-evidence-admission` Change made the fallback judge at the declared target. A replacement
that carries this fix no longer reports such a finding, and the strict superset rule would block it
as a comparative false negative. Without another outcome an adopter keeps a workaround instead: the
reporting adopter guarded its `tomllib` import, and an exempted path would hide true findings in its
whole scope.

The accepted quality scenario in which a candidate weakens its own quality policy already draws the
boundary: the trusted prior floor judges the candidate until an independently admitted transition
replaces it.

## Decision

A replacement may drop one incumbent blocking finding only as a correction that a retirement
judgment admits separately from the comparative result. The correction names the finding, its
subject, the obligation the finding claimed to judge, and the evidence that shows it false.

That evidence comes from outside the candidate: the repository's native tool run on the same subject
under the configuration the repository accepted before the candidate, or a verifier admitted outside
the candidate. The candidate's own policy, tests, exemptions or configuration changes, including a
changed target, never show an incumbent finding false.

A correction removes one false finding, not its obligation. The replacement still judges that
subject under that obligation, and every other incumbent blocking gap stays required. Until a
correction is admitted, the missing gap remains a comparative false negative.

## Alternatives Rejected

- **Keep the strict superset rule:** rejected because every product fix for a false finding would
  fail comparative assurance, which pushes adopters to keep broad exemptions that also hide true
  findings.
- **Let the candidate show the finding false:** rejected because self-certification is the weakening
  that the accepted quality scenario forbids; a candidate could change its target or exemptions
  until the finding disappears.
- **Treat a correction as stricter or advisory:** rejected because it would hide a semantic change
  inside the non-regression claim and make a real false negative indistinguishable from a
  correction.

## Consequences and Boundary

- Comparative assurance has three allowed outcomes. A dropped incumbent gap without an admitted
  correction still blocks.
- A correction never narrows a subject's scope or the common rule floor, and it never replaces an
  obligation with an exemption.
- A candidate's change to its own target or tool configuration is a policy transition that its own
  Change admits; it is not correction evidence.
- This record adds no checker or registry. Retirement judgments record corrections with their
  evidence, and a future comparative checker implements the same contract.

## Evidence and Revisit

- [Adopter Boundary And Retirement](../governance/adopter-boundary-and-retirement.md) states the
  current comparative outcomes and what a retirement judgment records.
- The accepted quality specification scenario "A candidate weakens its own quality policy" requires
  an independently admitted transition before a candidate's weaker policy judges it.
- Task 11.9.2.2 of `quality-evidence-admission`, fix `a28692620` with proof `dbe68ce0`, made the
  isolated Ruff fallback judge at the declared target.

Revisit if no evidence outside the candidate can judge some class of finding; such findings stay
blocking until a verifier exists. Retire this record when a comparative checker's specification
preserves these rejected alternatives and limits.
