## Context

Accepted `dev`, `candidate/dev`, and `main` are aligned at `3b04f2dfa3638099753bb484bf4f4e1cea19ceaa`.
The target-scoped lease observation repair is accepted and its carrier retired.
Two fresh direct-retire decisions then re-observed the exact clean ownerless
sources. Both effects stopped only at accepted ancestry and produced no package,
receipt, reservation, fence, ref, worktree, lease, or accepted-ref mutation.

## Goals / Non-Goals

**Goals:**

- Bind each no-effect result and exact target without changing prior decisions.
- Authorize the current native recoverable effect for only those two targets.
- Keep valid-owner descendants observe-only and avoid any feature acceptance
  claim.
- Require serial package, bundle, manifest, receipt, ref, and worktree checks.

**Non-Goals:**

- No product code, parser, schema, test, compatibility alias, source replay,
  package clear, valid-owner takeover, remote operation, or broad housekeeping.

## Decisions

1. **No-effect decisions remain immutable.** Decisions `lane-decision:4838b832-ce13-4392-913d-99a6ebc3cbbd` and
   `lane-decision:6d1a4a1d-4b3e-4cd1-9d2e-303e8688d45e` remain truthful `retire` records. New dispositions require
   new decision IDs and fresh observations.

2. **One accepted Chronicle per exact target.** Each `preserve-retire` Chronicle
   carries one literal branch selector, exact target HEAD, exact event, and its
   own Claim. No aggregate carrier can substitute for effect admission.

3. **Preservation is a transient effect bridge.** The sources are clean, so the
   new package's tracked and index patches must be empty. The repository bundle
   still binds the complete exact target history before ref and worktree removal.

4. **Retained recovery material is not generic residue.** Completion receipts,
   manifests, bundles, and packages remain governed records. Clearing them
   requires a later accepted exact decision ID and manifest SHA-256; this carrier
   does not authorize clear.

5. **Effects are serial and fail closed.** Complete decision, apply, inventory,
   package, bundle, receipt, ref, and worktree verification for the first target
   before observing the second. Any drift preserves the current target and all
   non-target state.

6. **Success is an exact native postcondition set.** Record the new decision
   current-record path and SHA-256, require `preserved_and_retired`, retained
   inventory state, exact format-v2 package files and cross-digests, empty clean
   patches, no `untracked.tar`, absent ref/registration/path, no reservation,
   fence, or receipt sidecar, and unchanged accepted plus non-target refs.

## Risks / Trade-offs

- **Target or ownership drift** -> Stop and leave the source intact.
- **Chronicle or decision drift** -> Reject before package or Git effects.
- **Package verification fails** -> Retain source and governed recovery material
  according to the native receipt state; do not hand-clean.
- **A valid-owner descendant is confused with the source** -> The exact branch
  and HEAD selectors make all descendant mutation unauthorized.
- **A retained package is mistaken for junk** -> Keep it outside final disposable
  filesystem housekeeping.

## Migration Plan

1. Add the two target-bound authorities and the OpenSpec delta.
2. Validate Claims and OpenSpec, archive officially, refresh parity, execute the
   final HEAD-bound proof, land, accepted-close, and retire this carrier.
3. Create a fresh preserve-retire decision for the first exact target, apply it,
   and record all native postconditions.
4. Repeat independently for the second target.
5. Leave packages retained and continue only with the explicitly bounded local
   orphan/cache housekeeping already selected by the user.

Rollback before accepted closeout is to discard only this owned carrier. After
acceptance, a blocked native effect leaves the target and immutable records in
place; raw Git or SQLite mutation is never a rollback path.

## Open Questions

None. Mutable target, lease, Claim, registration, package, receipt, and accepted
facts remain execution-time predicates.
