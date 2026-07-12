## MODIFIED Requirements

### Requirement: Canonical declarations have a self-contained package projection

ETHOS SHALL package canonical system declarations without making a wheel build
depend on paths outside its source distribution.

#### Scenario: The core wheel is built from its source distribution

- **WHEN** the `ethos-core` source distribution is unpacked for a wheel build
- **THEN** each packaged declaration is read from the sdist-local
  `src/ethos_core/data/` projection
- **AND** the wheel contains the corresponding `ethos_core/data/` resource
- **AND** the build does not require checkout-relative `system/` paths.
