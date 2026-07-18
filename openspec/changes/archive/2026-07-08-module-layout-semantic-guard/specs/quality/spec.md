## MODIFIED Requirements

### Requirement: Python Module Layout Gate

ETHOS SHALL gate Python module layout as a quality property so semantic
sub-packages, package-root visibility, suffix-flat debt, flat-directory debt,
ordinary-module facade debt, same-directory flat-growth, baseline growth, and
import-alias compatibility residue cannot grow through normal write paths.

#### Scenario: Semantic module layout is reported and enforced

- **WHEN** `ethos quality module-layout --json` runs
- **THEN** ETHOS reports suffix-module, suffix-flat, flat-directory, private import
  alias, package `__init__.py` facade, ordinary module facade, dynamic
  compatibility facade, flat-growth, new-directory burst, and baseline-growth
  findings against `.config/checks/module-layout/policy.toml`
- **AND** new findings outside the ratchet baseline fail the gate
- **AND** the ratchet baseline declares `baseline_gap_limit`, fails unless the
  current allowed-baseline count exactly matches that limit, and fails when
  baseline entries no longer correspond to current findings
- **AND** the ratchet baseline declares per-kind baseline limits for suffix
  modules, suffix-flat groups, flat directories, private import aliases, package
  init facades, and ordinary module facades, so one debt category cannot grow
  while the total count appears unchanged
- **AND** adding baseline entries or raising `baseline_gap_limit` fails the gate
- **AND** adding governed modules to existing crowded directories fails before the
  directory reaches a larger flat-directory breach
- **AND** creating a brand-new directory with more than the configured direct
  module burst limit fails before the directory becomes a flat bucket
- **AND** package-root `__init__.py` files remain declaration-only docstring
  boundaries rather than re-export or compatibility facades
- **AND** ordinary modules cannot act as import-only or module-level `__getattr__`
  compatibility re-export facades
- **AND** hosted CI, pre-commit, local CI, and proof invoke the reusable
  `.config/ci/scripts/run-module-layout.sh` owner script instead of duplicating
  the policy inline.
