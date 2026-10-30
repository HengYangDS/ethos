# Design

## Context

Docs health (`repository/registry/docs/health.py`, `docs_health_report`) builds the docs registry
before it measures document length. When a document's retained origin is not supplied, the
registry raises `docs_metadata_invalid:...:retained_origin_unobserved`, and the report returns that
single gap with no length gap. The native audit passes `observed_document_origins(root)`; the
checks behind `per-file-ceiling-parameters` task 3.1 and its fleet preview did not.

The two documents above 500 are current: the Product Design Contract (`role: policy`, 510 nonblank
lines) and the Command Plane (`role: reference`, 512).

## Goals / Non-Goals

**Goals:**

- Both documents are at most 500 nonblank lines without losing meaning.
- Each moved statement keeps one owner, with a route from where a reader looked before.

**Non-Goals:**

- Changing the ceiling, the measure or docs health.
- Rewording the Product Design Contract beyond the consolidated sentences.

## Decisions

### 1. The command plane routes to the operational roots

"Hidden Operational Roots" (90 nonblank lines) describes `ethos lane` and `ethos hook`, which
support admission and are not public workflow commands. It moves whole into
`docs/reference/operational-roots.md` with the command plane's metadata shape and a projection of
the Product Design Contract's First-Hour UX, which states that these operations support admission
only. The command plane keeps a short section with the route, and the reference index lists the new
document.

### 2. The Product Design Contract routes documentation shape to the Docs Registry

The contract's documentation paragraph restates what the Docs Registry owns: `docs/README.md` as
entrypoint, directory READMEs, and the admission and naming of Decision Records. The paragraph keeps
its evidence-retention meaning and names the Docs Registry for the rest, so each rule has one home.
The edited section wraps at the repository's 100-column Markdown width, as the paragraphs edited in
`050e7971c` do; the words of its other paragraphs are unchanged.

### 3. The archive keeps its record

The archived task 3.1 and fleet preview are history. This Change states their correction and
evidence instead of editing the archive.

## Risks / Trade-offs

| Risk                                              | Mitigation                                                                                             |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| A reader follows an old link to the moved section | No tracked document links to the section's anchor; the command plane keeps the heading with its route. |
| The contract sits exactly at the ceiling          | The next addition must consolidate again; the ceiling, not wrapping, decides.                          |
