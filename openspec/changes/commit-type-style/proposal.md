# Proposal

## Why

The paradigm's commit grammar admits ten types. It took them on 2026-10-15 as the types that the
five commit policies of that day all held; `spec` and `style` were in only some of them, and
their commits were to read as `docs` and `refactor`. The accepted requirement names the ten and
its first scenario rejects `style: reformat`.

Conventional Commits 1.0.0, which the grammar follows, fixes `feat` and `fix` and names
`@commitlint/config-conventional` for the others. That configuration's type list is the ten and
`style`, which it describes as changes that do not affect the meaning of the code.

One governed repository's migration lane holds eight signed commits with the type `style`,
made after the grammar landed. No command rewrites a commit's subject, so the lane's holder
would have to rewrite two weeks of history by hand. Six of the fourteen governed families with a
checkout on the releasing host have such subjects in their history; only this one has any that
the grammar judges.

The owner decided on 2026-11-19: the commit types may take `style`.

## What Changes

- `style` joins the paradigm's commit types. The set is the eleven of the conventional
  configuration.
- The requirement names the eleven. Its first scenario accepts `style: reformat` and rejects a
  `spec` subject; its scenario on a repository's own pattern names `spec` alone.

Not breaking: every subject that the grammar accepted is still accepted. No other type joins,
and `spec` stays outside.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the requirement "Commits follow one grammar and carry an SSH
  signature" names eleven types.

## Impact

`src/ethos/contracts/paradigm/paradigm.toml` (one list), two test modules, the contributing
guide's type list and the changelog. A governed repository whose commits the paradigm's grammar
judges needs no change; commits that were refused for the type alone become valid when the
release that carries this Change is bound there. A repository that declares its own
`subject_pattern` keeps that pattern until the field is removed.

Order: the owner's decision of 2026-11-19 on the commit grammar. It lands with the batch that
follows 0.2.0-beta.11, whose content is frozen.
