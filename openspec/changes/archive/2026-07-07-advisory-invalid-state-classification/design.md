# Design

The advisory layer already carries non-blocking signal strings. The fix simply
passes those strings to `invalid_state_projection` rather than projecting an
empty list. This preserves boundary separation: blocking status is still carried
by `required_gaps`, while advisory signals gain taxonomy visibility for diagnosis
and UX.
