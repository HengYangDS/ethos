# Proposal

## Why

Eight locked Python packages have newer releases that are now at least 24 hours old, the release
age ETHOS applies at lock time. alpha.30 and beta.2 held filelock, platformdirs, python-discovery
and virtualenv back because they were younger than that.

## What Changes

- `uv.lock` moves, by `uv lock --upgrade --exclude-newer <now minus 24 h>` and then a plain
  `uv lock` that drops the cutoff:
  - coverage 7.17.0 to 7.17.1;
  - dnspython 2.9.1 to 2.9.2;
  - filelock 4.2.7 to 4.2.8;
  - joserfc 1.7.7 to 1.8.0;
  - platformdirs 4.14.3 to 4.14.4;
  - python-discovery 1.9.2 to 1.9.4;
  - uncalled-for 0.4.1 to 0.4.2;
  - virtualenv 21.15.2 to 21.15.5.
- `pyproject.toml` raises the floors of the direct dependencies filelock (4.2.8) and platformdirs
  (4.14.4) to their locked versions, as the dependency hygiene gate requires.
- No package is added or removed. The supply image is rebuilt from the moved lock and bound.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A supply move changes no requirement, so `skip_specs: true` applies.

## Impact

`uv.lock`, `pyproject.toml`, `.config/ci/pipeline.cue` and `.gitlab-ci.yml`, and the Unreleased notes.
