## ADDED Requirements

### Requirement: Hosted verification preserves its evidence plane

Hosted CI SHALL execute declared source-quality owners against the exact event
object without requiring a local Work Lane, Lease, candidate checkout, active
Change, or installed mutation hooks. Its result SHALL remain host observation,
not repository acceptance proof, and SHALL retain gate and command failure
facts. Local proof, native package conformance, and provider success remain
independent obligations.

#### Scenario: Hosted checkout has no local lifecycle state

- **WHEN** hosted verification runs at the expected object
- **THEN** the declared default gate set, including coverage-floor, executes with its dependency closure through the existing gate owner
- **AND** official OpenSpec validation runs from the locked repository supply
- **AND** absent local candidate/runtime state does not authorize mutation or invalidate a passing host observation

#### Scenario: Result is stale, malformed, empty, or unsuccessful

- **WHEN** execution fails, HEAD changes, coordinates disagree, required gaps remain, or the observation envelope is invalid
- **THEN** the hosted receipt blocks and preserves the available diagnostics
- **AND** no passing local status or unrelated proof can override that result

#### Scenario: Locked runtime export has no ambient Python

- **WHEN** a package runtime invokes uv with its authenticated interpreter in an offline minimal environment
- **THEN** uv selects that exact interpreter without a download or ambient rediscovery
- **AND** lock, dependency, and runtime identity checks remain enforced
