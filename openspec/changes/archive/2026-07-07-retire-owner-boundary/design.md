# Design

The fix preserves the existing Work Lane model. A landed lane can be retired only
when the lane is merged, clean, HEAD-bound, and the runtime actor matches the
active lease owner recorded in `.ethos/state/state.sqlite`.

The actor is supplied through `ETHOS_ACTOR`, which is runtime context, not a new
truth store. The lease remains the authority evidence. This keeps the command
surface small while preventing a reader of foreign Work Lanes from implicitly
becoming their owner.
