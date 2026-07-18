# Design

The fix keeps the historical planning records in place but changes their front
matter state to `archived`, then records the closeout boundary in evidence. This
preserves the planning context while removing it from active work surfaces.

The plans index gains an `Archived Plans` section so readers can distinguish
current product plans from completed historical planning records. The closeout
claim points to this archived OpenSpec carrier because active claims require a
tracked carrier path, even for documentation-residue closeout.
