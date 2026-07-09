## Context

The official OpenSpec boundary remains the OpenSpec workspace, official CLI
validation, and accepted spec delta format. The ETHOS product boundary adds
repo-local lifecycle checks, capability profiles, claim binding, evidence refs,
and archive/closeout guards after official validation.

The reference adopter comparison contributed practical local GitLab emulator, closeout,
local-state, Pixi/Nox/Pants, Backlog, package/release, and Superpowers boundary
lessons. The alternate mechanism corpus comparison contributed dual GitHub/GitLab CI templates,
local `act` and `gitlab-ci-local` emulators, template consistency, actionlint,
format-selection policy, LikeC4/C4 projection, MCP smoke, runbook registry,
Docker-first runtime boundaries, and broad policy gates.

## Design

This change lands planning and contract surfaces only. It deliberately records
mechanisms as adoption targets instead of implementing all tooling at once.

The forge provider contract defines GitHub and GitLab as equivalent hosted
providers over one Git-native ETHOS repository subject. Provider templates,
tracked hosted YAML, local emulators, and hosted observations are separate
projection layers. Local emulators must label evidence as local provider
emulation and must not claim hosted success.

The roadmap contains a horizontal mechanism matrix across reference adopter, alternate mechanism corpus, and
ETHOS. The matrix distinguishes:

- product-kernel mechanisms ETHOS already owns;
- adopter mechanisms ETHOS should absorb as gates, evidence classes, or
  projections;
- environment, task, provider, architecture, release, and agent mechanisms that
  must remain adapter-only;
- domain runtime mechanisms that must not enter ETHOS unless ETHOS is governing
  that repository as an adopter.

The roadmap sorts adoption work into:

- P0: provider parity, local emulation, actionlint, official-compatible
  OpenSpec customization, Superpowers boundary;
- P1: quality/format/security/C4 and evidence operations;
- P2: runbook, MCP smoke, and release supply-chain gates;
- optional adapters: Nox, Pixi, Pants, Backlog, Superpowers.

`system/tools.toml` is extended with active and planned tools so the roadmap is
visible to machine checks without activating unimplemented gates. A planned
tool remains planned until it has catalog entry, config owner, reusable gate,
CI/hook projection, and tests/proof.

## Alternatives

- Copy adopter Pixi/Nox/Pants directly into ETHOS: rejected because it creates a
  second command plane and binds ETHOS to one adopter's local runtime.
- Copy alternate mechanism corpus `policy run`: rejected because it duplicates ETHOS proof and
  quality registry semantics.
- Treat GitLab as primary and GitHub as secondary: rejected because the user
  requires GitHub and GitLab as mirrored repository carriers.
- Use only OpenSpec defaults: rejected because official validation is necessary
  but not sufficient for ETHOS claim/evidence/capability lifecycle checks.
- Make Superpowers mandatory: rejected because ETHOS needs the discipline, not
  that specific plugin as substrate.

## Proof Strategy

This planning change is proved by static repository checks:

- OpenSpec lifecycle validates the active carrier and claim binding.
- Schema checks validate command/schema contracts and capability profiles.
- Markdown/config lint validates new docs and tool catalog syntax.
- `ethos plan --changed --json` shows docs/OpenSpec/system/claim scope.
- `ethos prove --execute --expect-head <head> --json` binds the planning change
  to the repository proof kernel before candidate landing.

Implementation work packages will require their own follow-up changes and
executed proof before any planned gate becomes active.
