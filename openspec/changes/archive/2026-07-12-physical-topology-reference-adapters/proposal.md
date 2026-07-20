## Why

The root-level `reference_adapters/` directory is an unbounded implementation
bucket. It is neither a buildable product package nor an explicit ecosystem
integration surface, so its location conceals ownership, lifecycle, and
installation boundaries. The independent-verification reference implementation
is optional and provider-local; it must not appear as a root-level product
subsystem or an adopter prerequisite.

## What Changes

- Move the one-shot independent-identity reference verifier from
  `reference_adapters/` into the declared `extensions/` boundary.
- Create an `independent-verification` extension manifest, local README, and
  colocated tests; remove the root directory rather than leaving a forwarding
  shell.
- Update canonical architecture and adoption references to the new physical
  owner without changing verifier semantics, policy modes, or public commands.
- Record the topology correction as a separate, HEAD-bound claim and
  Chronicle entry. Historical assurance evidence remains historical rather
  than being rewritten to assert a different past path.

## Capabilities

- `adapters`: subject=optional-independent-verification-reference; reuse=extend; change=rename; facet:lifecycle=validation; facet:surface=docs; facet:authority=source

## Out Of Scope

- Changing the optional/default-off independent-verification policy or making
  `yheng-agent-ethos` a prerequisite for any adopter.
- Changing the reference verifier's proof, sandbox, signing, account, or
  provider configuration behavior.
- Editing, landing, retiring, or cleaning the foreign
  `work/independent-evidence-verifier-20260711` Work Lane.
- Adding a dynamic extension loader, compatibility import, symbolic link, or
  root-level `reference_adapters/` replacement.
