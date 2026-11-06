# Proposal

## Why

DDWG, wib and seven other governed repositories track their GitLab peer's web address in
`.ethos/release.toml` (`forge_repository`), and ETHOS requires two local command fields
(`local_verification_command`, `local_installation_command`) that nothing executes. The owner ruled
on 2026-11-06 that no peer identity stays in tracked content: no host, port, namespace, project path
or project ID. The forge web repository is local connection metadata, and the fallback evidence is
the proof Attestation that publication already binds.

`peer-neutral-artifacts` draft 1 was withdrawn after review and split. This is its first part, which
DDWG and wib need. Drafts 2 to 4 were reviewed by fbee0c (adopter owner) and an independent reviewer
(`build/runtime/work/peer-neutral-artifacts/peer-resolution-draft*.md`).

## What Changes

- One adapter resolver replaces `_forge_url`. It reads the local `remote.<name>.forgeRepository`
  key first, then an `http` or `https` remote without userinfo. Otherwise it reports a gap whose
  next action is a value-free `git config --local` command.
- The tracked `forge_repository` and the two local command fields retire. The loader refuses them,
  a paradigm obligation reports them, and a pure `lane repair-paradigm` repair removes them without
  echoing any value.
- The publication fallback becomes a projection of publish's proof admission, and `local_ci`
  retires.
- A rollback across a repaired declaration refuses at hook activation until the predecessor's
  declaration is restored in a lane.
- ETHOS repairs its own `release.toml`. The cutover order is stated for ETHOS and for adopters.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: forge review observation resolves peer web coordinates locally.
- `repository-governance`: the publication fallback projects proof admission.
- `repository-paradigm`: retired publication fields have an obligation and a pure repair.
- `runtime-activation`: a rollback across a repaired declaration refuses until restored.

## Impact

- `src/ethos/adapters/mutation/publication/forge.py` (new) and `retirement.py`,
  `src/ethos/repository/release/publication.py`, `src/ethos/domain/publication/` (fallback,
  inspection), `src/ethos/repository/paradigm/repair.py`,
  `src/ethos/repository/policy/references/declarations.py`, `src/ethos/adapters/mutation/proof.py`,
  `src/ethos/adapters/repo/hook/activation.py`, `.ethos/release.toml`.
- `tools/ci/local_ci.py` and the `local_ci` session retire. `tools/ci/delivery/acceptance/` keeps
  the old fields only in its retained predecessor fixture.
- Adopters: each binds the release, applies the repair, proves, pushes its proposal from the lane,
  lands, then publishes. DDWG and wib are owned by fbee0c.
