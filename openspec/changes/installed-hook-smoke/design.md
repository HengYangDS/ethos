# Design

## Context

See the [proposal](proposal.md). `local-install-smoke` runs `nox -s install_smoke`, which calls
`DeliveryPipeline.prove_install` and then `acceptance_effect.run`: it installs the selected wheel
into an adopter fixture under the acceptance's owned work tree and observes the package, and no
step runs a generated hook. The fix of `514136415` has a unit test that stands in for the shipped
resource; nothing exercises the real installed path in the product repository.

## Goals / Non-Goals

Goals:

- A runtime whose generated `pre-commit` refuses every commit in the product repository fails
  `local-install-smoke` before it can ship.

Non-Goals:

- The other hooks and adopter repositories, which the package acceptance already covers.
- Any commit, signature or network access: the step runs the hook alone.

## Decisions

1. The step clones the head with `git clone --shared --no-checkout`, sets the accepted branch to the
   runtime's source commit and the candidate to the head, and runs after `prove_shared_supply` on
   the archive's host-store pin, which `hook install --runtime` accepts only as the development
   identity of the accepted head. A release or dirty build records `not_qualified`.
2. The hook admits an edit only in a Work Lane whose lease holder is the committing actor and whose
   paths one Change covers, so the step starts a lane, stages a Change whose documents keep every
   template section beside its edit, and runs `git hook run pre-commit` with `ETHOS_ACTOR`,
   `ETHOS_CHANGE` and the locked Gitleaks on `PATH`.
3. Two cases: a conforming `.gitignore` edit is admitted, which is the case the incident broke,
   and a `.gitignore` led by a blank line is refused with `pre_commit_text_layout:.gitignore:1`.

## Risks / Trade-offs

- The step adds about 17 to 19 seconds to `local-install-smoke`, and a cold tool cache supplies
  Gitleaks offline.
- It costs 98 tools and 80 test line-equivalents, above the design's inferred caps: no equal dead
  code exists in `tools/`, and the duplicated runner it removes recovers 18 lines. The RC's tools
  room shrinks by as much, which the RC's tools review accounts for.
