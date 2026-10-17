# Design

## Context

`current_document_length_gaps` in `src/ethos/repository/registry/docs/health.py` skips every path that `_official_openspec_carrier` matches: the archive, accepted specifications, and an active Change's `proposal.md`, `design.md`, `tasks.md` and delta specs. The skip follows the scenario "A normative OpenSpec carrier exceeds the document ceiling", which leaves those carriers to official validation and capability review.

With OpenSpec 1.14.2, `openspec validate --strict` reports missing task checkboxes, task identities outside their group, duplicate task identities, and ADDED requirement text over 500 characters. It does not inspect proposal or design structure: a Change whose proposal and design contain none of their template sections validates cleanly. It also leaves MODIFIED requirement text unbounded, while strict validation of the specifications that `openspec archive` produces rejects text over 500 characters; `lane archive-change` therefore fails only after a full proof.

The official CLI resolves the artifact outputs of every active Change (`openspec status --all --json`) and a schema's template files (`openspec templates --schema <name> --json`). The OpenSpec governance report already runs that CLI for every governed root during plan and proof, through one bounded read batch.

## Goals / Non-Goals

**Goals:**

- Measure every active Change artifact with the ceiling that bounds other current Markdown.
- Derive the required proposal and design headings from the templates the official CLI resolves, with no copy held by ETHOS.

**Non-Goals:**

- Accepted specifications keep their exemption. Removing it requires splitting each capability above the ceiling into cohesive capabilities, which waits until no active Change carries deltas for that capability.
- Checks that official strict validation already performs are not repeated. Unnumbered tasks, which the official validator deliberately ignores and no governed repository has, stay unchecked.
- Task wording length and session size have no official bound; authors and review keep them.
- ETHOS still requires a design for every Change, although the official schema makes it optional, because "Official spec-free Changes compile acceptance" derives acceptance from the design's meaning.
- Gaps are not repaired automatically, because consolidating an artifact needs semantic judgement.

## Decisions

- **Resolve templates instead of declaring sections.** For each schema in use, the governance report reads the template files that the official CLI returns and takes their literal second- and third-level headings; a heading that holds an HTML comment is a placeholder. Declaring the sections in `paradigm.toml` with a drift test was rejected: it is a second authority that a project-local template or an OpenSpec upgrade would silently contradict.
- **Check the proposal and design only.** The tasks template has only placeholder headings, and the specs template shows `## Purpose` and `## ADDED Requirements` as examples that a valid delta may omit; strict validation owns both artifacts.
- **Require the literal outline in order, and allow additions.** A required heading appears under its template parent and after its template predecessors; other sections, such as the optional Migration Plan and Open Questions, may follow. Rejecting unknown sections was rejected, because the official instructions list optional sections and forbid none.
- **Bound active artifacts by removing their exemption.** `_official_openspec_carrier` keeps only the archive root, which the paradigm declares immutable, and accepted specifications. Active artifacts need no name inference; they are measured like other tracked Markdown.
- **Simulate the archive instead of copying its rules.** Proof of the selected active Change, the one whose commitment the proof admits, runs the official `archive` for that Change on a disposable projection of the exact head tree and then official `validate --specs --strict`. Repeating the 500-character limit for MODIFIED text in ETHOS was rejected: it copies one official rule and misses any other check that only the archived specifications reveal.
- **Report where the checks already run.** Template gaps join the OpenSpec governance report, and length gaps stay in document health. Both reach every governed repository through the governance audit and plan or proof evaluation, without a new gate.

## Risks / Trade-offs

- [A runtime with these checks blocks every governed repository whose active Changes do not conform] → Run the checks against each repository's dev head first and report every gap to its owner; each adopter rebinds only after its gaps are cleared.
- [`proof-throughput` cannot pass with a 2,959-line design and delta specs of 884 and 702 lines] → Retiring it is a precondition of this Change.
- [An OpenSpec upgrade can add a required heading] → The pinned upgrade's own proof runs these checks, so its owner conforms the artifacts in the same upgrade.
- [Archive simulation adds work to every proof of an active Change] → It copies only the OpenSpec tree and runs two official commands, which is small next to a full proof.
- [The governance report reads more official state] → The reads join its existing batch: one artifact-graph read and one template read per distinct schema, usually one.

## Migration Plan

1. Retire `proof-throughput` in its own lane: move its open work into focused successor Changes, keep only current decisions in its design, prove, archive and land it.
2. Write this Change's `quality` delta against the archived requirement, then implement, prove, archive and land.
3. Report each adopter's gaps to its owner before it rebinds to a runtime with these checks; ETHOS's own active Changes conform through this Change's proof.
4. Rollback: revert the implementation commits, and adopters rebind to their predecessor runtime. No artifact or data migration is involved.
