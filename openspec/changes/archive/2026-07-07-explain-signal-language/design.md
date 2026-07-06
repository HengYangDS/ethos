# Design

The core taxonomy projection keeps the existing `gap` field for compatibility and
adds `signal` plus `kind = "invalid_state_projection"`. The human meaning and
next action use neutral gap-or-signal language. This avoids a new command, a new
truth store, or a second taxonomy while preserving compatibility for existing
callers.
