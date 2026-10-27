# Design

## Context

See [proposal.md](proposal.md). The owner's decisions bind this Change:

- D2 (decision numbering) and D5 (雅 and the root constraint), approved on 2026-10-27 for design revision 4.1 and kept in revision 5.1;
- D10 (order), decided on 2026-10-27 for revision 5.1.

Revision 5.1 (`build/runtime/work/architecture-realization/`, Part I, "Changes") sets the scope:

- the decisions index;
- the Docs Registry sentences on decisions (299-300) and elegance (210-212);
- the PDC's views paragraph (522-525) and root constraint (51-54);
- the TP's file-limit owner (118-121), views clause (319-321) and order sentence (367-369);
- the confirmed outdated statements, contradictions and dead references whose owners are accepted specs (kernel, distribution, repository-governance, contracts, adapters), unshipped documents, research, history, Skills, CONTRIBUTING, README and the glossary.

Constraints:

- **Size.** The PDC is at its ceiling of 512 nonblank lines and the TP is at 488. The repository paradigm caps every Markdown file at 512.
- **Shipped documents.** The wheel ships the PDC, the Docs Registry, the glossary, the command plane, the quickstart and the rules (`pyproject.toml`). A shipped document may not link to a document the wheel omits.
- **Requirement length.** OpenSpec 1.15.0 strict validation fails a requirement whose text exceeds 500 characters, and only the archive simulation sees it.
- **Concurrency.** The product lane runs in parallel on disjoint owners. This Change touches no Python product code, no `system/gates.toml`, no `runner-and-mutation.md`, no TP 104-107 or 149-150, and no quality or repository-paradigm spec.

## Goals / Non-Goals

**Goals:**

- Every decision number from DR-0001 to DR-0016 is visible in order, with a reachable Git origin for each deleted record.
- 雅 keeps its full meaning in its one owner, the PDC; the Docs Registry and the TP link to it.
- The accepted specs and the knowledge carriers in scope no longer state behavior the code has removed, cite deleted files, or contradict the PDC.
- Every finding of the rerun currency and duplication reviews in these owners has a disposition.

**Non-Goals:**

- Mechanical reference checks; `knowledge-checks` adds them.
- The orphan policy documents and the rules index; `normative-layering` owns them.
- Skill description rewrites; `skill-workflows` owns them.
- Branch-role wording; `shared-quality-obligations` owns it.

## Decisions

### Decision numbering

The README lists each number in order. A current record is a link. Every other number is one line with five parts:

- its MADR status;
- the record's own word for that status;
- its decision date;
- its successor;
- the commit where its record last existed.

Each line cites a reachable commit:

- **DR-0001 to DR-0008:** `374d49d94^`, the parent of the commit that deleted them.
- **DR-0009:** `13864eb4f`, where the number was reserved. Revision 5.1 cited `a8b859b6f`, but no ref reaches that commit. Its twin `13864eb4f` has the same tree (`915f90c35`) and is reachable from `dev`.

Each line names its direct successor as its own record stated it, so DR-0002 and DR-0007 name DR-0004, and DR-0004's line names DR-0011 and the Docs Registry. The chain stays visible without repeating it.

### DR-0003 and DR-0005 stay index lines

The admission test (Docs Registry 275-278) admits a record only when the choice "cannot be expressed clearly by the current contract or source". Both decisions are expressed today:

- **DR-0003 (proof scope compatibility).** `src/ethos/surface/cli/proof/report.py` accepts the known proof scopes and gaps an unknown one. The command plane's "Routine Scoped Execution" states that host execution mints no proof. Its own revisit trigger (a scope-to-gate router) never fired, and the adopter migration it served is over.
- **DR-0005 (declarative lifecycle spine).** The spine table of `docs/architecture/declarative-governance-compiler.md` and `rules/declarative-lifecycle.md` carry it.

Both lines read "superseded", naming the current owners as successors, with the record's own word "accepted, until its deletion on 2026-08-15" beside it.

Alternative rejected: restoring them as records. They would restate the current owners, which is the duplication this Change removes.

### 雅 in one owner

- **PDC 522-525** carries the full meaning in its four existing lines: aesthetic judgment, taste, and artistic and cultural refinement, assessed in the rendered whole; restraint and alignment support it without defining it. The faithful, legible, accessible and navigable obligations and the ban on a second ontology stay.
- **PDC 51-54** states that the verses are authored design analogies, also within its four lines.
- **The Docs Registry's elegance item and TP 319-321** link to that PDC section instead of restating a narrower meaning.

The PDC stays at 512 nonblank lines; its rewrapped lines are longer, which `proseWrap = "preserve"` allows.

### The TP's file-limit owner and order sentence

- **TP 118-121.** The repository paradigm's `[size]` table owns the per-file ceilings (`src/ethos/contracts/paradigm/paradigm.toml`; repository-paradigm spec 403-414). TP 118-121 therefore links there instead of to `.ethos/rules.toml`.
- **TP 367-369.** The added sentence is revision 5.1's contract amendment text, verbatim. TP 49 and 56 keep their text.

### Spec deltas

Each corrected requirement is a MODIFIED block restating its complete text and every retained scenario. A requirement that only describes removed behavior is REMOVED with a reason and a migration note. No requirement text exceeds 500 characters. The archive simulation runs before proof.

### Pinned commits

A history or research citation of a commit that no ref reaches moves to its reachable twin with the same tree. The history index records each tree equality once.

### Dispositions

Each finding of the rerun reviews gets one of four dispositions: corrected here, linked, kept with a reason, or owned by a named Change. The table below records them.

## Risks / Trade-offs

- [A product-lane Change edits a file this Change edits] → The route keeps owners disjoint. `one-proof-per-change` starts only after this Change lands, and edits `command-plane.md`, which this Change leaves unchanged.
- [A shipped document gains a link to an unshipped one] → The installed-navigation test runs before proof: `tests/unit/repository` and `tests/architecture`.
- [A MODIFIED spec block drops a scenario] → Each block is restated from the accepted text, and strict validation with the archive simulation runs before proof.
- [The longer PDC lines read less evenly in the source] → The rendered text is unchanged in form, and the line ceiling stays met.
