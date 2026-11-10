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
   prints that group's part. Kernel modules under 500 LE each: `attestation`, `hook`, `lane`,
   `lane_repair`, `retire`, `handoff`, `lease`, `host`.
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
    examples against the `COMMANDS` paths. `system/gates.toml` keeps its literal; an exported
    constant serves the five importing tests.
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

## Slices

One Change, ordered commits. Each slice records its measured product and test delta in its task and
ends with ruff, `ty`, `lint-imports`, the module-layout gate, the table test, the golden data, the
impacted sweep and readiness.

| Slice | Content                                                                                                                 | Import rows | Destructive rows | Product      | Tests        |
| ----- | ----------------------------------------------------------------------------------------------------------------------- | ----------- | ---------------- | ------------ | ------------ |
| S1    | spike, golden data, path keys, `GROUPS`, `modes()`, mixins, `process`, adapter, `attestation`, `host run`, fence part 1 | 5           | 1                | at most +110 | at most +100 |
| S2    | `hook` (7 leaves)                                                                                                       | 14          | 3                | +10          | -60          |
| S3    | `lane` lifecycle (7) and repair (6)                                                                                     | 18          | 2                | +50          | -80          |
| S4    | `lane` retire, handoff, lease (13)                                                                                      | 12          | 6                | +20          | -80          |
| S5    | delete old modules and tables, provider move, spec, rule, docs                                                          | 3           | 0                | -50          | -30          |
| total |                                                                                                                         | 52          | 12               | gate +200    | gate -100    |

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
