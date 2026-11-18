# Proposal

## Why

The owner directed on 2026-11-18 that every governed repository is optimised for performance and
that iteration gets faster, and ruled that this fix lands before 0.2.0 as a cost defect.

In a governed repository whose own tests are short, three gates are the proof: `source-format`,
`markdown-lint` and `config-quality`. On one governed checkout they took 140.5 seconds and
started 3,162 commands for 195 files. Two causes, both read in the gate code and profiled:

- A loop over files asked a question about the repository on every turn. The lookup of a tool's
  repository configuration lists the whole repository with two Git commands, and it ran once
  for each Prettier file in one gate and four times for each Markdown file in another.
- A repository with its own Prettier ignore file sent every Prettier file down the per-file
  path: one process to ask whether the file is excluded and one to render it for each
  configuration. `markdown-lint` rendered each Markdown file alone in every repository, although
  `source-format` had checked the same files in bulk in the same proof, and `config-quality`
  is the same function on the configuration files.

## What Changes

- The format gate lists the repository once for each report and passes the listing to every
  lookup that needs it.
- One process asks Prettier's own interface which named files the repository's ignore file
  excludes. The gate leaves those files alone and checks the rest in bulk, as it already did
  in a repository without an ignore file.
- `markdown-lint` takes its format verdict from the format gate's bulk path.

Not breaking: the same formatters judge the same bytes under the same configurations, and every
verdict and postimage is unchanged. One report differs: when a formatter refuses a file,
`markdown-lint` reports the refusal alone, where it used to list the drift found before it.

Measured on that checkout with both changes: 140.5 seconds to 8.7, 3,162 commands to 75. On
ETHOS's own tree: `source-format` 12.3 seconds to 5.5 and `markdown-lint` 36.1 to 4.7.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement changes, so `skip_specs: true` applies. Three tests hold the obligation: a
clean selection costs the same native runs at any size, with and without an ignore file, and
lists the repository equally often.

## Impact

`src/ethos/adapters/gates/formatting.py`, `tool.py`, `native/inputs.py`, a new script
`prettier-ignored.mjs` beside the Markdown adapter, and two test modules.
