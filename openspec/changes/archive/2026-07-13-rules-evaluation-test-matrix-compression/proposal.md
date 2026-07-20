# Rules Evaluation Test-Matrix Compression

## Why

The rules-evaluation test cluster repeats imperative fact envelopes and
coverage-only micro-scenarios across canonical and coverage files. The
repetition inflates executable test surface without adding independent behavior,
directly opposing the terminal source-budget objective.

## What Changes

- Declare stable rule-fact envelopes once through a compact immutable test
  fixture and project complete snapshots from it.
- Fold helper-edge scenarios into the canonical rules test surface and delete
  superseded coverage-only bodies and imports.
- Prefer a pytest matrix only when its measured representation is smaller than
  the direct semantic test; do not add callable adapters merely to label code
  declarative.
- Preserve fail-closed result, gap, waiver, and schema contracts.

## Out Of Scope

- Product rule-evaluation semantics, rule declaration format, policy exceptions,
  and command behavior.
- Any reduction in required branch coverage or the 100-percent test floor.

## Capabilities

- `quality`: subject=rules-evaluation-test-compression; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence
