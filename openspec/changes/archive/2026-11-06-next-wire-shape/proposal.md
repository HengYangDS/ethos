# Proposal

## Why

Result schema 3 is on dev but in no release, and beta.6 will ship it first. So `next` takes its
final vocabulary now, and every agent kit moves once. Today `next` cannot say what agents most need
before they run a step:

- whether it deletes something;
- which authority it carries;
- whether it can run anything at all.

In detail:

- `authorization` is `embedded` for any write, so a peer-ref deletion and a push look the same.
- `hook install` reports only an evidence write, though it writes Git-common activation and the
  host store. `host run` reports a local write, though it runs any child.
- A decision drops its argv. So the retirement previews hand back their destructive apply as a
  `decision` that says nothing about the deletion.
- A retirement receipt applies with the same argv as a publication receipt.
- `lane candidate --refresh-from-accepted --apply` can drop candidate commits that accepted does
  not contain, and nothing refuses it.

## What Changes

- `NextStep` gains `form`, which stays empty until declared forms select one, and `destructive`.
  `effects` gains `host-write` and `opaque`. Authorization names the argv's strongest authority
  token (`attestation`, `confirm-irreversible`, `authorize` or `apply`), else `none`. It is
  `human` for a decision or an opaque step. `embedded` is gone.
- `destructive` says whether the argv selects the deletion of something it does not recreate.
  Cleanup that another operation performs under a liveness check is not counted, and that operation
  reports it in its result.
- A table in `contracts/admission.py` derives these values until `command-forms` declares forms.
- A decision whose text is one exact ETHOS argv carries its argv, effects, `destructive` and
  binding, with authorization `human`.
- A retirement receipt applies only with `--retire`. A mismatch either way refuses with
  `remote_publication_receipt_retire_mismatch`, and the dry run's continuation carries the flag.
- A candidate refresh whose old head accepted does not contain refuses with
  `candidate_refresh_unaccepted_commits` unless `--confirm-irreversible` is given.
- Regressions pin that `prove --host --execute --full --json` exits 1 on `block` and on `unknown`,
  and that hook admission's readers do not widen.
- `CHANGELOG.md` gets the whole schema-3 entry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: the `next` vocabulary, decisions with their argv, retirement receipts and the
  candidate refresh refusal.
- `kernel`: a carried `next` must be well formed in this vocabulary.

## Impact

- Breaking for agent kits. A payload whose carried `next` names `embedded` no longer validates. No
  release carries one, because schema 3 is unreleased. Kits that read `next.kind`, `next.argv` and
  `next.binding` keep working.
- Breaking for scripts that apply a retirement receipt without `--retire`. The producer's own
  continuation carries it.
