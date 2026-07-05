## Context

Official OpenSpec owns the change carrier and validation boundary. ETHOS owns
the repository-local product boundary: Tao, docs, specs, tests, and promoted
contracts.

The root philosophy is:

> 道隐无名，几动于微，法乎自然；
> 生一启元，分二判势，孕三冲和；
> 万象昭幽，度协畛域，枢得环中；
> 物遂其性，化育无穷，是谓玄德。

## Design

The change treats the philosophy as a generative kernel:

1. **Hidden root, small signal, natural law.** ETHOS keeps authority deeper than
   any tool, vendor, model, UI, or host. Small drift is first-class evidence.
2. **One, two, three.** ETHOS starts from one kernel, separates necessary
   boundaries, and reconciles through explicit bindings.
3. **Visibility, measure, center.** ETHOS makes hidden repository state visible,
   measures only inside the right domain, and keeps the kernel chain as pivot.
4. **Let each thing fulfill its nature.** ETHOS absorbs tools and frameworks by
   contract and projection while preserving their native boundaries.

Ownership remains in `docs/governance/product-design-contract.md`,
`docs/concepts/kernel-model.md`, `system/tao.md`, and the `ethos-core` spec.
The Product Design Contract stays the product-level explanation. `system/tao.md`
becomes the short human-authored axiom carrier. The kernel model explains how
kernel objects derive from the root philosophy.

## Alternatives

Only keeping the poem in the product design contract is insufficient because it
can be read as branding. Creating a separate philosophy subsystem would be
worse: it would create a second authority center. Extending Tao and kernel docs
keeps the constraint close to the existing root.

## Proof Strategy

- Static architecture tests assert the Tao and kernel docs include the compact
  philosophy and operational derivations.
- Existing product design tests continue to assert provider neutrality and
  operational anchors.
- `openspec validate --all --strict --json` checks promoted specs.
- `ethos openspec --lifecycle --json` checks no active lifecycle gaps remain.
- `uv run --group dev pytest -q` verifies the repository suite in the managed
  project environment.
