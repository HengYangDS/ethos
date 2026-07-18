## Context

The material-path contract must work both for new adopters and for already
adopted repositories. A valid existing profile without `[openspec]` cannot
cover its own first declaration. Treating that condition as a general exemption
would let arbitrary material work bypass Change scope.

## Design

The scope reader recognises `profile_material_paths_bootstrap` only when all
of the following hold:

1. the profile parses and is already tracked;
2. the declaration is absent, rather than empty or malformed;
3. the request contains exactly `.ethos/profile.toml`;
4. the official OpenSpec list selects exactly one active Change; and
5. that Change directory exists.

The result carries the selected Change and profile path as provenance. It does
not declare coverage. After the profile write, the profile must declare the
Change's scope path, and the existing exact `scope.toml` bootstrap applies.

## Alternatives Rejected

- **Manual local bypass:** rejected because the cross-adopter transition
  belongs to ETHOS.
- **Treat empty declarations as bootstrap:** rejected because an explicit
  empty list must continue to fail closed.
- **Allow the profile and scope file together:** rejected because that would
  let a declaration and its claimed coverage arrive as one unverified bundle.

## Proof Strategy

Focused tests cover the single permitted profile write and reject widened,
empty, and untracked cases. Existing coverage tests continue to prove that
prewrite, plan, and prove share the ordinary scope read model. Strict OpenSpec,
lifecycle, claim, parity, and HEAD-bound proof remain separate requirements.
