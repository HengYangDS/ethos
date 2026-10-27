# Proposal

## Why

The owner decided on 2026-10-27 that the decision records be completed and numbered in sequence, that outdated knowledge be brought up to date, and that the full meaning of 雅 replace its narrowed form (decisions D2 and D5 of design revision 4.1, kept in revision 5.1). The owner also decided D10 of revision 5.1: the Changes that remove an iteration cost every later Change pays come first, which needs one added sentence in the terminal plan.

Read-only audits of 2026-10-27, rerun for this Change, found these knowledge carriers out of date:

- **Decision numbers.** 8 of 16 decision numbers have neither a record nor an index line. DR-0001 to DR-0008 were deleted on 2026-08-15 without supersession lines, and DR-0009 was reserved and never written.
- **Accepted specs.** Some describe behavior the code has removed, and the kernel spec contradicts the product design contract (PDC) on what persists.
- **Dead references and false claims.** Specs, Skills, history and research cite deleted files, rewritten commits and limits that changed.
- **The PDC** reduces 雅 to restraint, and the Docs Registry repeats that reading.
- **The terminal plan (TP)** names the wrong owner of numeric file limits, and its order rule forbids moving a cost-removing Change ahead ("Reordering requires a proved prerequisite, not convenience").

Revision 5.1 orders this Change first in the knowledge lane, before any reordered product Change starts.

## What Changes

- **Decisions index.** The index lists every number from DR-0001 to DR-0016 in order. A current record is a link. Every other number is one line with its status, its decision date, its successor and the Git commit where its record last existed. Each status shows the MADR status beside the record's own word. DR-0003 and DR-0005 become lines naming their current owners, because those owners already express them, so the admission test fails (see design).
- **Docs Registry.** It records the number history in the README sentence it owns, and its elegance item links to the PDC's meaning of 雅 instead of restating a narrower one.
- **PDC.** Its views paragraph carries the full meaning of 雅. Its root constraint states that the verses are authored design analogies. Both edits keep the PDC at 512 nonblank lines.
- **TP.**
  - The repository paradigm's `[size]` table owns the numeric file limits.
  - The views clause links to the PDC's 雅.
  - One sentence admits a measured iteration cost that every later Change pays to be removed ahead of the batches.
- **Accepted specs.** kernel, distribution, repository-governance, contracts and adapters drop or correct the statements that describe removed behavior, cite deleted files or contradict the PDC. The Work Lane coordination requirements of repository-governance follow in `coordination-spec-currency`, because one delta file must stay within the 512-line Markdown ceiling.
- **Other carriers.** Unshipped documents, research, history, Skills, CONTRIBUTING, README and the glossary correct their confirmed outdated statements and dead references. Pinned commits that no ref reaches move to their reachable twins with the same tree.
- **Dispositions.** Every finding of the rerun currency and duplication reviews in these owners gets one: corrected, linked, kept with a reason, or owned by another Change.
- **CHANGELOG.** One entry under `[Unreleased]`.

Out of scope, each owned by another Change of the route:

- the governance policy documents and the rules index, owned by `normative-layering`;
- the quality and repository-paradigm specs and the branch-role wording, owned by `shared-quality-obligations`;
- `runner-and-mutation.md` and the archive requirements, owned by `one-proof-per-change`;
- `system/gates.toml` and TP 104-107 and 149-150, owned by `gate-input-reuse`;
- Skill description rewrites, owned by `skill-workflows`;
- the mechanical reference checks, owned by `knowledge-checks`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `kernel`: the persistence requirement matches the PDC; Commitment is transient.
- `distribution`: requirements that name removed Node policy files and versions are corrected.
- `repository-governance`: requirements that describe removed runtime, status and package behavior or cite deleted files are corrected or removed.
- `contracts`: removed governance-context fields are dropped.
- `adapters`: the release identity requirement matches the current runtime identity.

## Impact

- Documentation, accepted specs, Skills and the PDC and TP, with the PDC line-neutral. No Python product code changes.
- Restores the withdrawn task documentation-comprehension 12.1 (DR-0016). Research is already organized by question, so the task closes on this review.
- Adopters are not touched. aigw-cli and DDWG adopt the same number history in their own Changes, before the release that ships `knowledge-checks`.
