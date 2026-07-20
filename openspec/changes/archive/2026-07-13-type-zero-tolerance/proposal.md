## Why

The current type policy admits a frozen diagnostic allowance for
`packages/ethos`. That exception is incompatible with ETHOS's zero-tolerance
quality law. More seriously, the gate currently converts an unavailable `ty`
runtime into zero diagnostics, so a failed tool invocation can be reported as a
passing proof gate.

## What Changes

- Make `ethos quality types` fail closed when `ty` cannot run or its result
  cannot be determined.
- Eliminate the existing `packages/ethos` type debt through behavioral tests
  and minimal type-safe corrections.
- Remove the type ratchet and require zero diagnostics for every declared
  package.
- Record the policy, gate, CLI, CI projection, OpenSpec, Claim, and Chronicle
  contract as one governed change.

## Capabilities

- `quality`: subject=python-type-zero-tolerance; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=quality,cli,ci,test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Changing the selected type checker, adding suppressions, baselines,
  per-file ignores, `noqa`, compatibility shims, or a second quality command.
- Relaxing unrelated Ruff, coverage, documentation, package-layout, or proof
  requirements.
