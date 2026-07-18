# Design

## Boundary

The owner split is:

```text
.config/checks/**       tool-native policy and quality configuration
tools/ci/scripts/**     reusable execution runners and hosted-tool installers
.gitlab-ci.yml          hosted provider projection over tools/ci/scripts
.pre-commit-config.yaml local hook projection over tools/ci/scripts
system/tools.toml       gate registry explaining why each owner exists
```

This follows the kernel instead of the provider: CI is not the semantic center,
and `.config` does not become a hidden executable package. The runner scripts
are repository tools; their policy inputs remain in `.config/checks`.

## Mechanism

Move the scripts as files, then update active references in gate descriptors,
command payloads, provider projections, public quality command wrappers, and
architecture tests. Historical evidence and archived OpenSpec records remain
chronology unless they are active contracts.

Add architecture coverage that fails if executable scripts reappear under
`.config/ci/scripts` and that proves every active script path in hosted CI and
pre-commit points to `tools/ci/scripts`.

## Net Gain

The change deletes a misleading boundary rather than adding a subsystem:
configuration configures, tools execute, CI projects, and ETHOS proof consumes
the same runner surface locally and remotely.
