## Context

See [proposal.md](proposal.md). ETHOS currently combines native Python and Node
locks with policy TOML, downloaded-binary installers, generated CI provider
files, and immutable action/image pins. The semantic information is mostly
present, but some installer defaults and provider literals duplicate owner
values and the current audit does not prove a complete relation.

## Goals / Non-Goals

**Goals:**

- Establish a finite inventory of controlled direct inputs and one semantic
  owner for each identity.
- Upgrade every inventoried input to the current stable release and bind it by
  the strongest native integrity mechanism available.
- Generate or check all secondary surfaces from those owners and fail before
  expensive gates when an owner or projection is stale or ambiguous.
- Delete duplicate defaults rather than synchronize them manually.

**Non-Goals:**

- Do not add a dependency-update service, environment ledger, or workflow
  engine.
- Do not make mise, Pixi, Renovate, a forge, or a hosted registry authoritative.
- Do not rewrite archived historical evidence.
- Do not change ETHOS lifecycle, runtime, or product semantics outside the
  supply-chain and quality contract.

## Decisions

### Native declarations remain semantic owners

`pyproject.toml` plus `uv.lock` own Python package resolution. `package.json`
plus `package-lock.json` own Node packages. Existing narrow policy TOML files
own downloaded tools and runtime channels. CI templates are the source for
generated forge files. No aggregate version catalog is added because it would
duplicate these native owners.

Alternative considered: centralize every version in one new manifest. Rejected
because native package managers would still require their own declarations,
creating a second authority rather than deleting one.

### Projection checks replace duplicated defaults

Installer and runner scripts read their existing policy owner or require an
explicit value from the owning caller. Generated GitHub and GitLab files are
re-rendered from canonical templates. A focused repository audit compares
owner, lock, integrity, and projection relations and reports exact residue.

Alternative considered: retain shell defaults and add tests that keep them in
sync. Rejected because the duplicate state remains expressible.

### Stable currency is observed, not persisted as a second truth

Native package resolvers and authoritative upstream release metadata determine
whether a direct input is current. The repository persists only the selected
exact release and integrity binding; observations used during an upgrade remain
evidence, not a mutable update database.

### mise and Pixi remain outside this atom

A disposable mise experiment proved that it can resolve and lock the external
binary set across supported platforms. Adoption is deferred to a successor
replacement atom because this change must first close the current upgrades and
because adding mise without deleting installers would increase authority
surfaces. Pixi is not selected because it would overlap the existing uv and npm
dependency and environment owners.

## Risks / Trade-offs

- **Simultaneous upgrades expose behavior changes** → run focused owner and
  projection checks after each coherent declaration cut, then one full proof on
  the frozen candidate.
- **Latest changes while the atom is open** → repeat authoritative resolution
  immediately before final proof and record the observation boundary.
- **Downloaded assets differ by platform** → require exact per-platform
  checksums and test the complete supported tuple set.
- **Deleting script defaults reduces ad-hoc invocation convenience** → owner
  scripts resolve their canonical policy automatically and fail with one exact
  remediation when it is unavailable.

## Migration Plan

1. Materialize the complete inventory and regression tests before modifying
   declarations.
2. Update native owners and regenerate locks using their package managers.
3. Update downloaded-tool policies, exact checksums, action SHAs, and image
   digests; remove duplicate script defaults.
4. Regenerate provider files from canonical templates and prove equality.
5. Run format, focused quality/supply-chain checks, full proof, and release
   compatibility at the frozen HEAD.
6. Archive and land through the public lifecycle. A failed gate leaves the
   existing accepted supply chain unchanged; no compatibility owner is retained.
