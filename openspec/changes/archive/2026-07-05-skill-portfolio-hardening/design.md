# Design

The portfolio remains five primary subjects: repository governance, change
lifecycle, skill portfolio, quality gates, and adoption profile. Hardening is a
measurement change, not an ontology expansion.

`validate_skill_markdown` now checks that provider-visible `SKILL.md` files keep
trigger descriptions concise and action-oriented, and that longer entrypoints use
progressive disclosure through `references/` or `scripts/`. This keeps skills as
thin procedures over repository truth.

`playbooks_report` now emits `portfolio_design` next to `portfolio_coverage`:

- duplicate exact `path_globs` are required gaps;
- overclaimed intent tokens are required gaps;
- each active record must route its primary subject and `changed-scope`;
- oversized packages are required gaps.

Command capabilities are counted but not treated as single-owner route truth,
because shared ETHOS commands are evidence affordances rather than skill
ownership. Exact path glob ownership is the MECE route boundary.

Repository-governance routes were narrowed so it no longer absorbs lifecycle,
quality, or skill-portfolio paths. This preserves `物遂其性`: each domain owns
its natural scale while the single kernel remains central.
