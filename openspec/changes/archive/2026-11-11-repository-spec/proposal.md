# Proposal

## Why

Fixture repositories are built by several separate builders in test support: `init_git_repo`, the
adopted candidate and the prepared Work Lane, and their own copies in the signature and proof
fixtures. Each spells part of the same stage sequence, so a change to the paradigm's base files or
to one stage is edited in several places. Phase T item 1 gives fixture construction one authority;
its step 1, one fixture signer, landed in `fixture-signer-owner`.

## What Changes

- `RepositorySpec`, a frozen dataclass in `tests/support/governed_repository.py`, declares what one
  fixture repository holds, and `build(spec, repo)` creates its stages in one order from the moved
  stage code. `BASE_FILES` holds the base commit's content.
- `init_git_repo`, `start_adopted_candidate` and `prepared_work_lane` keep their names as
  one-expression presets over `build`, so their callers do not change; their stage bodies are
  deleted.
- `signature_repository` and `proof_repository` build through a spec plus their own scenario lines.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Test support only; product behavior is unchanged, so `skip_specs: true` applies.

## Impact

`tests/support/governed_repository.py`, `tests/support/proof.py` and `tests/support/signature.py`.
The enforced `python_tests` figure does not grow.
