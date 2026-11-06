# Design

## Context

See [proposal.md](proposal.md). The design record is
`build/runtime/work/operator-verbs/next-wire-shape-draft.md`. It holds draft 1, its independent
review, fbee0c's review and the converging decision of 2026-11-07 05:2x.

## Goals / Non-Goals

Goals:

- One final `next` vocabulary inside schema 3 before beta.6.
- A truthful derivation from the argv until `command-forms` declares forms.

Non-goals:

- Declared forms, `when` selection, the entry check, per-form exit and the two-way gate
  (`command-forms`).
- Widening hook admission.
- Moving `hook install`'s cleanup.
- Typed producers and new bindings.

## Decisions

- **No `text` field.** `next_action` stays the text, so a second carrier would fail PDC question 2.
- **The table owns the derivation.** It sits in `contracts/admission.py` beside
  `ethos_step_effects`. `ethos_command_path` keeps up to three words. A row (a path and a token set)
  matches when its path prefixes the argv's words and every token is present. Tokens are read by
  presence, as hook admission reads them, so `--apply=false` over-reports.
- **Authorization is the strongest token.** In order: `--authorization <file>` is `attestation`,
  then `--confirm-irreversible`, `--authorize` and `--apply` give their namesakes. A decision and an
  opaque step are `human`. The kinds advise, and admission at effect time stays the authority.
- **Effects.** `host run` and `mcp` are `execute` and `opaque`, because their argv cannot bound
  what they run. `hook install` and `land --closeout` write locally without a token. `host-write`
  covers `hook install`, plus `hook retire-supply`, `lane start`, `lane candidate` and
  `adopt --select-runtime` with `--apply`.
- **Destructive rows.** These shapes select a deletion:
  - `lane retire abandon` and `recover` with a receipt;
  - `lane retire superseded`, `landed` and `absorbed-ref`;
  - `lane housekeeping`;
  - `lane handoff revoke-source`;
  - `lane candidate --refresh-from-accepted --confirm-irreversible`;
  - `publish --retire`;
  - `attestation release`;
  - `adopt --exit`;
  - `land --retag`;
  - `hook retire-supply`;
  - `hook install --reset-state`.

  Each row needs the tokens that its operation requires before it deletes anything. An opaque step
  is destructive too. Plain `hook install`, `lane start --apply` and `lane candidate --apply` are
  not destructive: their cleanup runs under a liveness check, and they report it.

- **A decision carries its command.** When the text of an `await-user` result is one exact ETHOS
  argv, `next` is a `decision` with that argv, its effects, `destructive` and binding, and
  authorization `human`. A kit runs only `kind == "command"`, so it stays safe.
- **`--retire` must match the receipt.** A replayed effect whose retirement differs from `--retire`
  blocks before any effect. The dry run's apply continuation puts `--retire` after `publish` when it
  retires.
- **The candidate refresh confirms a drop.** When the old candidate head is not an ancestor of the
  accepted head, `--apply` refuses with `candidate_refresh_unaccepted_commits` unless
  `--confirm-irreversible` is given. The preview's and the refusal's next action carry the flag,
  for a person to approve.

## Risks / Trade-offs

- **Older payloads.** A payload that carries `embedded` no longer validates in `from_payload`. No
  release carries one. `expand_result` returns the producer's mapping without validating it, so
  cross-build detail stays readable to any reader that does not validate it.
- **Retag publication.** A `publish` that moves a peer tag to a re-created tag object cannot be
  told from its argv. `land --retag` is destructive, and the peer-side replacement is a stated limit
  until declared forms select by bound values.
- **Moved repositories.** Install's shared-store cleanup treats a missing consumer path as
  released (`host_retention.py:84-85`), so a moved or unmounted repository can lose its pinned
  runtime. Register row 28 records this, and `command-forms` changes it when `hook retire-supply`
  takes over the cleanup.
