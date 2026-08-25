## ADDED Requirements

### Requirement: Package build temporary supply has a bounded owner

The OpenSpec build hook SHALL own temporary supply until the build target has
consumed declared `force_include` inputs.

#### Scenario: Successful build finalization reclaims supply

- **WHEN** a wheel or source build reaches finalization
- **THEN** the exact build-owned supply directory no longer exists.

#### Scenario: Build initialization failure reclaims supply

- **WHEN** initialization fails after supply allocation
- **THEN** the exact build-owned supply directory no longer exists
- **AND** the original failure remains observable.

#### Scenario: Editable build allocates no supply

- **WHEN** the hook initializes an editable build
- **THEN** it creates no OpenSpec supply directory.
