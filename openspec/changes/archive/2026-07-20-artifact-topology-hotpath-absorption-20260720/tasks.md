## 1. Source and semantic record

- [x] 1.1 Bind the exact source ref/head and the observed staged parity patch.
- [x] 1.2 Identify the historical useful behavior and the newer accepted
  topology/CEL contracts that must be tested instead of tree-compared.

## 2. Authority carrier

- [x] 2.1 Add the target-specific Claim, Chronicle, plan, and OpenSpec delta.
- [x] 2.2 Require one source-only native `lane_resolution/preserve-retire` and
  separate any later recovery-package clear authority.

## 3. Validation and lifecycle

- [x] 3.1 Run strict OpenSpec, claims, focused topology/CEL tests, and current
  source-observation checks.
- [x] 3.2 Refresh generic parity and execute HEAD-bound proof on the archived
  carrier.
- [x] 3.3 Bind the post-closeout native `preserve-retire` and separate
  manifest-bound clear sequence without treating either as complete here.

## Post-archive transition boundary

This archive does not itself land, close out, retire the source, or clear a
recovery package.  After this carrier is accepted, the native sequence is:

1. land the exact proven carrier and complete accepted-root local closeout;
2. re-observe and apply the one-source `lane_resolution/preserve-retire`;
3. preserve the resulting receipt/package until a separate accepted
   `lane_resolution/clear-preservation` decision binds that exact manifest; and
4. retire this carrier only after its accepted source no longer needs the
   linked worktree.
