# Tasks

## 1. Internal Skills

- [x] 1.1 Mark every tracked `SKILL.md` internal and record the four maintainer packages' new
      digests. Done when the test that reads every tracked `SKILL.md` fails before the change and
      passes after it, and the skill portfolio reports no gap. Evidence: e2780ea39 marks the five
      tracked `SKILL.md` files and records the four new digests, computed with
      `compute_skill_package_digest`. `test_every_tracked_skill_is_internal_to_skills_sh_discovery`
      failed before the change on the first maintainer Skill (18:23:07 to 18:23:12) and passed after
      it (18:24:27 to 18:24:32); the skill portfolio reported pass with no gap, and the 18 targets
      that read Skills or the packaged guidance passed (425 passed, 18:24:57 to 18:26:49).
- [x] 1.2 Say why in `.agents/skills/README.md` and add the Changed line to `CHANGELOG.md`. Done
      when Prettier and Vale accept both files. Evidence: e2780ea39 adds the README bullet and the
      Changed line; Prettier and Vale accepted both in the commit's checks.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against d1be14275 with 0 findings (18:30:03 to 18:30:08),
      and readiness passed 28 gates at d1be14275 with the 6 heavy gates left to the proof (18:30:20
      to 18:31:43).
