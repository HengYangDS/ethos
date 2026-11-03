# Design

## Context

See [proposal.md](proposal.md). The projection compiler passes each declared input to the CUE model
as `_inputs.<name>`. Today `inputs.node` binds `.config/mise/config.toml`, and the model reads
`_inputs.node.tools.node` for GitLab's `NODE_VERSION`.

## Goals / Non-Goals

**Goals:**

- One declaration owns the uv version of local, supply image and hosted runs.

**Non-Goals:**

- Deriving the Python versions of the hosted jobs, which follow the supported Python lines rather
  than the Mise pin.
- Changing the uv version or the setup action.

## Decisions

- **The model reads the existing Mise input.** The compiler already passes the Mise configuration
  to the model, so the uv version needs no new input or compiler code. The input is renamed `mise`,
  since it now serves two tools.
- **The rename touches a supply image input.** `.config/checks/ci-projection/policy.toml` is hashed
  into the supply image, so the image is rebuilt and bound before this lane's proposal is
  published. The uv 0.13.7 upgrade in the same lane requires that anyway.

## Risks / Trade-offs

- [A Mise uv pin that `setup-uv` cannot install fails hosted setup] → The pin is an exact released
  version, which `setup-uv` installs by version, as it installs the literal today.
