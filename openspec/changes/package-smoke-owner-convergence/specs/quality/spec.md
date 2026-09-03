## MODIFIED Requirements

### Requirement: Fresh Offline Installation

The full release proof SHALL build deterministic Python artifacts and execute
the complete package-only repository lifecycle through one `local-install-smoke`
owner. Installed command help, version, module origin, package and runtime
identity, hook activation, lifecycle continuations, and artifact digests SHALL
bind to the same stable HEAD. The complete Python test surface SHALL verify gate
declarations, orchestration, and pure contracts without installing another
wheel, materializing another runtime, or executing a second repository
lifecycle.

#### Scenario: Offline installation succeeds

- **WHEN** `uv run --frozen --offline python -m nox -s install_smoke` completes
- **THEN** one wheel installation SHALL activate an immutable Git-common runtime
  without a source-checkout or ambient `ethos` dependency
- **AND** the acceptance transaction SHALL create one environment, install the
  frozen production dependency closure into it exactly once, and install the
  wheel into that same environment without resolving dependencies again
- **AND** the selected runtime manifest, wheel digest, source commit, source
  tree, distribution version, and runtime digest SHALL agree
- **AND** the selected runtime SHALL remain executable after its bootstrap
  environment is removed and SHALL repair a stale hook projection through its
  own public continuation
- **AND** the installed runtime SHALL start a first Work Lane, expose the exact
  official OpenSpec metadata prewrite continuation, and recover a partially
  completed retirement through the public receipt-bound command
- **AND** the runtime SHALL exclude development-only dependencies
- **AND** disposable state SHALL stay under `build/runtime/**` and be removed
  before a passing receipt is published under `build/evidence/**`
- **AND** cleanup failure, source-checkout imports, network access, HEAD
  movement, or identity drift SHALL fail the gate without a passing receipt

#### Scenario: Full proof selects package acceptance

- **WHEN** the full proof graph executes both `unit-architecture` and
  `local-install-smoke`
- **THEN** package-only lifecycle acceptance SHALL execute exactly once through
  `local-install-smoke`, after its declared build dependency
- **AND** `unit-architecture` SHALL NOT install a wheel, activate a package
  runtime, create a lifecycle worktree, or replay package acceptance
- **AND** the local-install receipt SHALL report the result of every required
  package-only lifecycle assertion for the exact HEAD
- **AND** installed runtime and lane command observations SHALL preserve the
  validated public result, exit code, and captured stderr without introducing
  another policy or lifecycle owner
