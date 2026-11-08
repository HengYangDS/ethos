# Design

## Context

The root commands parse their own flags (`src/ethos/surface/cli/root/`), each operation selects its
mode by first match (`application/land/operation.py`, `adoption.py`, `publication/operation.py`,
`proof/operation.py`), and the MCP tools call the same operations with whole signatures
(`surface/mcp/server.py`); `next` classifies root argv with token rows in `contracts/admission.py`.
The operation catalog (archived `rc-plan`, Appendix A) declares each mode as one entry. The design
was reviewed twice: `build/runtime/work/catalog-root/decisions-draft-2.md`, its reviews 1 and 2 and
the settlement appended to the draft; `closeout-rebinding-fence` made the closeout preview read
only.

## Goals / Non-Goals

Goals:

- One declaration of each root mode, selected the same way by every transport, refusing a request
  that names no mode or sets a field its mode does not take.
- Usage and delivery failures as structured results with stable exits.
- `next` and help derived from the same entries.

Non-Goals:

- Group commands (lane, hook, attestation, host), the complete `binding`, `inputs`, typed steps,
  execution handles, emitted `delegation` and per-entry MCP tools, which are A6, A7, A10, A12 and
  A16's.
- One implementation per operation and the root import edges (draft 2, Decision 10), which are
  A5b's: here a selected request reaches today's operation, whose first match then picks the same
  mode, since every field its operation does not take is at its default.

## Decisions

1. **One declaration per command.** `ethos.contracts.operations` holds, in one module per command,
   the frozen request model with keyword-only, described fields, the flag spellings and each
   operation: ID, selector predicates, request fields, effects, destructiveness, authorization kind
   and exit kind. The model sits in the kernel, not the application, so the kernel's argv reading
   and the CLI share one field list; Cyclopts takes the spellings through a name transform.
   `ethos.application.catalog` maps each command to its application operation.
2. **One selection.** `select_operation(command, fields)` returns `Selected(operation, request)` or
   `Refused(result)`. The CLI adapter calls it on the parsed request before it runs anything, and
   `catalog_operation` calls it before each of the six root operations, which keep their names and
   keyword signatures, so the SDK, MCP and the CLI refuse alike; `invoke` runs a selected request.
3. **Field roles.** Each union field has one role per entry: selector predicate, request field or
   refused. The partition is total and disjoint over every assignment of a path's selectors, which
   the table test enumerates; unmatched selector assignments and refused fields exit 2 with
   `command_operation_unmatched:<path>` or `command_field_refused:<field>`, and `data.selection`
   names the failed predicates or refused fields per entry.
4. **One parser.** Union fields are keyword-only, Cyclopts' own errors map to
   `command_usage_invalid:<path>` (exit 2, JSON under `--json`), and an undelivered result exits 3
   for every command; `_require_live_next` checks that `next.form` equals its parse's selection.
5. **Entries.** I §3's 29 rows with review 1's amendments: `land.closeout.preview` reads only;
   `proof.run` is `r, x, le`; formation apply is `hw`; kinds stay `authorize` and `none`, and
   `delegation` joins the authorization vocabulary without being emitted.
6. **Exits per entry.** `observe` exits 0 on every verdict and `verdict` 0 only on `pass`; a publish
   probe exits 1 on `unknown`; an invalid profile follows the selected entry's exit kind.
7. **`next` for root argv.** The kernel classifies root argv through the selected entry; an
   unselected root argv is `opaque`, destructive and `human`; the root rows of the step table
   retire; `next.form` names the entry. Typed steps for the golden path's builders move to A7 with
   A6's, as an owner ruling.
8. **Help.** `ethos --help --json` prints the root catalog as one schema-3 result within a declared
   `help` payload budget, 48 KiB for the 40,755 bytes measured; text help lists each operation with
   the flags that select it. A field keeps one description, which names its meaning per operation
   where it differs, such as `--expect-head`.
9. **No direct publish apply.** `ethos publish --apply` without `--receipt` matches no entry, in the
   CLI and the MCP `publish` tool alike.
10. **Retired checks.** The checks that only refused a request no operation now takes retire with
    their codes; a check that still guards an accepted field, such as the local-source proof's,
    stays.

## Risks / Trade-offs

- Breaking for callers that relied on ignored flags or first-match refusal codes; before 1.0 the
  CHANGELOG names every retired code and the migration.
- A larger product: about +450 to +650 effective lines, within the product budget.
- Until A5b, a selected request reaches an operation that still selects by first match; the table
  test and the selection guard keep the two in step.
- One union model per path couples the entries of a command; the table test is the guard that keeps
  them total and disjoint.
