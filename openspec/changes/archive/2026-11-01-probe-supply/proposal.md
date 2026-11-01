# Proposal

## Why

ETHOS ships one Python behavior probe to the repositories it governs
(`src/ethos/adapters/gates/python_quality.py`), and decision D21 of the end-state design makes that
probe the one runner of ETHOS's own suite, starting with `test-runner-unification`. Wherever a
repository has Mise configuration, the probe takes uv and Python from Mise
(`python_quality.py:225-237`, through `locked_tool` in `src/ethos/adapters/toolchain/mise.py`).
ETHOS declares Python 3.14.10 in `.config/mise/config.toml` but no uv, and its hosted supply
installs only cue, actionlint, Node and Go through Mise (`tools/ci/toolchain/native.py:212-234`).
Through the probe, ETHOS's suite would therefore stop at `mise_supply_unavailable:uv` on the
workstation and find no Mise Python in the GitLab supply image. The governed repositories that run
the probe already declare uv in Mise (`aigw-cli` and `web-ingestion-benchmark`): ETHOS does not yet
meet the paradigm it ships.

Read on 2026-11-01, five locked Python packages have newer stable releases (`uv lock --upgrade
--dry-run`), and npm and Mise report nothing else newer within ETHOS's constraints.

## What Changes

- Mise: `uv = "0.13.6"`, the latest release and the version `uv.lock`, setup-uv and the supply
  image already use; `mise lock` records it for the six locked platforms.
- Hosted supply: the native supply installs every declared one of Node, Python and uv through Mise,
  and the offline image check requires each of them, so the GitHub jobs and the GitLab image
  provide the Mise Python and uv that the probe resolves.
- Python: `uv lock --upgrade` moves cachetools 7.2.8, filelock 4.2.6, nodeenv 1.12.0, platformdirs
  4.14.2 and python-multipart 0.0.33; the direct floors of filelock and platformdirs rise to their
  locked versions, as the dependency declaration check requires.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This aligns ETHOS's own supply with the paradigm it ships and refreshes locks under the
existing quality and runtime contracts, so `skip_specs: true` applies.

## Impact

- `.config/mise/config.toml`, `.config/mise/mise.lock`, `uv.lock`, `pyproject.toml`,
  `tools/ci/toolchain/native.py` and its test, and `CHANGELOG.md`. No product code changes.
- Every hosted job that prepares the Mise supply also installs Mise's Python and uv, which costs
  their download on GitHub's runners and a larger GitLab image.
- GitLab's supply manifest check refuses the landed head until the supply image is rebuilt from it
  and bound. The binding is its own Change, and GitLab receives the head only with it.
