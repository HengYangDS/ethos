# Design

## Context

See [proposal.md](proposal.md). One paradigm pattern serves commit admission (commit messages),
release admission (tag messages) and ETHOS's product boundary, and ETHOS's Gitleaks rule carries
the same string for staged and tracked scans.

## Goals / Non-Goals

Goals:

- Loopback and link-local literals pass every check that serves adopters.
- ETHOS's own product surfaces refuse every form the old pattern refused.

Non-goals:

- The peer-identity scope, record roots, markers and the redact verb (`peer-identity-records`).

## Decisions

- **Remove the alternatives at the source.** The paradigm pattern drops `127`, `169.254`,
  `fe[89ab]` and the quoted or bracketed `::1`. The Gitleaks rule carries the same string, and its
  keywords drop `127.`, `169.254`, `fe8`-`feb` and `::`.
- **Keep the refusal verbatim on product surfaces.** A URL-only pattern would catch 6 of the 20
  forms the old pattern refused (independent review, measured). The catalog therefore keeps the
  removed alternatives exactly as they were, as its own pattern beside the `localhost` pattern.
  ETHOS's surfaces hold no such literal today.
- **Joined fixtures.** Tests build loopback and link-local literals from joined parts, because tests
  are product surfaces and the staged scan judges a commit under HEAD's policy.

## Risks / Trade-offs

- `paradigm.toml` is packaged data, so the two runtimes' plans are compared before landing.
