## ADDED Requirements

### Requirement: hook installation retires the legacy runtime locator

After the final package-only runtime manifest, public entrypoint, and hook
launchers validate, hook installation SHALL remove the common-directory
`ethos-runtime-python` legacy locator whether it is a regular file or symlink.
The receipt SHALL report the locator disposition. Failure before validation
SHALL leave the locator untouched.

#### Scenario: obsolete locator survives from a source launcher

- **WHEN** successful hook installation finds `ethos-runtime-python` in the Git common directory
- **THEN** it removes the locator and reports it as retired without changing runtime or SQLite authority

#### Scenario: runtime validation fails

- **WHEN** the final runtime manifest or launcher validation fails
- **THEN** hook installation fails closed and does not remove the legacy locator
