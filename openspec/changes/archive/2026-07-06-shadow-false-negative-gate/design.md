# Design

Shadow parity compares embedded fallback command outputs with external ETHOS
product command outputs. The retirement-critical invariant is superset safety:
external ETHOS may be stricter, but it must not miss embedded blocking gaps or
turn them into advisory-only signals.

The gate operates at two layers:

1. Runtime shadow comparison records `false_negative_count` and per-command
   `false_negative_gaps` whenever embedded `required_gaps` are absent from
   external `required_gaps`.
2. Tracked parity evidence validation requires the false-negative semantic
   dimension and an explicit zero false-negative count before evidence can close
   adopter parity.

Advisory external additions remain non-blocking accepted differences. Embedded
blocking gaps missing externally are blocking `shadow_false_negative:<command>`
required gaps.
