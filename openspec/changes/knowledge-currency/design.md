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
- **DR-0009:** `13864eb4f`, whose text of DR-0008 first named DR-0009 as a record to create. DR-0009 was never written and had no index row. Its tree twin `a8b859b6f` (tree `915f90c35`) survives only under preservation refs (`refs/keep/…`, `refs/codex/snapshots/…`), which no branch reaches. `13864eb4f` is on `dev` and `main`.

Each line names its direct successor as its own record stated it, so DR-0002 and DR-0007 name DR-0004. DR-0004's line names the Docs Registry, which its retained historical carrier names as the current owner, and says that no replacement record was created. The retained carrier keeps its exact bytes, so its Git origin is cited from the index rather than added to the carrier.

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

Each corrected requirement is a MODIFIED block that restates its complete text and every retained scenario. A requirement that only describes removed behavior is REMOVED, with a reason and a migration note. No requirement text exceeds 500 characters, and the archive simulation runs before proof.

OpenSpec 1.15.0 refuses a MODIFIED block that drops or renames a scenario, because it matches scenarios by name. A stale scenario therefore keeps its title and gets a true body. Where a kept title would be false (kernel "Chronicle remains authoritative evidence", distribution "Linux bootstrap repairs supported prerequisites"), the requirement is REMOVED and ADDED under a new name with the same obligation.

A delta cannot change a spec's Purpose, so the kernel and repository-governance Purposes are edited directly in their spec files.

### Pinned commits

A history or research citation of a commit that no ref reaches moves to its reachable twin with the same tree. The history index records each tree equality once.

### Dispositions

Each finding of the rerun reviews gets one of four dispositions: corrected here, linked, kept with a reason, or owned by a named Change. Four read-only audits at `ad9108d70` produced the findings. Their reports, with file, line and evidence for every finding, are in `build/evidence/knowledge-currency/`.

| Owner                                  | Findings                      | Corrected here                                                                                                                     | Not corrected here                                                                                                                                                                                                                                                                                                                                      |
| -------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| kernel spec                            | 8                             | 8, the Purpose included                                                                                                            | —                                                                                                                                                                                                                                                                                                                                                       |
| distribution spec                      | 4                             | 4                                                                                                                                  | —                                                                                                                                                                                                                                                                                                                                                       |
| contracts spec                         | 9                             | 9                                                                                                                                  | —                                                                                                                                                                                                                                                                                                                                                       |
| adapters spec                          | 5                             | 5                                                                                                                                  | —                                                                                                                                                                                                                                                                                                                                                       |
| repository-governance spec             | 48 requirements               | 46: 19 modified, 8 replaced under new names, 19 removed; plus the Purpose                                                          | Release Policy's in-repository executable rule is kept: it matches PDC 405-406, and the bare-name PATH lookup in `publication.py:380-390` is a product defect for the product lane. The `release_mirror` key in "Accepted closeout remains candidate-first and non-self-approving" is left to `shared-quality-obligations` with the branch-role wording |
| Unshipped documents, research, history | 26 rows and 15 pinned commits | 23 rows; 14 commits moved to reachable twins; research receipt claims re-dated, with custody digests cited where the bytes survive | distribution Homebrew status (true as stated); a dated historical table (MEF 264); `4dd2f442` is gone with no twin, so its description stays and the citation is marked missing                                                                                                                                                                         |
| Skills                                 | 7                             | 7, with both package digests                                                                                                       | —                                                                                                                                                                                                                                                                                                                                                       |
| CONTRIBUTING                           | 4                             | 4                                                                                                                                  | —                                                                                                                                                                                                                                                                                                                                                       |
| README                                 | 3                             | 3                                                                                                                                  | —                                                                                                                                                                                                                                                                                                                                                       |
| Glossary                               | 7                             | 7                                                                                                                                  | —                                                                                                                                                                                                                                                                                                                                                       |

Findings outside these owners go to the route's Changes:

- **`normative-layering`:**
  - `rules/module-layout.md` still names the retired `python-size` gate;
  - `authority.md` points at a missing North Star section;
  - the retained entry in `docs/_meta/taxonomy.toml` is past its 2026-10-15 review;
  - `docs/_meta/stable-paths.toml` has no reader;
  - the proof-hosts spec still names parity, Claim admission and promotion targets;
  - `ethos-change-lifecycle` was removed without a `[retired]` record in the activation file.
- **`bounded-supply-and-state`:**
  - `topology.toml` still admits `.cache/local-state/` and `.config/ethos/`;
  - the supply image's uv `0.13.4` lags the locked `0.13.5`.
- **`application-result-contract`:**
  - the status schema diagnostic is labelled `target: "data"` when nothing is emitted;
  - `governance_context` is optional on results.
- **`knowledge-checks`:** the `skills` gate accepts an activation glob that matches no tracked file.
- **`skill-workflows`:** Skill descriptions, `uv run ethos` portability, link portability and `--expect-head` in post-checks.
- **`promote-by-identity` and `one-proof-per-change`:** the spec ranges they own, which this Change leaves untouched.

`command-plane.md` keeps "explicitly human-authorized": that authorization is the maintainer's, which CONTRIBUTING now links to the PDC's bounded maintainer recovery.

## Risks / Trade-offs

- [A product-lane Change edits a file this Change edits] → The route keeps owners disjoint. `one-proof-per-change` starts only after this Change lands, and edits `command-plane.md`, which this Change leaves unchanged.
- [A shipped document gains a link to an unshipped one] → The installed-navigation test runs before proof: `tests/unit/repository` and `tests/architecture`.
- [A MODIFIED spec block drops a scenario] → Each block is restated from the accepted text, and strict validation with the archive simulation runs before proof.
- [The longer PDC lines read less evenly in the source] → The rendered text is unchanged in form, and the line ceiling stays met.
