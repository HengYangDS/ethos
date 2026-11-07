# Proposal

## Why

The RC plan needs more product code than the 75,000 line-equivalent ceiling leaves. The product
measures 73,163 of 75,000 after `layout-invariant-budget`. The converged operation catalog design
adds about 1,980 line-equivalents for its RC Changes, the `github-pin` step 2 design about 440 and
the release rehearsal design about 460 (`build/runtime/work/operation-catalog/design-draft.md` §8,
`github-pin/step2-design-draft.md` and `release-rehearsal/design-draft.md`, to be carried by the
`rc-plan` Change). DR-0010 and the owner's 2026-11-01 rule allow one 5,000 step only after the
growing owner retires proved duplication and a fresh necessity review shows the rest is needed. The
2026-11-07 expert committee asked for exactly this order before the catalog's application package
(review finding M2 B1).

## What Changes

- One owner reads the process actor: `ethos.adapters.actor` gives `process_actor()` (the stripped
  value of `ETHOS_ACTOR`, empty when undeclared), `process_issuer()` (that actor or the local process
  default `agent:local:process:ethos`) and the variable's name. The 47 direct reads in 32 modules and
  the 12 inlined defaults use it, and the four reads that did not strip the value now do.
- One check identifies hexadecimal identities: `ethos.contracts.digest` gives `is_sha256_hex` and
  `is_object_id` (a 40- or 64-character Git object ID), and the procedural copies of those checks use
  it.
- The dead `mapped_retag_receipt` is deleted; nothing has called it since it was added.
- DR-0020 records the necessity review and moves the product ceiling one step to 80,000.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The numeric limit is owned by the native source-budget declaration, and the refactor keeps
behavior, so `skip_specs: true` applies.

## Impact

- `src/ethos/adapters/actor.py`, `src/ethos/contracts/digest.py`, the modules that read the actor or
  check a digest, `src/ethos/adapters/mutation/accepted/retag.py` and their tests.
- `.config/checks/format-selection/policy.toml`, `docs/decisions/dr-0020-product-budget-step.md` and
  `docs/decisions/README.md`.
- Behavior: an actor value with surrounding whitespace is now stripped in the MCP server and in lane
  merges, as it already was everywhere else.
