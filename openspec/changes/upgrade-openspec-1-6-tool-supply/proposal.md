## Why

OpenSpec 1.6.0 introduces the planning-only update workflow and changes
validation/archive behavior. ETHOS-owned fallback, CI bootstrap, and adopter
scaffold surfaces currently float the package version, so the governance tool
supply cannot be reproduced or audited as one coherent release.

## What Changes

- Pin ETHOS-owned OpenSpec fallback and CI/adopter bootstrap invocations to the
  official `@fission-ai/openspec@1.6.0` package.
- Keep explicit binary, cached official CLI, and PATH precedence unchanged.
- Add focused contracts proving the exact pin while retaining official strict
  validation as the deep governance gate.

## Capabilities

- `repository-governance`: subject=openspec-governance-tool-supply;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,release;
  facet:surface=cli,ci,scaffold,openspec,test; facet:authority=source,test,
  openspec,evidence

## Out Of Scope

- Changing the ETHOS public command plane or making OpenSpec a product runtime.
- Rewriting archived OpenSpec records, dated evidence, claims, or chronicles.
- Restarting local Codex/PyCharm processes or publishing a branch remotely.

## Impact

- `packages/ethos/src/ethos/adapters/openspec/cli.py`
- `tools/ci/scripts/bootstrap-python.sh`
- `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/ci/gitlab.yml.j2`
- focused ETHOS CLI, product, and CI-projection tests
