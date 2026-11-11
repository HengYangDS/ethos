# Design

## Context

See the [proposal](proposal.md). The scratch design is Phase T item 1's
`repository-spec-draft-2.md` with its review; this Change is that design's step 2.

## Goals / Non-Goals

Goals: one fixture construction authority, every step's enforced `python_tests` delta at most 0.

Non-Goals: a template cache, per-build spec records, rewriting call sites, and the builder families
of later steps (publication, lifecycle, proof and gates, budget).

## Decisions

1. Fields cover only what rows 1 to 5 and the signature family use: object format, files, signed,
   adoption (`carriers` or `governance`), release mirror, docs only, candidate, runtime, lane and
   holder. A later step adds a field only with the builder it replaces.
2. `build` runs stages in field order and returns the repository with the sibling paths of its
   candidate and Work Lane, so presets stay one expression.
3. Rows 1 to 5 keep their names; no wrapper, alias or second path survives this Change.
4. Old and new builders were compared outside `tests/` before the change: refs, objects,
   checkouts, local configuration, reflogs, ETHOS common files and leases were equal for every
   preset; `signature_repository` now records its files in the native-source commit, with the
   same head tree.

## Risks / Trade-offs

The step saves no budget (effective lines -2, tokens +0); its value is the single authority that
the later steps extend.
