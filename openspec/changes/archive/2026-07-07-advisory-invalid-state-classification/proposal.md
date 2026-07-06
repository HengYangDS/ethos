# Advisory Invalid-State Classification

## Problem

`ethos report` exposed advisory signals, but the advisory layer's
`invalid_states` projection stayed empty. That made non-blocking small signals
visible yet not reducible to the same kernel-derived invalid-state vocabulary as
required gaps.

## Change

Classify advisory signals through the existing invalid-state taxonomy inside the
advisory scorecard layer. The signal remains advisory and non-blocking; only its
read model gains the same failure-language projection used elsewhere.

## Capabilities

- `command-plane`: subject=advisory-invalid-state-classification; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=report; facet:authority=source,test,openspec,evidence

## Out Of Scope

- No new invalid-state category.
- No conversion of advisory signals into required gaps.
- No new command surface or truth store.
