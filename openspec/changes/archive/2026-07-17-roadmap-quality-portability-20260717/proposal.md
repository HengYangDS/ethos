## Why

The standalone configuration-lint runner assumes a bare `python` command,
which fails in valid Python 3 environments that expose only `python3` or an
explicit ETHOS runtime interpreter. The authoritative adopter material-scope
contract is also duplicated in the accepted OpenSpec specification, leaving
two competing texts for one product behavior.

## What Changes

- Make configuration lint resolve its Python interpreter through the bounded
  ETHOS/Python runtime override chain rather than a host-specific `python`
  alias.
- Consolidate the adopter material-change scope contract into one authoritative
  repository-governance requirement without changing OpenSpec ownership.
- Re-execute the full Python test owner script with isolated, sharded evidence
  paths to prove that the portability repair preserves the existing coverage
  floor and HEAD-bound evidence isolation.
- Add an active claim and dated Chronicle for this governed product change.

## Capabilities

- `quality`: subject=config-lint-portability; reuse=extend; change=add;
  facet:lifecycle=validation,runtime; facet:surface=ci,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence
- `repository-governance`: subject=adopter-material-scope-spec-consolidation;
  reuse=extend; change=modify; facet:lifecycle=validation,archive;
  facet:surface=docs,openspec,test,claim,evidence;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Adding a Python dependency or a new runtime installation surface.
- Relaxing any configuration, coverage, timeout, test-selection, or
  HEAD-stability quality policy.
- Extending or replacing official OpenSpec workflow schema, treating
  `scope.toml` as an official schema extension, or promoting a method package
  to governance authority.
- Mutating DDWG, foreign Work Lanes, GitLab, GitHub, hosted CI, or remote refs.

## Impact

- `tools/ci/scripts/run-config-lint.sh` and its standalone regression fixture.
- The quality and repository-governance OpenSpec specifications.
- Change, claim, Chronicle, and proof evidence surfaces only; no provider,
  adopter, or foreign Work Lane is mutated by this Change.
