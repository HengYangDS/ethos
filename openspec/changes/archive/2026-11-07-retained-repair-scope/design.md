# Design

## Context

See [proposal.md](proposal.md). `prove_retained_authoring` migrates the retained fixture's topic,
proves one change in it, and then runs the successor's pure paradigm repair as a preview and an
apply.

## Goals / Non-Goals

Goals:

- The harness proves what matters: the retired publication fields are repaired, and the repair
  changes nothing outside the obligations that a legacy retained adopter carries.
- The repaired set that the harness judges comes from the product, both in the unit test and in
  the journey.

Non-goals:

- Any change to `lane repair-paradigm` or the paradigm's obligations.

## Decisions

- **A required subset plus one admitted obligation.** The preview and the apply must each report
  both retired publication gaps. Every other repaired gap must carry the
  `repository_paradigm_branch_roles:` prefix. That obligation normalizes the default-valued branch
  roles the legacy fixture declares. Any other obligation still refuses with
  `package_retained_publication_repair_failed`.
- **The report keeps the evidence.** `publication_repair` stays `repaired`, and the report adds
  `publication_repaired_gaps` with the complete list.
- **The unit test uses the real repair.** Only the prewrite calls stay faked, so the repair's
  preview and apply both run the CLI on the materialized retained fixture.

## Risks / Trade-offs

- A later paradigm obligation that also repairs the retained fixture would refuse here until it is
  admitted by name. That is intended: each admitted obligation is a reviewed decision.
