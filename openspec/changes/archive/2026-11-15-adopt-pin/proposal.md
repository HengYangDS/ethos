# Proposal

## Why

No ETHOS code writes the pin that selects a release. `ethos adopt` plans a profile and an OpenSpec
configuration and nothing else, the product source holds no pin writer, and the only pin artifact is
a per-release declaration file whose table an adopter pastes by hand. Every release therefore costs
every governed repository a hand-pasted table inside a Change of its own: eight repositories landed
39 such Changes between 2026-10-25 and 2026-11-12.

This Change is row C3 of the release-candidate plan
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, Decision 2, Family 7); item 3 of that
design's Appendix C.2 is its done condition. Step 2 of the plan's `github-pin` gate requires it, and
so does R10, whose one install line must name an attested channel (Decision 5, item 6). It follows
`github-pin` (C1), whose pin module it calls, and it ships in 0.2.0-beta.11 under the release
candidate scope that the owner approved on 2026-11-14.

## What Changes

- The adoption plan of a release build gains one step for `.config/mise/config.toml`: the release's
  bare entry under `[tools]` and `locked_verify_provenance = true` under `[settings]`. The step
  shows its text diff, only adds lines, and the plan digest binds it.
- A Mise configuration that names another version or form of the pin, holds an `http:ethos` table,
  sets the provenance setting to another value or does not parse is an `adoption_conflict`.
- A development build plans no pin and says so; the formation of a new repository plans none.
- After an apply that wrote the pin the next action is `mise lock`.
- `ethos adopt --exit` names the bare pin in its preview and removes that key alone.
- **BREAKING** for adopters: adoption now writes a key of a second file, and a repository that
  still installs ETHOS through an `http:ethos` table, or pins another version, gets an
  `adoption_conflict` from a release build until its Mise configuration holds that release's bare
  entry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: MODIFIED requirement `Minimal Adoption Binding`.
- `runtime-activation`: MODIFIED requirements `A repository exit is previewed before any effect` and
  `A previewed exit is applied in a fenced order`.
- `command-plane`: MODIFIED requirement `Adoption continuation preserves request meaning`.

## Impact

`src/ethos/adapters/repo/adoption.py`, `src/ethos/application/adoption.py`, the exit plan and apply
under `src/ethos/adapters/repo/hook/`, two helpers of `src/ethos/repository/paradigm/repair.py` that
become public, the brownfield and MCP package acceptance under `tools/ci/delivery/acceptance/`,
their unit tests, `docs/architecture/adoption-profiles.md`, `CHANGELOG.md` and the three specs
through this Change's deltas.
