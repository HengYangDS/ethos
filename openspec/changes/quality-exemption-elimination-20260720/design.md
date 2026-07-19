## Context

The active Python lint gate selects broad Ruff rules but then hides part of
that selected set through global ignores, path-based ignores, a ratchet file,
and in-source `noqa` directives. The current proof therefore demonstrates
non-growth for some findings, not their absence.

## Goals / Non-Goals

**Goals:**

- Make every currently selected Ruff rule directly enforceable for every tracked
  Python asset.
- Delete rather than neutralize the ratchet and exception-carrier shapes.
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
2. **Delete all exception carriers atomically.** An empty ratchet, zero-valued
   ignore, or allowlist would preserve the wrong semantic shape. The removal
   includes global ignores, per-file ignores, the ratchet file, the ratchet
   runner, and references in gates, tool registry, docs, and tests.
3. **Refactor findings rather than suppress them.** Tests, tools, agent scripts,
   and packages use the same selected rules. Where a framework needs runtime
   annotations or a test needs an assertion, code structure or rule selection
   must express the legitimate boundary without path-level exemption.
4. **Make residue executable.** Contract tests scan active tracked Python
   carriers for forbidden Ruff policy/suppression forms and prove the owner
   script does not invoke a retired runner.
5. **Type checks enter through the canonical runtime bootstrap.** The type
   adapter invokes the checkout-local runtime wrapper rather than directly
   executing a possibly unmaterialized `build/runtime/venv/bin/python`. This
   keeps the executable environment, source tree, lockfile, and type search
   paths bound to one checkout. The wrapper also clears an inherited
   `VIRTUAL_ENV`, so a parent `.venv` cannot leak a false mismatch warning into
   a clean type-gate result.

## Risks / Trade-offs

- **Large finding inventory** → resolve in deterministic waves, always keeping
  the exact full-rule command as the acceptance oracle.
- **Framework annotations trigger typing/import rules** → use ordinary runtime
  imports or a declared architectural rule boundary, never `noqa`.
- **Temporary broad edit scope** → preserve candidate integration discipline;
  land only a head-bound, fully proven change.
