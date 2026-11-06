## MODIFIED Requirements

### Requirement: Hosted supply preparation precedes expensive verification

Hosted verification SHALL prepare its declared scanner, budget and SBOM supply through the existing
supply owners before starting proof. Preparation failure SHALL preserve native diagnostics and exit
status, invalidate previous attempt reports, and produce a failed hosted observation without
executing proof. Package execution SHALL still validate supply in its own current environment.

#### Scenario: A declared tool cannot be prepared

- **WHEN** scanner, budget or SBOM preparation fails
- **THEN** expensive proof does not start and the native failure remains observable
- **AND** old proof, test and coverage reports cannot describe the new attempt
- **AND** the hosted receipt identifies failed supply without issuing an Attestation

#### Scenario: Prepared supply permits exact-source verification

- **WHEN** every required preparation succeeds
- **THEN** verification executes against the requested exact source
- **AND** a retained adopter runtime selector cannot redirect source CI to older code
- **AND** the later package boundary retains its own executable validation

#### Scenario: Linux runner reuses locked immutable supply

- **WHEN** a new GitLab checkout begins on a cold ARM64 runner
- **THEN** its image is selected by published OCI digest, not a mutable tag or local cache hit
- **AND** the image's input hashes match the checkout's Python and Node locks before provisioning or
  proof
- **AND** APT, PyPI and npm registry access are not required by the quality job
- **AND** missing or mismatched supply fails before any quality result is issued

#### Scenario: A Change alters a supply input

- **WHEN** a lane changes a file that the supply image's input manifest hashes, such as `uv.lock`
- **THEN** the lane binds an image built from its own proposal commit before it lands
- **AND** GitLab verifies the landed head with that image instead of refusing it

#### Scenario: A manifest input changes without a rebuilt image

- **WHEN** a manifest input differs from its bytes at the commit that the bound image was built from
- **THEN** the CI projection check refuses with `supply_image_stale:<path>` and names the rebuild
  and bind route, before any proof gate runs

#### Scenario: One selected Forge remains executable without its peer

- **GIVEN** two selected Forges project the same exact source and required CI graph
- **WHEN** one Forge's registry and release endpoints are unavailable and the other's runner has no
  local image or tool cache
- **THEN** the available Forge executes every required job from its own verified supply or
  independent sources
- **AND** the selected source, supply materials and resulting evidence remain bound to that Forge's
  run
- **AND** missing bytes or a peer-dependent fetch blocks before proof rather than accepting a
  warm-cache or other-Forge result

#### Scenario: Unqualified image is not published

- **WHEN** a newly built image cannot bootstrap a fresh checkout without network access
- **THEN** the build job fails before pushing that image
- **AND** the previously published digest remains available for diagnosis or rollback

#### Scenario: Native provisioning exceeds its execution deadline

- **WHEN** a native tool emits partial output before its bounded preparation times out
- **THEN** the supply entrypoint reports both available streams and the exact failed command
- **AND** owned descendants terminate before preparation scratch is removed
- **AND** a preceding successful tool cannot be mistaken for the failed attempt
