# Design

## Context

See the [proposal](proposal.md). A gap is a string whose code is the text before its first colon.
The refusal helpers of `src/ethos/contracts/outcome.py` take any string, `outcome_of` turns any
other error's message into a gap, and nothing registers the result. The census of 2026-11-14
(kept with the Change's preparation, outside this repository) reads 1,552 codes at 2,228 sites:
940 are a literal at the site, 471 are composed from a literal prefix, a colon and a value, and
615 exist only where a value flows into a gap position, which no syntactic rule bounds. Three
small tables already hold a few codes: the remediation if-chain, the artifact topology prefixes
and the 20 paradigm obligations. Ten exit sites exist in six files, and the exit kinds are already
declared as the observability of an operation (`observe`, `verdict`, `process`), but the numbers
are literals in one module and prose in the specification.

## Goals / Non-Goals

Goals:

- One closed vocabulary that a diff shows, a two-way test that keeps it closed, and one exit table
  that the CLI exits by and that help prints.

Non-Goals:

- Any exit number change: the `host run` refusal keeps 1 and the awaiting-archive block keeps 1.
- Typed next steps, command builders or catalog conformance fixtures.
- A run-time refusal for an unregistered code; a missing row must not turn a block into a crash.
- One-line meanings for every row: `meaning` is optional, and only 14 rows state one here.

## Decisions

1. **The table is packaged data beside its loader.** `src/ethos/contracts/codes/gaps.toml` sits
   beside `gaps.py` as `contracts/artifacts/topology.toml` sits beside `topology.py`; the wheel
   takes the package tree, so `pyproject.toml` needs no force-include. One sorted inline-table row
   per code: `owner` is the lowest common package that raises it, `detail` says what follows the
   colon of a composed name, `meaning` is present where the name does not say it, `repair` is the
   fixed next step where one exists, and `reserved = true` marks a declared name nothing raises.
   A `[family]` table lists the 41 prefixes of names assembled from parts, including the 11
   artifact-topology prefixes; a member of a family is registered without a row.
2. **The loader is the only reader, and it is standard library only.** `gaps.py` imports
   `tomllib`, `functools` and `importlib.resources` and reads once. `gap_code`, `registered`,
   `record` and `repair_for` are the whole surface; an unregistered code returns None and an empty
   repair rather than raising. No hook-path module imports it yet, so `pydantic` and `cyclopts`
   stay out of its reach by construction.
3. **The static test reads the tree as it finds it.** `tests/architecture/test_gap_registry.py`
   walks `src/ethos` for a literal, or the literal head of an f-string, that reaches a refusal
   helper or a raised `ValueError`, `TypeError` or `RuntimeError`, directly or through the one
   local or module constant bound before it, and requires a registered code; a prose literal at
   such a position counts under a ceiling of 127 that only falls. The rule is exact for 934 codes
   of the census. It also reads the second member of each pair in a literal table that a loop or a
   comprehension reads under the name `gap`, directly or through the one local bound before it (99
   sites); at the batch's stacked head that form alone held 47 unregistered codes. The remaining
   ones reach a gap position through data, where the plan measures no bounded rule; the test does
   not approximate them.
4. **The runner guard is the dynamic half.** `tests/support/ethos_cli_runner.py` checks each
   in-process result's `required_gaps` after the run and fails with
   `unregistered_gap:<codes>:<argv>`; it covers exactly the codes a test produces, without a
   frozen count of the tree. It found three codes the census did not shape into a row
   (`command_field_refused`, `command_operation_unmatched`, `command_usage_invalid`), which are
   rows now.
5. **The exit table lives in the kernel beside the exit kinds.** `ExitRow` and `EXIT_CODES` in
   `contracts/operations/declaration.py`; `output.py` exits by kind, help publishes
   `data.exits`, and an architecture case refuses a numeric `SystemExit` argument anywhere under
   `src/ethos/surface/`. `refused` is 125 and reserved: the `host run` refusal flip and the
   awaiting-archive exit are successors, named under Risks.

## Risks / Trade-offs

- **Successors, in order of prerequisite.** `host-run-refusal-exit` (beta.12) flips the `host
run` refusal to 125; it is a Breaking change and needs its own caller repair. `typed-steps-rest`
  (beta.12 or beta.13) types the 168 builders and 226 sinks; it needs A7's typed producers, whose
  request models are `pydantic` models, so a hook-path producer needs a plain value first.
  `conformance-fixtures` (beta.13 or A17) needs the installed build and a catalog-driven fixture
  set.
- The count is not closed: 324 bare and 55 prefixed candidates outside the census positions are
  untriaged; a row is added when a site or the guard proves it. A code that a function returns as
  a bare string and a caller places among the gaps meets no static rule: 45 such codes are rows
  from one triage of 81 returned literals, and a later one is found only when a test produces it.
- The static test is exact for about 60 percent of the codes; a composed name whose prefix ends
  the literal part registers as a fragment family, so a new member passes without a row.
- Land last in the batch: `provider-ids`, `ci-commit-trust` and `hook-install-converge` add or
  move codes, and each must carry its row.
