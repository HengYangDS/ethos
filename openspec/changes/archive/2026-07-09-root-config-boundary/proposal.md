# Root Configuration Boundary

## Why

`ruff.toml` and `pytest.ini` were still root-level tool configuration surfaces.
They were deliberately thin, but they still taught the wrong product boundary:
a vendor tool discovery file at repository root looked like a truth center. ETHOS
should keep package metadata, repository substrates, hosted projections, and
quality policy in separate physical owners.

## What Changes

- Move Ruff policy fully into `.config/checks/ruff/ruff.toml` and keep the
  ignored-rule ratchet in `.config/checks/ruff/ratchet.toml`.
- Move pytest configuration into `.config/checks/pytest/pytest.ini` while keeping
  pytest runtime cache under ignored `build/runtime/tool-cache/pytest` and proof
  evidence under `build/evidence/quality/tests/`.
- Make owner scripts pass explicit Ruff and pytest config paths from the
  repository root.
- Update active docs, tool catalog, OpenSpec quality requirements, and tests so
  root-level Ruff/Pytest config files cannot silently return.
- Keep adopter CI scaffold provider-neutral by emitting ETHOS/OpenSpec public
  command-plane checks instead of product-repository owner scripts or assumed
  pytest/Ruff commands.

## Capabilities

- `quality`: subject=root-config-boundary; reuse=modify; change=remove-root-config;
  facet:lifecycle=quality; facet:surface=config,ci,docs,openspec,test,adoption;
  facet:authority=source,test,system,docs,openspec

## Out Of Scope

- No new quality command plane.
- No change to historical evidence or archived command text.
- No claim that adopter repositories share the ETHOS product repository's Python
  test or lint stack.
- No removal of root files that are repository substrates or provider projections
  with no admitted explicit-config alternative.
