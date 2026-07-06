# Design

`ethos report` now collects explicit advisory signals from known governance
owners: OpenSpec shape audit, claims, and playbooks. The collection is explicit
rather than recursive so provider payloads do not become accidental truth. The
scorecard exposes `advisory_gap_count` and an `advisory_signals` gap layer.

`ethos orient` reads those report fields and surfaces advisory counts/items in
its readiness packet and concise human summary. The signals remain non-blocking;
required gaps continue to own transition refusal.
