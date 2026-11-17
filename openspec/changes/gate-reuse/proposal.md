# Proposal

## Why

The archived `rc-plan` design places this row in Family 4 (lines 107-109): "`gate-reuse` splits
`unit-architecture`, keys reuse on every file a gate reads and keeps one coverage floor decision
per attempt (MODIFIED `openspec/specs/quality/spec.md:120-131`); the 900-second requirement is then
met, or amended with the measurements." DR-0026 rejected a waiver of the row (line 136): "reuse is
its own sentence of R5, it is what makes a pin-only bump cheap, and without it one failed gate in a
batch of five Changes costs a full proof". The archived `rc-scope-plan` design lists the row in
0.2.0-beta.13, the committee's resolution of 2026-11-14 moved it to 0.2.0-beta.14, and DR-0029
fixes no row to a batch. On 2026-11-17 the release lead moved its first slice back into
0.2.0-beta.13, and the owner decided its shape the same day: the first release computes and
records each gate's input key and compares verdicts, and no proof skips a gate.

The measures of 2026-11-17 behind that move:

- The 34 gates of the lane's last full proof took 2,315.5 seconds together: `unit-architecture`
  1,264.6 and `local-install-smoke` 645.3, and no other gate over 55.
- Of the 264 commits on the accepted branch since `v0.2.0-beta.10`, 211 change only Markdown or
  OpenSpec documents (`git log --format=%H v0.2.0-beta.10..67b0f4aac`, each commit's paths tested
  against `\.md$|^openspec/|\.openspec\.yaml$`). Each owed every gate.
- One slot serves every repository of the host. Three sessions measured waits of 47 to 72 minutes
  for runs of 1 to 20 minutes.

A reused result changes what a proof asserts, and a wrong reuse admits a wrong proof, one of the
three defect classes that DR-0015 lets no beta carry. The study of this Change measured how near
that is. A gate declares `asset_classes`, and no code reads that field as a list of paths. The
study wrote a first statement of inputs for each of the 21 gates whose reads are narrower than the
tree, then traced what each gate's process opened: 11 of the 21 statements omitted a file. On a
tree that differed in one unrelated document, 16 gates kept their key and all 16 gave the same
verdict, 5 of them under an incomplete statement. So an agreeing verdict does not show that a key
is complete, and the record this Change keeps has to show more than verdicts.

The same study bounds what the row can give. Eleven gates read state that no tree digest holds,
and this design never reuses them. A bump of the product's own pin changes the judge, so no sound
key makes it cheap. The time of a proof is in the tests and in the install smoke; the gates that
can arm first hold almost none of it.

## What Changes

- Each gate of an executed exact-source proof run gets an input key: a digest of the gate's
  identity, the committed paths its statement selects, and named inputs outside the tree.
- The product states what each of its own providers reads, in one packaged table by provider ID.
  A gate that runs a declared command, and a provider without a statement, is keyed by every
  committed path. A provider that reads outside the committed tree is marked open.
- The named inputs are the running product, the interpreter and platform, Git's version, Git's
  attribute classification of the committed paths and the names of the entries that Git ignores.
- Each run writes one record of its keys and verdicts in the repository's Git-common store.
- A gate whose key an earlier decided result carries still runs. The run compares the two
  verdicts, records each comparison, and its result counts the comparisons by state and names
  each difference. A difference is a note.
- The record also names each committed file that a provider's own process opened outside its
  statement, and the count of effective lines of the Git directory's local attributes file.
- No gate is skipped, by any route, and no result of the record enters a proof.

Not breaking. No gate declaration, policy digest, Attestation, proof artifact, verdict or required
gap changes. The `prove` result gains fields.

Named remainders, each its own Change:

- `gate-reuse-arming` (read at the cut of 0.2.0-beta.14): a gate is reused once its own record
  meets the threshold that the owner sets; the proof carries each reused result with the tree it
  ran on; the accepted scenarios on the dependency audit and on hosted preparation each gain one
  line, and the 900-second requirement is amended with the cold and the reused measure.
- `test-gate-split` (read at the cut of 0.2.0-beta.14): `unit-architecture` becomes a part that
  reads the whole repository and a part that reads code, with one coverage floor decision for an
  attempt; it modifies the scenario "Change proof executes the complete test surface".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ADDED requirement `Gate results carry an input key before any result is reused`.

## Impact

New: `src/ethos/adapters/gates/input_key.py`, `src/ethos/contracts/gate-inputs.toml` and their
tests. Changed: `src/ethos/application/proof/operation.py` and `host.py`, one statement of
`src/ethos/adapters/gates/runner.py`, the record kinds of
`src/ethos/adapters/store/retention/kinds.py` with their batch in `apply.py`,
`docs/architecture/gate-runner.md`, `docs/architecture/local-state.md`,
`docs/reference/command-plane.md` and `CHANGELOG.md`.

Size, in line-equivalents, measured on the built slice: product +369.5, tests +449.3, tools none.
A proof gains under 0.4 seconds, measured on the spike for 34 gates and 1,005 earlier records.
