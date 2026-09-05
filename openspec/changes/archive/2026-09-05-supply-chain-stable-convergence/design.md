## Context

See proposal.md for motivation. Existing manifests and policy files already own
direct versions; lockfiles, immutable digests, and hosted CI files are derived
or mechanically checked projections. The defect is stale values, not a missing
version-management abstraction.

## Goals / Non-Goals

**Goals:**

- Advance every stale repository-controlled direct input to the verified
  stable release available from its authoritative upstream.
- Regenerate native locks and immutable image bindings, then prove source,
  package, and installed-runtime compatibility.
- Preserve one semantic owner for every controlled identity.

**Non-Goals:**

- No new dependency registry, update bot, compatibility shim, or host software
  mutation.
- No prerelease, floating tag, or unverified major-version adoption.
- No new version carrier: `VERSION` remains the sole product SemVer authority.

## Decisions

1. **Update only stale owners.** The version audit uses PyPI, npm, Node's
   official release index, GitHub releases and refs, and OCI manifests. Already
   current identities remain untouched to avoid meaningless churn.
2. **Use native resolvers.** npm regenerates `package-lock.json`; uv upgrades
   the Python closure. Integrity metadata is never edited by hand.
3. **Keep compatibility distinct from currentness.** Exact Node LTS/current
   compatibility releases stay unchanged because both are current. Python's
   supported 3.12-3.14 matrix remains a compatibility contract, not a request
   to drop older supported runtimes.
4. **Preserve CI projection ownership.** Template files remain authoritative;
   GitHub and GitLab provider files are regenerated or checked from those
   templates rather than independently designed.
5. **Separate activation from target build supply.** An already selected
   runtime may coordinate activation, but an exact source checkout builds only
   through its own root `.venv`. That environment must match the complete lock,
   including build tooling; only the exported no-development production closure
   is projected into the immutable runtime. Package-only successor construction
   keeps its existing content-addressed closure path.
6. **Validate behavior before acceptance.** Official OpenSpec validation,
   focused supply tests, the full gate graph, build, package-only install, and
   runtime version inspection must all pass on one frozen candidate.
7. **Advance the product prerelease once.** `0.2.0-alpha.4` identifies the
   accepted runtime that bundles OpenSpec 1.12.0 and the refreshed dependency
   closure; source and artifact digests remain the finer-grained identities.

## Risks / Trade-offs

- **A stable dependency release changes behavior** → reproduce at the smallest
  affected gate and either adapt to the current contract or revert that exact
  input; do not add a compatibility layer.
- **An OCI tag moves during the change** → bind the verified multi-platform
  digest and validate the declared image identity before acceptance.
- **OpenSpec 1.12 changes artifact behavior** → run official strict
  validation and repository OpenSpec lifecycle tests before full proof.
- **A transitive upgrade expands churn** → accept resolver-owned transitive
  movement only when the complete locked closure remains green.

## Migration Plan

Update the Change contract first, then change existing manifests and policy
owners, regenerate locks and CI projections, and run the verification ladder.
Rollback is the exact Git parent before landing; no compatibility state or
secondary registry is created.
