# Proposal

## Why

OpenSpec 2.0.0, published on 2026-11-11T22:41:44Z, is the newest stable release of ETHOS's intent
carrier. On 2026-11-12 the owner asked for it in ETHOS and every governed repository at once,
before the 24-hour release age, and allowed breaking changes.

2.0 keeps OpenSpec's workflows. It installs OpenSpec's skills once, in `.agents/skills/`, and
records which of them are its own in `.agents/skills/.openspec-target`; it removes the `/opsx:*`
commands; and `openspec update` removes the files older releases generated. ETHOS's skill portfolio
reports every `SKILL.md` package under the Skills root that no activation record routes as
`skill_package_unregistered`, so a repository that sets up OpenSpec's tools under 2.0 would block.

## What Changes

- The embedded OpenSpec CLI moves from 1.17.0 to 2.0.0 in `package.json` and the npm lock. Its
  dependency ranges are those of 1.17.0, and the internal modules ETHOS loads are unchanged except
  `utils/task-progress.js`, which now joins a wrapped task's lines into its description while its
  task count stays the same.
- The skill portfolio routes to OpenSpec each package that OpenSpec's own record names as its own,
  read through OpenSpec's module by the existing configuration bridge, so such a package needs no
  activation record. A package the record keeps as the user's, and any package without the
  record, still needs one or reports `skill_package_unregistered`.
- The CI supply image is rebuilt from the moved lock and bound.
- The owner's exception is recorded with its scope and exit: OpenSpec 2.0.0 only, every other
  package keeps the 24-hour rule, and the exception lapses at 2026-11-12T22:41:44Z.
- **Breaking:** ETHOS reads OpenSpec's skills only as 2.0 lays them out. A repository that keeps
  skill or command copies from an older OpenSpec release runs `openspec update` once.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `assistant-projections`: MODIFIED `Skill portfolio validation`, with a scenario for the packages
  that OpenSpec's record owns.

## Impact

- `package.json`, `package-lock.json`, the OpenSpec configuration bridge, the skill portfolio and
  their tests; the CI supply image digest in `.config/ci/pipeline.cue`; the Unreleased entry.
- Size, an estimate: product +40 and tests +60 line-equivalents.
- Governed repositories take OpenSpec 2.0 with their next ETHOS pin bump, each in its own Change by
  its owner. Three also declare their own `@fission-ai/openspec` (aigw-cli, openai-responses-proxy
  and architecture-publisher), and one keeps 1.x skill copies that `openspec update` migrates
  (alphasim-dmgr-fix-b3).
