## 1. Contract and RED

- [x] 1.1 Specify one product-version authority, identity layers, unreleased
  build uniqueness, accepted non-reuse, and public JSON behavior; verify with
  `openspec validate version-identity-authority --strict`.
- [ ] 1.2 Add failing tests proving no independent version literals remain,
  distinct source commits cannot share a consumable distribution identity, and
  `0.1.0a2` cannot be emitted again.
- [ ] 1.3 Add failing tests for structured `ethos --version --json`, package-only
  provenance, runtime-manifest validation, and same-version/different-source or
  artifact rejection.

## 2. Single authority and projections

- [ ] 2.1 Implement the tracked product-version authority with mature version
  parsing and derive Python/npm metadata; verify projection and comparison tests.
- [ ] 2.2 Remove the static `pyproject.toml`, root npm, and launcher npm version
  owners and prove repository-wide reference closure.
- [ ] 2.3 Derive unique work/candidate distribution identity from exact source
  coordinates while reserving exact product identity for an admitted release;
  verify wheel metadata from two commits differs.

## 3. Provenance and admission

- [ ] 3.1 Extend package/runtime identity with product, distribution, source,
  artifact, interpreter/ABI/platform, channel, and acceptance facts; verify a
  package-only runtime can self-inspect without source paths.
- [ ] 3.2 Implement release monotonicity, non-reuse, tag/metadata/manifest/hash
  agreement, and local-only/single-Forge/dual-Forge checks; verify all negative
  cases have zero effect.
- [ ] 3.3 Add one public UTF-8 human/JSON version projection and verify stable
  fields and absence semantics without double-encoded JSON.

## 4. Closure verification

- [ ] 4.1 Run focused format, lint, type, import-boundary, release, runtime,
  package-only, schema, and strict OpenSpec checks without building a legacy
  `0.1.0a2` artifact.
- [ ] 4.2 Run the full HEAD-bound proof once, then use the public lifecycle for
  archive, post-archive proof, candidate integration, accepted closeout, and one
  newly versioned immutable package/runtime delivery.
