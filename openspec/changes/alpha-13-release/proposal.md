## Why

The latest public release, 0.2.0-alpha.12, predates fixes that accepted ETHOS already carries.
Host link checks observe current authored Markdown, and an unstaged deletion no longer stops them.
Native tool resolution no longer leaves records in the host's mise state, and admitted repository
commands can run their own mise tasks again. Adopters install only published releases, so none of
them receives these fixes until a successor is published. Architecture Publisher's bootstrap and
the hosted verification of `data-department-work-guidelines` wait for that successor.

## What Changes

- Move the product version to 0.2.0-alpha.13 in `VERSION`, the npm launcher manifest and its lock
  entry, and the version tests that read them.
- Curate the Unreleased notes, together with the mise fix that landed without one, into the
  `0.2.0-alpha.13` entry dated on the release day.

Out of scope: beta qualification, which DR-0015 grants only after hosted verification on every
supported platform and adopter journeys from published assets on macOS and Linux; supply refresh;
and changes to the release mechanics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no specified ETHOS behavior.

## Impact

`VERSION`, `CHANGELOG.md`, `distributions/npm/package.json`, `package-lock.json` and the version
tests in `tests/unit/cli/test_version_command.py`, `tests/unit/release/test_version_identity.py`
and `tests/unit/release/test_policy_attestation.py`. The signed tag, the hosted release assets and
adopter rebinds follow the landing as separate effects.
