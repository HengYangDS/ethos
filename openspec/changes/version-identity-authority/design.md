## Context

See [proposal.md](proposal.md). Current package metadata has three manually
maintained version literals, while runtime provenance carries hashes but no
truthful product or distribution identity. Distinct builds therefore collide at
the package-manager identity layer even when lower-level hashes differ.

## Goals / Non-Goals

**Goals:**
- Make one tracked value the product-version authority.
- Preserve SemVer product meaning while using standards-compliant PEP 440 and
  npm projections.
- Bind version, source, artifact, runtime, channel, and acceptance facts without
  conflating them.
- Reject reuse before artifact activation or publication.

**Non-Goals:**
- Make Git tags, a Forge, or a mutable release database the version owner.
- Reimplement SemVer or PEP 440 parsing.
- Retain `0.1.0a2` as a current compatibility identity.

## Decisions

### One tracked product-version source

`VERSION` owns the SemVer product version. Build and quality projections read
that file; package manifests cease to be independent owners. A generated source
module may package the resolved build identity, but it is a projection and is
never hand-edited.

Alternative rejected: keep `pyproject.toml` authoritative and copy its value to
npm. That preserves the present multi-owner drift and gives a Python packaging
file authority over the product identity.

### Standards own parsing and comparison

`packaging.version.Version` owns PEP 440 normalization/comparison. npm tooling
owns npm package-version validation. ETHOS owns only repository-specific
selection, provenance binding, monotonicity, and non-reuse predicates.

Alternative rejected: local regex parsers. They increase maintenance and risk
in an area already standardized by mature tools.

### Release and development identities are different projections

The product version describes the next accepted generation. A release build
uses its exact normalized distribution version only when release authority and
source/tag coordinates are satisfied. Any untagged work or candidate build adds
standard PEP 440 development/local source identity, so two commits never claim
the same consumable build identity.

Alternative rejected: append a Git SHA to product SemVer itself. Source identity
is provenance, not product meaning.

### Runtime currentness binds the complete immutable manifest

The runtime digest includes product/distribution identity, source commit/tree,
wheel digest, ABI/interpreter/platform, channel, and acceptance state. `CURRENT`
selects that content-addressed runtime. Inspection validates all fields rather
than trusting a version string.

Alternative rejected: select by product version alone. Equal labels cannot
prove equal bytes or provenance.

### Accepted version reuse is a repository admission problem

Release admission compares the requested version and exact source/artifact facts
against immutable Git and Attestation evidence. Forge tags/releases are checked
as projections when configured; their absence cannot invalidate local-only
version truth.

Alternative rejected: a new mutable release ledger. It would become a parallel
truth source and add recovery obligations.

## Risks / Trade-offs

- **Dynamic build identity can make casual local wheels non-reproducible if the
  source coordinate is omitted.** → The build hook requires exact committed
  source identity and fails closed for release artifacts.
- **Moving three manifest literals to one authority requires generated projection
  checks.** → The quality gate verifies projected manifests and rejects drift.
- **Historical `0.1.0a2` runtimes remain on disk.** → They are immutable history
  only; currentness rejects them and consumer-aware runtime GC is handled by the
  runtime-authority lifecycle, not by a compatibility reader.

## Migration Plan

1. Advance the product authority once beyond `0.1.0a2`; never emit that identity
   again.
2. Replace static package literals with derived projections and add RED tests for
   uniqueness, comparison, and mismatch rejection.
3. Extend public and runtime manifests, then make selectors validate the full
   provenance.
4. Build one newly identified candidate artifact, prove it, and only then admit
   accepted release identity and package-only runtime installation.
