## Decision

Remove the product-root conditional in both commands. The existing result
envelopes already carry lifecycle required gaps, so no code-correctness gate or
second command plane is needed.

## Boundary

OpenSpec owns lifecycle artifacts. Superpowers and other method packages may
assist work but cannot carry lifecycle authority. Material scope admission is a
separate follow-up Change so it cannot dilute this universal correction.
