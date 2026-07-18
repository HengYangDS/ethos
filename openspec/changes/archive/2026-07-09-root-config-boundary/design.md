# Root Configuration Boundary Design

## Boundary

The change separates four subjects:

1. `pyproject.toml` — Python package/workspace metadata and uv wiring.
2. `.config/checks/ruff/` — Ruff policy and ignored-rule ratchet.
3. `.config/checks/pytest/` — pytest execution config and test policy.
4. `tools/ci/scripts/` — executable owner scripts that bind tool configs to the
   repository root and produce proof evidence.

Root-level `ruff.toml` and `pytest.ini` disappear. Direct vendor invocation is no
longer the source of truth; owner scripts are the executable proof surface.

## Net Gain

- Removes two root tool-policy files without adding a new semantic center.
- Makes `.config/checks/<concern>/` the MECE owner for tool policy.
- Preserves pytest and Ruff behavior through explicit config paths and focused
  tests.
- Prevents ETHOS adoption scaffolding from projecting product-repository internals
  into other repositories.
- Turns stale command examples into current owner-script or ETHOS command-plane
  examples.

## Recovery

If a tool version later proves unable to honor explicit config paths, the recovery
path is a narrow root shim with no policy body and an explicit OpenSpec decision.
The default remains concern-owned policy under `.config/checks/`.

## Documentation Command Boundary

Active product docs may show repository-owned CI owner scripts because those scripts
are the reusable proof surface. The docs command-example gate admits only the bounded
`tools/ci/scripts/*.sh` family; arbitrary `tools/**` command roots remain rejected.
