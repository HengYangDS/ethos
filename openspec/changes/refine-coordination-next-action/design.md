## Context

The official OpenSpec boundary is
`openspec/changes/refine-coordination-next-action`. The ETHOS product boundary
is the `ethos status --json` workspace-status read model over Git worktrees,
configured branch roles, Work Lane leases, and branch refs.

The prior read model made a true small signal visible — an unbound `work/*` ref
— but reused generic overlap/unknown-scope guidance. In a multi-agent repository
that guidance is too coarse: it implies candidate-integration remediation even
when the state is advisory-only residue.

## Design

`coordination_package` continues to emit the same JSON shape and gap taxonomy.
It now derives `next_action` from the already-reported measures:

1. required gaps;
2. unknown scope;
3. overlap;
4. missing lease;
5. foreign Work Lane presence;
6. unbound Work Lane refs;
7. clean state.

This keeps the kernel centered on existing Git and Work Lane facts. No new store,
provider surface, or lifecycle owner is introduced. The change only makes the
hidden distinction between blocking and advisory coordination state explicit.

## Alternatives

- Keep one generic next action: rejected because it blurs advisory residue with
  blocking scope uncertainty.
- Add new gap names: rejected because the existing `required_gaps`,
  `advisory_gaps`, counts, and migration recommendations already carry the
  needed facts.
- Drop `next_action`: rejected because the workspace-status schema requires a
  non-empty action string and agents benefit from precise next guidance.

## Proof Strategy

- Focused unit tests cover foreign missing-lease guidance, unbound-ref guidance,
  and coordination package selection.
- `ruff format/check` protects changed Python files.
- `ethos status --json` validates the command payload against
  `workspace-status.schema.json` and shows advisory unbound refs without overlap
  wording.
- `ethos openspec --lifecycle --json`, `ethos quality claims --json`, and an
  executed `ethos prove --execute --expect-head <head> --gate ...` bind the
  carrier, claim, and proof to the Work Lane head before land.
