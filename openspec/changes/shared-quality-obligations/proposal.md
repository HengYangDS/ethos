# Proposal

## Why

D14, adopted on 2026-10-28, holds PDC Invariant 1 across the fleet: one durable obligation has one
narrow semantic owner, the author of its meaning. ETHOS owns, once, the obligations whose meaning is
the same for every repository, and is itself one of those repositories. Two exceptions remain:

1. `product_source` is a second resolver path. A registry at `system/gates.toml` whose history the
   running build shares skips the shared quality floor and judges dependency acceptance by its own
   committed policy. Its answer depends on a registry path and a merge base, which cannot change a
   repository's obligations.
2. The packaged `system/gates.toml` mixes the entries every repository runs with 28 gates that
   serve only ETHOS. An adopter that names one of them gets `proof_gate_not_importable`.

## What Changes

- **One registry per owner.** The packaged `system/gates.toml` holds only the obligations ETHOS owns
  for every repository: the seven shared floors and the two gates the starter rules require of every
  repository, `schemas` and `skills`, each declared in the form every repository runs. ETHOS
  declares its own gates in `system/repository-gates.toml`, which its profile names as any
  repository names its registry.
- **One resolver path.** A repository's obligations are a function of the carriers it authors and
  the values it declares. `product_source` and its three consumers are removed. One fact replaces
  it: a tree whose `pyproject.toml` declares the running product's distribution supplies the shared
  registry and their provider sources from that tree, as ETHOS's source runner already reads them.
  Dependency acceptance accepts a capture that names either the judging product's portable policy or
  the subject's own, compared by content.
- **ETHOS proves the shared floor.** `unit-architecture` and `javascript-tests` become behavior
  verifiers, with native JUnit and Cobertura or lcov outputs, and Node tests exercise every product
  JavaScript module and the npm launcher. A new `code-static` gate claims every static subject.
  `tools/**` and `noxfile.py` declare the tooling role.
- **The static floor reads declared values.** The shared Python static provider applies the
  import-sorting values a repository declares in its native Ruff configuration.
- **Contract texts.** The PDC's Product, Configuration Boundaries, Isomorphic Adopter Governance and
  Invariant 1; the quality and repository-paradigm requirements below; DR-0017, one obligation, one
  owner, extending DR-0012.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: "Adopters share applicable quality obligations" becomes "Every repository shares the
  obligations ETHOS owns", with ETHOS judged as every repository is; the static floor follows
  declared import-sorting values; resource coordination states the registry a repository declares.
- `repository-paradigm`: a repository declares its gates in its profile or in the registry file its
  profile names.

## Impact

- Python product code shrinks by 3 effective lines, to 69,983 of 70,000, and Python tests grow by
  38, measured with `ethos.measure` against `ebe90676a`; the shared floors' deletions follow in
  `shared-quality-floors`.
- Governed repositories: the composed floors stay unchanged field for field, so an adopter's policy
  digest is unchanged until it rebinds; the films' own registries at `system/gates.toml` stay their
  own; no active adopter names one of the 29 gates that move.
- ETHOS's default proof gains `openspec`, `markdown-links`, `markdown-lint` and `prose`, the floors
  its authored carriers select.
- Landing: one. The installed predecessor compiles the candidate as it compiles any adopter, because
  the candidate's registry is no longer at the packaged path; the hook reinstall after this landing
  then reads shared data by the same fact as the lane.
