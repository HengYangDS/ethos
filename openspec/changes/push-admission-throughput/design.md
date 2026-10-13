## Context

The bounded reuse introduced on 2026-09-22 kept canonical member validation for up to 64 MiB of retained input. Its design measured a 1,704-member set at 5.49 s cold and about 0.2 s warm. The set has since grown past that bound, and an LRU scan larger than its capacity reuses nothing.

Measured on the accepted root (2,684 members, 280.0 MiB):

| Reads in one process | Read times (s) | Peak RSS |
| -------------------- | -------------- | -------- |
| Current 64 MiB bound | 19.3, 21.1     | 2.4 GiB  |
| 512 MiB bound        | 24.6, 1.2, 1.3 | 2.1 GiB  |

A repeated read holds the same decoded values instead of a second copy, which is why peak memory falls.

`_push_remote_ref_set_exact` gives the atomic exact-lease push a fixed 120 s. The repository's pre-push hook runs inside that deadline and re-derives the same push and proof admission that publication applied just before pushing.

## Decisions

1. Keep one byte-budgeted LRU keyed by exact member bytes, and keep oversized members validating without retention. Raise the budget to 512 MiB. ETHOS commands and hooks are short-lived processes, and a single read already materializes the whole set, so retention adds no new peak.
2. Build the cached validator through one factory with an explicit capacity. Reuse tests then exercise eviction and oversized members with small payloads instead of real 64 MiB inputs.
3. Measure each peer's admission immediately before its push. The push deadline is 120 s for transfer plus twice that measurement, because the hook repeats the measured work. A hung transfer still ends at that derived deadline.
4. Out of scope: each pushed ref still validates a repaired history separately inside the hook. Only non-fast-forward convergence of repaired history reaches that path, and the derived deadline now covers it.
