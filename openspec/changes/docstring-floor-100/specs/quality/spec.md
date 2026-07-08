## MODIFIED Requirements

### Requirement: Python Public-Surface Docstring Gate

ETHOS SHALL gate intent-bearing Google-style docstrings for public Python product surfaces
without requiring private helper docstrings to become a parallel documentation
store.

#### Scenario: Public docstring coverage is reported

- **WHEN** `ethos quality docstrings --json` runs
- **THEN** ETHOS reports configured source paths, minimum coverage, documented
  public-surface count, total public-surface count, missing symbols, Google-style
  conformance, and a non-blocking broader public-definition inventory
- **AND** the configured minimum coverage floor is 100 percent for product
  public surfaces
- **AND** the gate fails when public-surface coverage is below the configured
  threshold
- **AND** existing structured docstrings must use Google-style sections and their
  `Args` section must match the Python signature
- **AND** legacy reStructuredText or NumPy-style sections are rejected
- **AND** the gate scope is limited to product-visible Python surfaces such as
  CLI command functions, explicit exports, and package boundary docstrings
- **AND** hosted CI invokes the reusable docstring coverage script instead of
  duplicating the policy inline.
