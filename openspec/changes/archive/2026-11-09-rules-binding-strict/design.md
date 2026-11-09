# Design

## Context

The workspace binding conformance reads `paradigm.binding.workspace_tables` and reports every other
top-level table of `workspace.toml` as `workspace-binding`, whose repair deletes the table's header
blocks and the comments directly above them, and deletes the file when nothing remains. The rules
readers are `resolve_profile_stack` (`profiles`), `configured_rules` (`rule`) and
`parameter_resolution` (`paradigm`, the declared parameters and their reasons). The record binding
retires `[artifacts]` in two phases, roots first, and `binding-restatement` moves a
`[quality.code_size]` into `[paradigm.size]`.

## Goals / Non-Goals

Goals: report and repair every `rules.toml` table that no reader consults, with the workspace
binding's mechanism.

Non-Goals: the contents of `[profiles]` and `[[rule]]`, which their readers validate; the record
binding's two phases; the deferred repository families, which keep their bindings until their own
migration.

## Decisions

1. **One declaration names the admitted tables.** `[binding]` in the paradigm declaration gains
   `rules_tables = ["paradigm", "profiles", "rule"]` beside `workspace_tables`, and
   `BindingFileSet` carries it, so the readers and the conformance check name one list.
2. **The rules binding mirrors the workspace binding.** A rules conformance check reads the tracked
   `rules.toml`, and for each top-level key outside `rules_tables` reports `rules-binding` at
   `<carrier>:<key>`, with the repair "remove [<key>]; no reader consults it", except an
   `artifacts` table and a `quality` table that still holds `code_size`. A key that is not a table,
   `artifacts` and `quality` included, is reported, and like the workspace binding's bare value it
   stays report-only, because the repair deletes only header blocks. A carrier that does not parse
   is the rules readers' own gap, as now.
3. **The repair is the unread-table repair.** `rules-binding` maps to the existing handler that
   deletes an unread workspace table; it keeps the repair only when the result parses as exactly
   the binding without that table, and removes a binding left empty.
4. **Tables with their own move stay with it.** `[artifacts]`'s roots must reach the profile
   before the table may go, which the record binding orders. While `[quality]` holds `code_size`,
   `binding-restatement` reports it and has no repair, so deleting the table would drop the value
   before it is restated in `[paradigm.size]`; the table is reported as `rules-binding` only once
   `code_size` is gone.

## Risks / Trade-offs

- A repository that documents conventions in such a table loses that text from `rules.toml`; the
  text belongs in its documentation, which the repair does not write.
