# Design

This is a projection-boundary repair only. Cyclopts derives the positional
metavar from the Python parameter name, so the smallest durable fix is to name the
argument `gap_or_signal` and keep the internal compatibility contract unchanged.
No new command, truth store, payload field, or lifecycle state is introduced.
