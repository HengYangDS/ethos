# Design

Code is cited at `dev` `77d21c5b5`. `L`, `A`, `P`, `R`, `I` and `N` are `land/operation.py`,
`adoption.py`, `publication/operation.py`, `proof/operation.py`, `inspection.py` and `plan.py` in
`src/ethos/application/`; `cli/` is `src/ethos/surface/cli/`. LE are effective lines
(`ethos.measure.effective_code_lines_for_source`; per-file ceiling 500,
`src/ethos/contracts/paradigm/paradigm.toml:99`). Only read-only probes ran.

## Context

- A5a (archived `2026-11-08-catalog-root`) declares 29 root operations. The CLI adapter
  (`cli/root/catalog.py:53-70`) selects and calls `invoke` (`application/catalog.py:118-124`);
  `catalog_operation` (`:92-115`) selects again around the six SDK functions, five of which MCP
  serves through FastMCP (`surface/mcp/server.py:141-158`).
- Each SDK function then picks its body by first match (`L:430-490`, `A:73-96`, `P:438-454`,
  `R:79-85`), which only an edit can make drift from the selection; the 29 IDs run 15 bodies.
- Fifteen root rows remain in `.config/checks/import-linter/import-linter.toml` (`:29-35`, `:80-81`,
  `:90-93`, `:96-97`): the console in `src/ethos/cli.py`, the bound in `cli/output.py`, root
  binding, `version_text` and `with_runtime`; `cli.py:94` also loads
  `ethos.repository.paradigm.parameters` by string, which the contract cannot see.

## Goals / Non-Goals

Goals:

- Each operation ID maps to exactly one implementation `(root, request) -> EthosResult`; no SDK
  function reads a field, and each keeps its name, keyword signature, defaults and docstring.
- The fifteen rows empty, and `ethos.cli` loads no lower layer, even by string.
- No result, exit, frame or effect changes for a typed request; the suite is the regression.
- Adopters see nothing change: their commands, flags, exits and JSON fields, the console script
  `ethos.cli:console_main`, `python -m ethos.cli`, the hook entry
  `ethos.adapters.repo.hook.protocol` and the five MCP tools stay as they are, and the SDK's
  Changed line (Decision 4) is the only observable change.

Non-Goals:

- Splitting a body by mode or changing its gaps, states or next actions; the group rows (A6:
  `:36-79`, `:82-89`), the actor reader (A7: `:94`), per-entry MCP tools and model-derived schemas
  (A16: `:95`), and deadlines and handles with `invoke` in `invocation` (A10; `rc-plan`, A.1).

## Decisions

1. **One table.** `IMPLEMENTATIONS` in `ethos.application.catalog` maps each of the 29 IDs to
   `"module:function"` in place of the six-row `OPERATIONS` (`application/catalog.py:26-33`),
   keeping imports lazy. An implementation is public, takes `(root, request)` with the command's
   model, stays in its body's module and, as the catalog's docstring adds, only `invoke` calls it.
2. **One function per body.** Fifteen functions serve the 29 IDs (Appendix A): preview and apply,
   adopt's runtime selection and publish's probe, apply and retirement already share a body that
   reads `apply`, `select_runtime`, `receipt`, `retire`, `execute` or `full`, and no implementation
   reads a field to choose another body. One function per ID would need 14 forwards, which the
   identity-forward rule (`rules/module-layout.md:165-171`) refuses, or wrappers restating a
   selector value the request carries.
3. **SDK bodies.** After its docstring, each keyword SDK function only returns
   `invoke("<command>", root, locals())`, so the mapping holds exactly its parameters;
   `prove_repository` passes its request. FastMCP's schemas, the signature test
   (`tests/unit/kernel/test_operation_catalog.py:137-147`) and
   `docs/reference/command-plane.md:104-119` keep their source. Ruff passes the shape, since
   `locals()` uses every argument (draft 1's probe), and the identity-forward check sees a literal
   and a computed mapping. `catalog_operation` goes.
4. **`invoke` selects, then runs under today's normalization.** `invoke(command, root, fields)`
   takes a request or a mapping, drops a mapping's `root` entry only when it is the `root`
   argument itself (`isinstance(fields, Mapping) and fields.get("root") is root`, as `locals()`
   passes it), so a caller's stray
   `root` key is still refused as `command_usage_invalid`, selects, returns a refusal unchanged and
   otherwise runs
   `application_result(command)(implementation)(root, chosen.request)`, so selection stays outside
   `invocation_scope()`; the CLI adapter is unchanged and re-selects through `invoke`, which is
   pure. Every body now runs the validated request, which the proposal and CHANGELOG name in one
   Changed line: the root SDK functions run the request their selection validated, as the CLI and
   MCP tools already do, so a list arrives as a tuple, `land_repository(root, apply="false")`
   previews as it selects, `prove_repository(root, {...})` no longer raises `AttributeError`, and
   a mapping whose `root` entry is the very `root` argument now runs where it is refused today. No
   caller in the repository passes such a value (review 1).
5. **Preambles stay with their bodies.**
   - land: a private `_landing(closeout=...)` decorator holds `selected_change`, `root.resolve()`
     and `profile_blocks_operation` (`L:425-429`); `close_out` reads the head after the legacy role
     check (`L:458-463`) and `land_on_candidate` first (`L:464`), each passing its command as a
     literal (`L:465`); release and retag never read it; the unreachable `L:427` check goes.
   - publish: a private `_publishing` decorator holds `root.resolve()` and the profile guard
     (`P:435-437`) for both bodies, as `_landing` does for land, so the guard has one copy and
     `project_publication` drops to complexity 9 of 10 (`.config/checks/ruff/ruff.toml:72`).
     `project_publication` binds only `target_refs`, which its body reassigns, and reads the other
     fields inline. The body's receipt mapping `request` (`P:110-199`) becomes `receipt_request`,
     still passed as `_publication_result(request=receipt_request)`, so the `request` parameter
     is never shadowed.
   - prove: `_proof_preflight` keeps only the local-source admission (`R:71-78`) and its call, so
     the patches at `test_proof_command.py:133`, `:265` and `:445` hold; `prove_readiness` and
     `prove_on_host` run `R:79-85`'s observations under `selected_change` on `root.resolve()`, as
     `R:335` passes it (`proof/host.py:40-44`, `:76-78`); `prove_governed` keeps `R:334-335`.
   - status and plan: the bodies move unchanged and read `request.change` and `request.changed`.
6. **The console moves to `ethos.application.console` (rows 29-35, 90).**
   `ethos.application.invocation` keeps only failure normalization (`invocation.py:1`). Moved:
   `run_console(argv: list[str], main: Callable[[], None]) -> EthosResult | None`,
   the runtime re-execution returning a failure that `console_main` emits with `enforce=True`, as
   today (`cli.py:38-75`, `:156`; `output.py:158`); `command_boundary(command, argv, emit)`, a
   context manager with the command scope and failure results (`:82`, `:99-112`, `:115-181`),
   where `emit(result, *, json_output: bool, enforce: bool) -> None` is the callable `main`
   passes; `invocation_parameters(command: str, argv: list[str])`, keeping the `mcp`
   exemption (`cli.py:96`) and importing `repository_parameters` statically, as
   `adapters/repo/runtime/selection.py:28` does; and `resolve_root` with its context variable
   (`cli/root_binding.py:15-30`). Every `resolve_root` importer present when commit 2 is written
   changes one import line: the 13 command modules that `load_command_groups([])` loads at
   `77d21c5b5`, and 14 once `peer-identity-redaction` lands (`surface/cli/lane/redaction.py:14`);
   if A5b lands first, that Change's module imports `ethos.application.console` instead.
   `_argument_root` and the failure builders stay private. `ethos.cli` keeps `console_main`, `main`
   and its surface calls and passes `main` and an `emit` callable that resolves
   `ethos.surface.cli.output` when called, since that module's Cyclopts import (`output.py:16`) must
   not load for `ethos --version` (`test_version_command.py:61-85`). The console thus loads no
   surface module and emits failures inside the command scope; no SDK or MCP module imports it.
7. **The result projection (rows 80-81, 91-93, 96-97).** New `ethos.application.result_projection`
   holds `with_runtime` (`surface/runtime_identity.py:14-31`); the bound with its detail store
   (`cli/output.py:41-43`, `:71-79`) as `bounded_result(result, *, anchor: Path | None)`, whose
   `None` falls back to `Path.cwd()` (`output.py:73`), anchored at the artifact root or
   `console.resolved_root()` that `output.emit` passes, so the projection MCP shares imports no
   console; and
   `version_result()`, the identity result with its artifacts (`cli/version.py:18-23`, `:25-34`,
   `:44-52`). `cli/version.py` keeps a rendering-only `version_text`, the JSON dump of
   `with_runtime(version_result())` as today (`version.py:35-36`) or the human line from the
   result's fields, still without a
   committed-build read (`:24`, `:35-41`), so `cli.py:29` and `cli/application.py:13` keep their
   import. `surface/runtime_identity.py` retires, `surface/mcp/server.py:29` and `cli/version.py:13`
   import `with_runtime` from the projection, `root_binding.py` keeps `RootOption`, and `output.py`
   drops its two `emit_*` failure helpers (`:144-159`).
8. **Tests and callers.** The table test gains one case, replacing `test_operation_catalog.py:47`
   and `:148`: `IMPLEMENTATIONS` keys equal the 29 IDs, each value resolves under
   `ethos.application.` to a two-parameter function whose second parameter is its command's model,
   and no model declares `root`; the signature test (`:137-147`) compares annotations as well as
   defaults. Both read annotations through
   `typing.get_type_hints(function, localns={"Path": Path})`, since `R` postpones them (`R:3`)
   and imports `Path` only for type checking (`R:56`). The refused-mode case
   (`tests/unit/application/test_proof_operation.py:24-27`) gains
   its mapping-and-list form, `{"acceptance_purpose": "local-source", "gate": ["ruff"]}`, which
   raises `AttributeError` at `R:334` today and must return what `ethos prove` renders. No SDK call
   changes, and kept helpers' patches hold (`test_proof_command.py:132-143`,
   `test_host_gate_proof.py:196`, `test_contracts_closeout.py:486`,
   `test_post_archive_planning.py:34-39`). Retargets to `console`: the patches of
   `cli.git_common_dir`, `current_runtime`, `subprocess` and `os.execv`
   (`adapters/repo/runtime/test_selection.py:389-392`, `test_invalid_profile_boundary.py:209`,
   `adoption/test_greenfield.py:193-197`) and of `cli.command_scope` (`test_catalog_commands.py:68`,
   `test_invocation_facts.py:240`). Retargets to `result_projection`: `output.git_common_dir`
   (`surface/cli/test_output.py:225`), the identity readers and `OFFICIAL_VERSION`
   (`test_version_command.py:33`, `:47`, `:50`; `test_invalid_profile_boundary.py:16`, `:248`,
   `:270`), the runtime module (`test_result_runtime.py:8-42`) and `with_runtime` imports
   (`surface/mcp/test_binding.py:14`, `test_contracts_closeout.py:23`,
   `test_invalid_profile_boundary.py:30`, `tools/ci/delivery/acceptance/mcp.py:27`). Patches of
   `cli.main`, `cli.sys` and `cli.import_module` (`adapters/repo/runtime/test_binding.py:203-343`,
   `test_selection.py:349`, `adoption/test_greenfield.py:198`,
   `adapters/process/test_capture.py:277`,
   `:344`, `adapters/test_process.py:459`) hold, as `ethos.cli` keeps those names and `main`
   keeps its zero-argument signature, which `run_console` calls.
9. **Parity stays meaningful.** With every transport reaching `invoke`, parity tests
   (`test_catalog_commands.py:89-117`, `test_proof_operation.py:21-47`,
   `test_terminal_command_surface.py:128-133`, `land/publication/test_effect.py:63-73`) keep testing
   what differs: Cyclopts' parse, spellings, root binding and exits, the SDK's `locals()` capture
   and the MCP schema (`surface/mcp/test_binding.py:50-75`), which the signature test pins.

## Risks / Trade-offs

- `locals()` is implicit: a statement placed before it adds a name, which selection refuses as
  `command_usage_invalid` in every SDK and MCP test, so the failure is loud.
- Shared bodies still branch on selector fields (`P:113-122` on `receipt` and `retire`, `L:264`,
  `:283` on `apply`), so a selector and its body can still drift inside one, and an implementation
  imported directly skips failure normalization and the selection that A5a's in-process API promises
  (archived spec `:294-296`), which Decision 1's docstring line states.
- Size (Appendix B): about −72 to −87 product LE, short of the scope note's −150 to −250, as the SDK
  signatures (55 LE) stay, each body regains its preamble, and the separate console and the
  surface's `version_text` cost about 37 LE against draft 1's layout.
- Move 2 edits one import line in each `resolve_root` importer, 14 once `peer-identity-redaction`
  lands, 12 of them A6's; A6's owner is the same team, so this behaviour-free edit needs no
  separate consent. `IMPLEMENTATIONS` strings escape
  import-linter, so the table test resolves each one.

## Migration Plan

1. Commit 1 (Decisions 1 to 5 with Decision 8's three cases): the table, signature and parity tests,
   the SDK callers, the land, adopt, publish and prove suites, Ruff, `ty` and the module-layout
   gate.
2. Commit 2 (Decisions 6 and 7, the retargets, the 15 rows): Decision 8's console, output, version,
   runtime and process tests, `test_greenfield.py`, `test_version_command.py:61-85` and the table
   test, whose `load_command_groups([])` (`test_operation_catalog.py:109`) imports every retargeted
   module, 14 once `peer-identity-redaction` lands; Ruff, `ty` and the module-layout gate; then the
   import-boundaries gate.
3. No spec delta (`skip_specs: true`): the requirement already has every transport run the same
   typed operation (`openspec/specs/command-plane/spec.md:1245-1249`). Rollback reverts either
   commit; nothing migrates. Both commits stay in this Change: they share the table test, and the
   rows retire only with commit 2's moves.

## Open Questions

None.

## Appendix A. Operations and implementations

| Operations                      | Branch today | Body today  | Implementation                |
| ------------------------------- | ------------ | ----------- | ----------------------------- |
| `status.inspect`                | none         | `I:73-251`  | `I.inspect_status`            |
| `plan.compile`                  | none         | `N:36-239`  | `N.compile_transition_plan`   |
| `proof.{preview,execute,run}`   | `R:81-82`    | `R:338-497` | `R.prove_governed`            |
| `proof.readiness`               | `R:79-80`    | inline      | `R.prove_readiness`           |
| `proof.host`                    | `R:81-85`    | inline      | `R.prove_on_host`             |
| `land.{preview,apply}`          | `L:479-489`  | `L:241-361` | `L.land_on_candidate`         |
| `land.closeout.{preview,apply}` | `L:458-478`  | `L:111-238` | `L.close_out`                 |
| `land.release.{preview,apply}`  | `L:439-457`  | inline      | `L.release_accepted_head`     |
| `land.retag.{preview,apply}`    | `L:430-438`  | `L:364-400` | `L.move_release_tags`         |
| `publish.readiness`             | `P:451-454`  | inline      | `P.report_readiness`          |
| `publish.{probe,apply}`         | `P:438-450`  | `P:93-207`  | `P.project_publication`       |
| `publish.retire.{probe,apply}`  | `P:438-450`  | `P:93-207`  | `P.project_publication`       |
| `adopt.{preview,apply}`         | `A:97-172`   | inline      | `A.adopt_existing`            |
| `adopt.runtime.{preview,apply}` | `A:97-172`   | inline      | `A.adopt_existing`            |
| `adopt.create.{preview,apply}`  | `A:83-96`    | `A:249-373` | `A.form_repository`           |
| `adopt.evolve-starter.preview`  | `A:81-82`    | `A:198-246` | `A.propose_starter_evolution` |
| `adopt.exit.{preview,apply}`    | `A:73-80`    | `A:175-195` | `A.leave_ethos`               |

## Appendix B. Sizes

| SDK function         | Module | Dispatch | Signatures | Re-added | Net        |
| -------------------- | ------ | -------- | ---------- | -------- | ---------- |
| `land_repository`    | 463    | 68       | 33 → 3     | 48–54    | −44 to −50 |
| `adopt_repository`   | 357    | 25       | 25 → 3     | 3–7      | −40 to −44 |
| `publish_repository` | 447    | 21       | 13 → 1     | 13–16    | −17 to −20 |
| `prove_repository`   | 443    | 10       | none       | 13       | +3         |
| `inspect_repository` | 233    | 1        | none       | 3        | +2         |
| `plan_repository`    | 274    | 1        | none       | 3        | +2         |
| `catalog.py`         | 87     | 29       | none       | 34       | +5         |

Move 1, in LE (module: today's total), about −89 to −102; Module, Dispatch and Signatures (the seven
private bodies') are measured, Re-added and Net estimated. Dispatch: decorators and branches
(`L:403`, `:425-490`; `A:47`, `:73-96`; `P:420`, `:435-454`; `R:331`, `:334-335`, `:79-85`), a
dropped import, and the catalog's `catalog_operation` (18), `OPERATIONS` (8) and three imports.
Re-added: land's `_landing` (12), moved release (18), legacy check (5) and two head reads (2);
`report_readiness` (7); prove's three implementations (11); `IMPLEMENTATIONS` (31); per module an
SDK body, `def` and decorator lines, imports and up to six wrapped field reads.

Move 2, measured with a stdlib copy of the measure on in-memory sketches: `src/ethos/cli.py` 154 →
37 LE, the new `application/console.py` 146, `application/invocation.py` 83 unchanged, the new
`application/result_projection.py` 60, `cli/output.py` 119 → 93, `cli/root_binding.py` 17 → 5,
`cli/version.py` 43 → 17, and `surface/runtime_identity.py` (17) retires: 433 → 441, about +8. A5b
is about −72 to −87 product LE once publish's `_publishing` decorator (about 8 LE) is counted, and
tests about +20 to +30; `L` falls from 463 to about 416 LE, and
`test_selection.py` (492 of 500) lands near 495 as its retargets wrap.
