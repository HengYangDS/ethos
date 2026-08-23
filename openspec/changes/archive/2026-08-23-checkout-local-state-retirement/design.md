## Context

See `proposal.md` for motivation. The accepted implementation already declares
Git-common mutable state as the only valid topology, but production code still
contained a checkout fallback, a migration command, migration guards, and policy
allowances for `.ethos/state/**`. Linked worktrees therefore did not share one
physical owner even though they shared one semantic repository.

The change is destructive by design: retaining a reader or migration facade
would preserve the competing owner and keep every consumer responsible for
precedence and drift semantics.

## Goals / Non-Goals

**Goals:**

- Make `<git-common-dir>/ethos/**` the only physical home resolved by mutable
  state and proof-artifact adapters.
- Delete every production path that observes, migrates, guards, documents, or
  permits checkout-local mutable state.
- Preserve structured fail-closed behavior at public read/admission boundaries
  when the supplied path is not a Git repository.
- Make tests create tracked `.ethos/` declaration parents explicitly instead of
  relying on an ignored runtime directory as incidental scaffold.

**Non-Goals:**

- Automatically import or delete historical residue whose equivalence has not
  been proven.
- Add a generic migration framework, compatibility schema, recovery ledger, or
  second public lifecycle command.
- Change Lease semantics, Attestation authority, or Git CAS behavior.

## Decisions

### Delete the compatibility plane instead of redirecting it

All consumers call `state_database()` or `local_state_root()`, which resolve
through Git's common directory. The checkout observer, migration guard, public
migration command, and migration-only tests are removed. A redirecting shim was
rejected because it would keep the retired vocabulary and ambiguous precedence
alive.

### Keep tracked declarations and mutable coordination physically disjoint

Tracked `.ethos/` files remain repository bindings. Ignore rules, generated
artifact policy, docs, and fixtures no longer reserve `.ethos/state/**` as a
runtime home. Proof artifacts use the same Git-common root as Lease state rather
than falling back into a non-repository path.

### Translate missing Git identity only at the public proof-gap boundary

The low-level state resolver raises `git_common_directory_unavailable`; it does
not fabricate storage. `proof_gaps()` translates that condition to the existing
public `attestation_set_repository_invalid` gap, preserving a typed fail-closed
result without reintroducing checkout storage.

### Delete migration tests and strengthen terminal topology tests

Tests whose sole purpose was the removed migration mechanism are deleted.
Remaining state, hook, proof, lifecycle, policy, and CLI tests verify the sole
Git-common owner and the absence of the retired command. Fixtures explicitly
create declaration directories they require.

## Risks / Trade-offs

- **Historical checkout-local residue remains on disk** -> Do not delete it in
  this change; require a separate hash/inventory proof before operator cleanup.
- **Older callers of `migrate-local-state` stop working** -> This is intentional
  forward-only removal; command-surface tests make the retired name
  undiscoverable and detect reintroduction.
- **Non-repository callers could see low-level resolver exceptions** -> Preserve
  the existing structured public proof gap at the boundary and test it.
- **Hidden consumers may still import retired symbols** -> Run repository-wide
  literal closure, import collection, type/static gates, focused tests, and the
  complete proof boundary before archive.
