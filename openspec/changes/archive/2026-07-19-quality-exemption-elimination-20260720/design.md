## Context

The active Python lint gate selects broad Ruff rules but then hides part of
that selected set through global ignores, path-based ignores, a ratchet file,
and in-source `noqa` directives. The current proof therefore demonstrates
non-growth for some findings, not their absence.

## Goals / Non-Goals

**Goals:**

- Remove the bounded `DTZ011` carrier with an explicit UTC calendar boundary.
- Bind type checks to the current checkout's runtime and suppress only ambient
  environment noise, not diagnostics.
- Preserve one policy owner and one owner-script path across local, hook, CI,
  and proof projections.

**Non-Goals:**

- Claim that unrelated historical source-budget or release-state work is closed.
- Alter foreign Work Lanes or reuse their unmerged changes as authority.
- Add a second linter, quality database, or compatibility mode.

## Decisions

1. **Ruff remains the only Python lint/format executor.** Its existing native
   policy file remains the rule owner; the owner script retains only file-set
   discovery and invocation.
2. **Remove one exact carrier at a time.** `DTZ011` is deleted only after the
   UTC clock and a whole-corpus probe prove its absence. Remaining carrier
   classes stay visible as unresolved work rather than being implied complete.
3. **Refactor findings rather than suppress them.** The terminal architecture
   remains direct enforcement; each later wave must make its rule applicable
   without adding a new waiver or compatibility surface.
4. **Type checks enter through the canonical runtime bootstrap.** The type
   adapter invokes the checkout-local runtime wrapper rather than directly
   executing a possibly unmaterialized `build/runtime/venv/bin/python`. This
   keeps the executable environment, source tree, lockfile, and type search
   paths bound to one checkout. The wrapper also clears an inherited
   `VIRTUAL_ENV`, so a parent `.venv` cannot leak a false mismatch warning into
   a clean type-gate result.

## Risks / Trade-offs

- **Large finding inventory** → resolve in deterministic waves under a later
  terminal change, always keeping the exact full-rule command as the oracle.
- **Framework annotations trigger typing/import rules** → use ordinary runtime
  imports or a declared architectural rule boundary, never `noqa`.
- **Temporary broad edit scope** → preserve candidate integration discipline;
  land only a head-bound, fully proven change.
