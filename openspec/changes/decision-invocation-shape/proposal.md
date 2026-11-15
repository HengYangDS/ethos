# Proposal

## Why

The rule that a decision record holds no command invocation reads prose as a command. In
`repository/policy/references/commands.py` any later token that starts with a hyphen makes an
invocation, so `a - b` and `x -> y` qualify. Read in the released 0.2.0-beta.10 and reproduced
there with the installed function by a governed repository's session.

- In that repository 357 prose or heading lines of 47 decision records are flagged, 336 of them
  only for a spaced hyphen or an arrow.
- The result is `docs_decision_execution_content` on 42 of its records.

## What Changes

- A later token counts as an option only when it has an option's shape: one or two hyphens
  followed by a letter or a digit.
- A regression with the probe strings: a spaced hyphen, an arrow and a heading are no invocation;
  a real option still is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

One function and its test. It narrows a refusal, which the law freeze admits.

Owner: the release lead. Next action: write the patch and measure it. Read again: at the cut of
0.2.0-beta.12.
