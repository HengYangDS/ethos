# Tasks

## 1. Decision Numbering

- [x] 1.1 List every decision number from DR-0001 to DR-0016 in order in `docs/decisions/README.md`. Current records stay links. Every other number becomes one line with its MADR status beside the record's own word, its decision date, its successor and a reachable commit where its record last existed. Done when the index has 16 entries without a gap and each cited commit is reachable from `dev`.
- [x] 1.2 Record the number history in the Docs Registry sentence on the decisions README (299-300). Done when the Docs Registry validation passes.

## 2. Original Intent And Order

- [x] 2.1 Carry the full meaning of 雅 in PDC 522-525 and the note that the root constraint's verses are authored analogies in PDC 51-54, without adding lines. Done when the PDC has 512 nonblank lines and `markdown_lint` and `prose` pass.
- [x] 2.2 Link the Docs Registry's elegance item (210-212) and TP 319-321 to the PDC's meaning instead of restating it. Done when `markdown_links_report` passes.
- [x] 2.3 Name the repository paradigm's per-file ceilings as the owner of numeric file limits in TP 118-121. Done when the link resolves.
- [x] 2.4 Add revision 5.1's order sentence, verbatim, to TP 367-369. Done when TP 49 and 56 are unchanged.

## 3. Accepted Specs

- [x] 3.1 Correct the kernel persistence requirement to match the PDC: Commitment is transient. Done when strict validation passes.
- [x] 3.2 Correct the distribution requirements that name removed Node policy files and versions. Done when strict validation passes.
- [x] 3.3 Correct or remove the repository-governance requirements that describe removed runtime, status and package behavior, cite deleted files or pin an old OpenSpec version. Done when strict validation passes.
- [x] 3.4 Drop the removed governance-context fields from the contracts spec. Done when strict validation passes.
- [x] 3.5 Match the adapters release-identity requirement to the current runtime identity. Done when strict validation passes.
- [x] 3.6 Simulate the archive and validate every spec strictly. Done when no requirement exceeds 500 characters and every spec validates (12 specs valid after the simulated archive: `build/evidence/knowledge-currency/archive-simulation.log`).

## 4. Other Knowledge Carriers

- [x] 4.1 Correct the dead activation globs and outdated Skill reference statements, and refresh the affected package digests. Done when the `skills` gate passes.
- [x] 4.2 Align CONTRIBUTING's signing setup, emergency path and small-change statement with the specs and PDC 453-458. Done when `markdown_lint` and `prose` pass.
- [x] 4.3 Make README tell agents to run `ethos status` first, name both declared publication peers and bind the proof command to the exact head. Done when every command shown matches the CLI help.
- [x] 4.4 Add Continuation to the glossary, align the Change, Authority, proposal-ref and Required Gap entries, and remove the unsourced Proof Lattice entry. Done when the installed-navigation test passes.
- [x] 4.5 Correct the outdated statements and dead references in the unshipped documents, research and history, and move unreachable pinned commits to their reachable twins, recording each tree equality once. Done when every cited commit is reachable from `dev` (14 moved to their twins in the history index's "Rewritten Commits" table; `4dd2f442` no longer exists and is marked missing).

## 5. Review And Record

- [x] 5.1 Give every finding of the rerun currency and duplication reviews in these owners a disposition in design.md. Done when the table lists every finding with corrected, linked, kept or owner (audit reports: `build/evidence/knowledge-currency/`).
- [x] 5.2 Restore documentation-comprehension 12.1: confirm that foundation research is organized by semantic question with its arguments, sources and incoming links preserved. Done when the review finds no duplicated authority in research (eight foundation files answer eight questions in `docs/research/foundations/README.md`; this Change corrects only currency, and the link and registry tests pass).
- [x] 5.3 Record the Change under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, land it and publish `dev` to GitHub.
- Publish `main` only after the `dev` push run's ETHOS CI has succeeded, then read the `main` push's rule suite, which settles revision 5.1's open D11 observation. GitLab follows on the owner's notice.
