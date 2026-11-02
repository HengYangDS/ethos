## MODIFIED Requirements

### Requirement: CI runner and retained-step records own their commands

`.config/ci/runners.toml` MAY name, per Forge, the executables and references
its CI runner provides beyond the toolchain and product runtime. Admission
SHALL count them as owned only in that Forge's pipeline files and in templates
the CI projection declaration projects into them, a template reaching several
Forges needing each Forge's record; a malformed record SHALL own nothing. A CI
step the retention record keeps SHALL be owned by that record as a whole until
its text changes.

#### Scenario: A runner executable is used by another Forge

- **GIVEN** `.config/ci/runners.toml` names `sha256sum` for `gitlab`
- **WHEN** only `.gitlab-ci.yml` invokes `sha256sum`
- **THEN** reference closure reports no orphan consumer for `sha256sum`
- **AND** once a GitHub workflow also invokes it, `sha256sum` is reported as an
  orphan consumer.

#### Scenario: A declared template belongs to its pipeline's Forge

- **GIVEN** `.config/ci/runners.toml` names `sha256sum` for `gitlab` and the
  CI projection declaration names `.config/ci/templates/hosted/gitlab-ci.yml`
  as the template of `.gitlab-ci.yml`
- **WHEN** the template and `.gitlab-ci.yml` both invoke `sha256sum`
- **THEN** reference closure reports no orphan consumer for `sha256sum`
- **AND** a YAML file under `.config/ci/` that no projection names still makes
  `sha256sum` an orphan consumer.

#### Scenario: A retained PowerShell step is owned as a whole

- **GIVEN** a retention record that keeps a PowerShell `before_script` step by file, job and digest
- **WHEN** a patch touches that pipeline without changing the step
- **THEN** admission reads no command names from the step
- **AND** once the step's text changes, admission reads it again
