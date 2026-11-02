# Tasks

## 1. System contracts

- [x] 1.1 Delete `system/formats.toml`, `system/routing.toml`, `system/evidence-boundaries.toml` and
      their schemas, and keep `surfaces` as the only system contract. Done when
      `system_contracts_report` passes with one contract and no test, document or policy row names
      a deleted file. (The report passes with `surfaces` only; `git grep` outside archived Changes
      and the changelog finds no deleted name; the 48 affected test modules pass.)

## 2. SVG validation

- [x] 2.1 Delete the `svg-format` gate and the `svg_lint` session, and validate `svg-assets` with the
      shipped `source-format` gate. Done when the full proof set lists no `svg-format` and the
      tracked SVG files pass `source-format`. (The full set lists no `svg-format`; `source-format`
      selects all 6 tracked SVG files under `svgo` and passes them.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
