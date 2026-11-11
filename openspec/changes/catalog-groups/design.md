# Design

Code is cited by repository-relative path. `S` is `src/ethos/surface/cli/`, `K` is
`src/ethos/contracts/operations/` and `A` is `src/ethos/application/`. LE are effective lines
(`ethos.measure.effective_code_lines_for_source`; per-file ceiling 500). The reviewed history is the
scratch drafts 1 to 4 under `build/runtime/work/catalog-root/catalog-groups/`; this document is the
design.

## Context

- The root catalog (`K/catalog.py`) declares 29 operations; `S/root/catalog.py` renders them and
  `A/catalog.py` selects and runs one implementation each.
- 38 leaves remain outside it: `lane` 26, `hook` 7, `attestation` 3, `host run` 1, and the transport
  launcher `mcp`. Their modules total about 1,800 LE.
- `src/ethos/contracts/admission.py` classifies group argv by token rows, 12 of them destructive,
  and `src/ethos/contracts/next_step.py` falls back to them for any non-root argv.
- 54 surface `ignore_imports` rows exist; 52 serve these leaves, 2 belong to
  `surface/mcp/server.py`.
- The Cyclopts loop spike shows paths of up to three words, positionals, variadics, `-` values and
  `--` passthrough bind through one generated signature.

## Goals / Non-Goals

Goals:

- Each group leaf is one catalog entry with a kernel and an application half; one adapter renders
  every command, `<path> --help` and the group help.
- `next` reads every ETHOS argv through the catalog; an unselected argv is `opaque`, destructive and
  `human`.
- 52 import rows and 12 destructive rows retire; no valid request changes its result or exit.

Non-Goals:

- Lane semantics and new verbs (A9), the `hook install` self-loop (A8), the actor reader (A7), typed
  steps beyond the golden path (A13), deadlines and handles (A10), per-entry MCP tools (A16),
  provider IDs (A14), group SDK functions, the `domain` import rows (0.3.0).
- Fencing the root-write implementations `A/adoption.py` and `A/publication/`: a named follow-up.

## Decisions

1. **Path-keyed commands.** `Command.name` is the space-joined path and `COMMANDS` stays one eager
   dict. `select_argv` takes the longest prefix of up to three words that is a key, accepts
   positionals and `--`, and returns `(command, None)` for a prefix without a matching entry.
2. **Groups.** One `GROUPS` constant beside `COMMANDS` maps a path prefix to its help and hidden
   flag (`lane` and `hook` hidden). Bare help lists non-hidden groups; `<group> --help --json`
   prints that group's part: its own commands in full and its non-hidden nested groups by name and
   help, as bare `--help --json` prints the root commands and the shown groups. So `lane`, whose 26
   entries took 98,582 bytes and moved to the bound detail, prints its 12 commands and four groups
   in 43,021 bytes, within the unchanged 48 KiB help budget (S5). Kernel modules under 500 LE each:
   `attestation`, `hook`, `lane`, `lane_repair`, `retire`, `handoff`, `lease`, `host`.
3. **`modes()` and reusable field types, delivered first.** `modes()` returns the preview and
   apply pair (selectors `apply=false|true`; the apply entry adds `authorize` where its kind needs
   it, the write effects and a `verdict` exit). Recurring fields are composed, not inherited: one
   `Annotated` type each for `apply`, `authorize`, `expect_head`, `reason`, `change`, `receipt`,
   `receipt_sha256` and `subject` carries its type, constraint, description and CLI spelling, and
   every request lists its own fields, so a model's whole surface reads in one place and its order
   is the declaration's, not a base-class order. A field type joins the slice that first uses it.
4. **Authorization classifies; bodies enforce.** `authorize` for `--apply --authorize` leaves,
   `apply` for `revoke-source`, `attestation record|release` and `project`, `confirm-irreversible`
   for `retire absorbed-ref` and `candidate --refresh-from-accepted`, `attestation` for
   `lane lease takeover`. Effects are at or above the old classifier's. `hook install` is
   `local-write host-write` with authorization `none`, a named exemption owned by A8;
   `--reset-state` is a separate `authorize`, destructive entry. `host run` is `execute opaque`,
   `human`, destructive.
5. **`IMPLEMENTATIONS` by command**, with
   `IMPLEMENTATIONS.get(operation.id) or IMPLEMENTATIONS[command]`: about 38 rows plus overrides for
   `lane candidate` and `lane retire abandon`. Application modules: `A/lane/`, `A/hook/`,
   `A/attestation.py`, `A/host.py`, with one report-to-result projection in `A/lane/result.py`.
6. **Adapter.** `S/catalog.py` routes on `argv[1:4]`, builds only the invoked group's Cyclopts `App`
   and imports only its application half, generating a signature per path. Kernel models stay eager;
   S1 records their measured import cost. The adapter reads stdin for `lane prewrite --patch -` and
   `lane redact --key-stdin`; the application never reads it. `mcp` stays a 17-line launcher
   outside the catalog, `opaque` and `human` by the unselected default.
7. **Usage refusals name the full path:** `command_usage_invalid:lane start`, payload `command` the
   path; an unknown subcommand names the group, an unknown root `ethos`.
8. **`process` exit.** The `host run` half returns an `EthosResult` and sets `data.exit_status` on
   every non-gap result; the adapter acts on it only for an entry with `exit="process"`: no frame,
   then `SystemExit(exit_status)`. A table rule requires the set field. `result.py` is unchanged.
9. **Golden `next` data.** An uncommitted generator in owned scratch runs the old classifiers over
   each leaf and its mode-bearing flag subsets and writes one JSON file under `tests/fixtures/`; the
   test records the provenance. Per argv: effects, authorization rank and destructiveness at or
   above the old, exit kind equal; a `refused` class asserts `("", opaque, human, true)`.
10. **Docs-registry provider** moves to `A/docs_registry.py` in S5 as its own commit, checking
    examples against the `COMMANDS` and `GROUPS` paths and the `mcp` launcher. `system/gates.toml`
    spells the new reference literally; an exported constant serves the five tests that name it.
11. **Fence** (`src/ethos/adapters/admission/control/replacement.py`), widened by the owner's
    acknowledgement on 2026-11-09: S1 adds the catalog, invocation, console, attestation, host
    modules, `S/catalog.py`, `S/output.py`, `S/application.py`, `S/root_binding.py` and
    `surface/mcp/`; S2 swaps `S/hook/` for `A/hook/` and adds `retention.py` and `peer_identity.py`;
    S3 adds `A/lane/` and `redaction.py`; `S/root/` stays while it holds `mcp.py`. A test checks,
    for group entries, that each prefix exists and each write, hook or `opaque` module lies under
    one.
12. **Breaking changes** are named in the CHANGELOG: the refusals of the audit table (a field
    outside its mode, such as `--authorize` without `--apply`), the full-path usage gap, and the
    additive keyword spelling of positionals. Body checks that own a gap code (`lane retire abandon`
    without `--receipt`, `lane refresh-base --source-ref` with rebase) stay, their fields optional.

## Audit

Decision 12's rows for the S1 leaves, read from the old commands and the new adapter (the S1 spike
and the CLI tests). Product callers were searched in `src`, `tools`, `.gitlab-ci.yml` and `.github`;
the one emitter, `src/ethos/adapters/mutation/lane_lifecycle/archive/command.py:464`, renders
`attestation query --predicate … --subject … --json`, which selects `attestation.query`. S2 adds
the `hook` rows below; S3 and S4 add their leaves' rows before writing entries.

| Leaf                  | Flag or shape                                                        | Exit before                           | Exit after                                      |
| --------------------- | -------------------------------------------------------------------- | ------------------------------------- | ----------------------------------------------- |
| `attestation record`  | missing `--input`                                                    | 2 `command_usage_invalid:attestation` | 2 `command_usage_invalid:attestation record`    |
| `attestation record`  | the input as a word                                                  | binds                                 | binds: `input_path` stays positional            |
| `attestation record`  | `--evidence` without `--apply`                                       | read by the preview                   | unchanged: a field of both entries              |
| `attestation record`  | `--authorize`, which no entry takes                                  | 2, unknown option                     | 2 `command_usage_invalid:attestation record`    |
| `attestation release` | missing `--id`                                                       | 2, the group word                     | 2, the full path                                |
| `attestation release` | `--reason` without `--review-content`, or the reverse                | ignored by the body                   | unchanged: fields of both entries               |
| `attestation query`   | `--apply`, or a word                                                 | 2, usage error                        | 2 `command_usage_invalid:attestation query`     |
| all three             | `--no-apply`, `--no-review-content`, `--empty-evidence`, `--no-json` | accepted                              | 2: no negated forms, as for the root commands   |
| `host run`            | no command                                                           | 1 `host_run_command_missing`          | unchanged                                       |
| `host run`            | the command's status                                                 | the exit status, no frame             | unchanged, also under `--json`                  |
| `host run`            | `--root <path>` before `--`                                          | taken into the command                | ETHOS's `--root`, as `--json` and `--wait` were |

The `hook` rows come from one probe that runs every shape below through the old commands and the
new adapter and records each exit and the arguments each body received. Product callers were
searched in `src`, `tools`, `.gitlab-ci.yml`, `.github`, `.config/ci` and `.agents`: the CI jobs
render `hook commit-range` with named coordinates, alone or after `--check peer-identity`;
`src/ethos/adapters/repo/hook/admission.py` renders
`hook ref-transaction <ref> <old> <new> --phase prepared`; the install continuations render
`hook install --root <root>`, with `--runtime <path>` or `--reset-state --authorize`; and each
retirement preview renders its own `--apply --authorize` step. Each selects its entry and none
renders a refused shape; no caller renders `hook admit` or `hook ref-update`. With a profile that
does not validate, every hook command keeps its exit, as each body reports the profile's gap.

| Leaf                                   | Flag or shape                                                                               | Exit before                            | Exit after                                                   |
| -------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------ |
| all seven                              | a missing or invalid field, or an unknown option                                            | 2 `command_usage_invalid:hook`         | 2, the full path, such as `command_usage_invalid:hook admit` |
| all seven                              | `--no-require-editor-root`, `--no-reset-state`, `--no-apply`, `--no-authorize`, `--no-json` | accepted                               | 2: no negated forms                                          |
| `hook admit`                           | several paths after one `--paths`                                                           | binds them                             | 2 `command_usage_invalid:hook admit`                         |
| `hook admit`                           | the paths as words, or `--paths` once per path                                              | binds                                  | unchanged                                                    |
| `hook commit-range`                    | `--check peer-identity` with `--trusted-baseline`                                           | ignored by the body                    | unchanged: one entry takes every field                       |
| `hook commit-range`                    | the coordinates as words                                                                    | 2, the group word                      | 2, the full path: the coordinates stay named                 |
| `hook ref-transaction`                 | `--ref-name`, `--old-value` and `--new-value` for the words                                 | binds                                  | unchanged                                                    |
| `hook install`                         | `--authorize` without `--reset-state`                                                       | ignored by the body                    | 2 `command_field_refused:authorize`                          |
| `hook install`                         | `--reset-state` without `--authorize`                                                       | 1 `state_reset_authorization_required` | unchanged: a body check                                      |
| `hook retire-supply`, `retire-records` | `--authorize` without `--apply`, with or without `--expect-plan`                            | ignored by the preview                 | 2 `command_field_refused:authorize`                          |
| `hook retire-supply`, `retire-records` | `--expect-plan` without `--apply`                                                           | ignored by the preview                 | unchanged: a field of both entries                           |
| `hook retire-supply`, `retire-records` | `--apply` without `--authorize`                                                             | 1 `authorization_required`             | unchanged: a body check                                      |

The S3 rows come from one probe of 139 argv shapes through the old commands and the new adapter,
recording each exit, the gaps, the standard input read and the arguments each body received, and
from 13 real previews against a profile that does not validate, which keep their exits, verdicts
and gaps. Product callers were searched in `src`, `tools`, `.gitlab-ci.yml`, `.github`,
`.config/ci` and `.agents`: status reads, landing, retirement and admission render
`lane status --json`; the archive effect and OpenSpec scope render
`lane prewrite --paths <path> --editor-root <root> --require-editor-root`; landing, proof, status
bindings and the refresh render `lane refresh-base --apply --authorize --expect-head <head>`, and
the merge steps `--strategy merge --mode <mode>` with `--expect-state` and `--subject`; the
candidate renders its bootstrap `--path --expect-head --apply` and its refresh
`--refresh-from-accepted --apply --authorize`, with `--confirm-irreversible` when it drops commits;
the other leaves render their own `--apply --authorize` step; and the CI acceptance runs
`lane format` with `--check` or `--apply --authorize --expect-head`, `lane project --patch` and
`lane repair-paradigm`. Each selects its entry and none renders a refused shape. The authorized
leaves are `housekeeping`, `refresh-base`, `project`, `format`, `trust-commit-signer`,
`repair-signature` and `redact private-addresses`.

| Leaf                       | Flag or shape                                                                                                                | Exit before                                                      | Exit after                                                         |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------ |
| all thirteen               | a missing or invalid field, or an unknown option                                                                             | 2 `command_usage_invalid:lane`                                   | 2, the full path, such as `command_usage_invalid:lane start`       |
| all thirteen               | `--no-apply`, `--no-authorize`, `--no-check`, `--no-json` and every other negated flag                                       | accepted                                                         | 2: no negated forms                                                |
| the authorized leaves      | `--authorize` without `--apply`                                                                                              | ignored by the preview                                           | 2 `command_field_refused:authorize`                                |
| the authorized leaves      | `--apply` without `--authorize`                                                                                              | 1, the body's authorization gap                                  | unchanged: a body check                                            |
| `candidate`                | `--authorize` or `--confirm-irreversible` on a bootstrap, with or without `--apply`                                          | ignored by the bootstrap                                         | 2 `command_field_refused:<field>`                                  |
| `candidate`                | `--authorize` without `--apply`, or `--confirm-irreversible` outside `--refresh-from-accepted --apply`                       | ignored by the body                                              | 2 `command_field_refused:<field>`                                  |
| `candidate`                | `--path` with `--refresh-from-accepted`; `--preserved-preimage`, `--retention-ref`, `--reason` or `--expect-state` elsewhere | ignored by the body                                              | 2 `command_field_refused:<field>`                                  |
| `candidate`                | `--materialize` with `--refresh-from-accepted`                                                                               | `candidate_mode_conflict`, 0, or 1 with `--apply`                | 2 `command_operation_unmatched:lane candidate`                     |
| `candidate`                | `--materialize` with `--path`                                                                                                | `candidate_mode_conflict`, 0, or 1 with `--apply`                | 2 `command_field_refused:path`                                     |
| `candidate`                | `--refresh-from-accepted --apply` without `--confirm-irreversible`                                                           | runs; the body asks for the confirmation before it drops commits | unchanged; `next` reads it as confirm-irreversible and destructive |
| `prewrite`                 | several paths after one `--paths`, also `--paths=a b`                                                                        | binds them                                                       | 2 `command_usage_invalid:lane prewrite`                            |
| `prewrite`                 | the paths as words, or `--paths` or `--paths=` once per path                                                                 | binds                                                            | unchanged                                                          |
| `prewrite`                 | `--patch -`                                                                                                                  | 2, `-` was not a value (only `--patch=-` read stdin)             | binds; the CLI reads stdin for the operation                       |
| `format`                   | `--paths <path>` for the words                                                                                               | 2, unknown option                                                | binds, as the words do                                             |
| `start`                    | `--name` for the word                                                                                                        | binds                                                            | unchanged                                                          |
| `redact private-addresses` | `--apply --verify`                                                                                                           | the verify ran; `--apply` was ignored                            | 2 `command_operation_unmatched:lane redact private-addresses`      |
| `redact private-addresses` | `--key-stdin`, `--expect-head`, `--base`, `--head` or `--rotate` in a mode that ignores it                                   | ignored                                                          | unchanged: fields of every entry                                   |
| `refresh-base`             | `--source-ref` with the rebase strategy                                                                                      | the body's merge path                                            | unchanged: a field of both entries                                 |
| `repair-signature`         | `--corrections`, `--corrections-sha256`, `--reason`, `--backup`, `--replacement`                                             | the corrections' checks and the extended next action             | unchanged                                                          |

The S4 rows come from one probe of 106 argv shapes through the old commands and the new adapter,
recording each exit, the gaps, the next step's form and the arguments each body received, and from
13 real previews against a profile that does not validate, which keep their exits, verdicts and
gaps. Product callers were searched in `src`, `tools`, `.gitlab-ci.yml`, `.github`, `.config/ci`
and `.agents`: the abandonment derivation renders
`lane retire abandon --receipt <path> --receipt-sha256 <sha> --authorize --apply`; the retirement
continuations render `recover` with the same receipt and `--authorize --apply`, the content review
`abandon --branch|--path --review-content --reason-code --reason`, the re-derivations
`abandon --branch --reason-code --reason` and `landed --branch`, and the unbound routes
`superseded --branch --expect-head --path --absorbed-by --reason` and
`absorbed-ref --branch --expect-head --accepted-head`; linked and absorbed retirement render their
own `--authorize --apply` step, with `--confirm-irreversible` for an absorbed ref; status bindings
render `lane retire landed --branch`; archive, status and admission render
`lane lease resume|renew` with the four coordinates and `--apply` or the bare preview, and
`lane lease reacquire --path --holder-ref`, whose preview adds
`--expect-head --expect-snapshot --expires-at --authorize --apply`; and the CI acceptance derives
and recovers an abandonment, takes `lane handoff transfer` and the reacquisition through their
previews and applies, and previews an absorbed ref. Each selects its entry and none renders a
refused shape. The authorized leaves are the five `lane retire` commands and
`lane lease reacquire`.

| Leaf                                        | Flag or shape                                                                                   | Exit before                               | Exit after                                                                      |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------- |
| all thirteen                                | a missing or invalid field, or an unknown option                                                | 2 `command_usage_invalid:lane`            | 2, the full path, such as `command_usage_invalid:lane retire landed`            |
| `lane retire`, `lease`, `handoff`, `redact` | no subcommand, or an unknown one                                                                | 2 `command_usage_invalid:lane`            | 2, the group, such as `command_usage_invalid:lane retire`                       |
| all thirteen                                | `--no-apply`, `--no-authorize`, `--no-review-content`, `--no-json` and every other negated flag | accepted                                  | 2: no negated forms                                                             |
| all thirteen                                | a next action that renders one of them                                                          | `next` without a form, from the argv rows | `next` names the entry, with its effects, authority and deletion                |
| the authorized leaves                       | `--authorize` without `--apply`                                                                 | ignored by the preview                    | 2 `command_field_refused:authorize`                                             |
| the authorized leaves                       | `--apply` without `--authorize`                                                                 | 1, the body's authorization gap           | unchanged: a body check                                                         |
| `retire absorbed-ref`                       | `--confirm-irreversible` without `--apply`                                                      | ignored by the preview                    | 2 `command_field_refused:confirm_irreversible`                                  |
| `retire absorbed-ref`                       | `--apply` without `--confirm-irreversible`                                                      | 1 `irreversible_confirmation_required`    | unchanged: a body check                                                         |
| `retire abandon`                            | `--apply` without `--receipt`                                                                   | 1 `lane_retirement_receipt_required`      | unchanged: a body check of the derivation's apply                               |
| `retire abandon`                            | `--receipt-sha256` without `--receipt`                                                          | the receipt path, with an empty receipt   | 2 `command_field_refused:receipt_sha256`                                        |
| `retire abandon`                            | `--branch`, `--path`, `--reason-code`, `--reason` or `--review-content` with `--receipt`        | ignored by the receipt                    | 2 `command_field_refused:<field>`                                               |
| `retire abandon`, `recover`                 | `--receipt` without `--receipt-sha256`                                                          | the receipt's own gap, or 2 for `recover` | unchanged                                                                       |
| `lease renew`, `resume`                     | a preview that omits some of the four coordinates                                               | reads them from the current Lease         | unchanged                                                                       |
| `lease renew`, `resume`                     | `--apply` without all four coordinates                                                          | 1 `lease_coordinates_required`            | unchanged: a body check                                                         |
| `lease takeover`                            | `--authorization`, which every takeover takes                                                   | `attestation` from the token              | unchanged; `next` reads its preview and its apply as `attestation`              |
| `handoff export`                            | `--ttl-seconds`, which no export reads                                                          | accepted                                  | 2 `command_usage_invalid:lane handoff export`                                   |
| `handoff import`                            | `--apply`                                                                                       | `next` reads `local-write`                | unchanged; `next` adds `host-write`, as the import adds a worktree like `start` |
| the `lease` leaves, `handoff transfer`      | a result whose verdict is `unknown`                                                             | state `blocked`                           | state `unknown`, as every lane result                                           |

## Slices

One Change, ordered commits. Each slice records its measured product and test delta in its task and
ends with ruff, `ty`, `lint-imports`, the module-layout gate, the table test, the golden data, the
impacted sweep and readiness.

| Slice | Content                                                                                                                      | Import rows | Destructive rows | Product      | Tests        |
| ----- | ---------------------------------------------------------------------------------------------------------------------------- | ----------- | ---------------- | ------------ | ------------ |
| S1    | spike, golden data, path keys, `GROUPS`, `modes()`, field types, `process`, adapter, `attestation`, `host run`, fence part 1 | 5           | 1                | at most +110 | at most +100 |
| S2    | `hook` (7 leaves)                                                                                                            | 14          | 3                | +10          | -60          |
| S3    | `lane` lifecycle (7) and repair (6)                                                                                          | 18          | 2                | +50          | -80          |
| S4    | `lane` retire, handoff, lease (13)                                                                                           | 12          | 6                | +20          | -80          |
| S5    | delete old modules and tables, provider move, spec, rule, docs                                                               | 3           | 0                | -50          | -30          |
| total |                                                                                                                              | 52          | 12               | gate +200    | gate -100    |

A slice that misses its figure is re-cut before the next begins. If S2 to S4 cannot recover toward
the test total, the work stops and returns to the committee.

## Risks / Trade-offs

- The test total is the weakest figure: S1 may add up to +100 and S2 to S4 must recover about -220
  from deleted option, annotation and wrapper tests.
- Unspiked: the `process` exit and `lane prewrite` stdin through the generated signature; S1 spikes
  both first.
- The audit table is complete for S1 only; S2 to S4 add their leaf rows before writing entries, and
  each new refusal is a CHANGELOG line.
- The fence widens; root-write implementations stay outside it until a follow-up.
- `hook install` remains a tokenless write under a named exemption until A8.
- Unverified: effective-line arithmetic, the kernel import cost, callers in adopter repositories,
  whether the golden JSON counts toward the test ceiling.

## Migration Plan

Commits follow the slices. Until S5 the old classifier tables and command modules of unmigrated
groups remain as counted shims. Rollback reverts a slice; nothing migrates.
