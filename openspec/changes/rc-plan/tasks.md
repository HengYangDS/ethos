# Tasks

## 1. Dependency order

- [x] 1.1 Insert the section `0.2.0 Release Candidate Order` into
      `docs/plans/terminal-governance-product-design.md`, after the paragraph that ends "not a queue
      to replay." and before `### Immediate Dependencies`. Done when the section names the eight
      families of design Decision 2 in that order, cites this Change's design by name, and Prettier
      and Vale pass on the plan. The section `0.2.0 Release Candidate Order` now sits before
      `### Immediate Dependencies` in the terminal plan, names the eight families of Decision 2 in
      order and cites this Change; Prettier and Vale passed at commit `9f9875808` (20:30:22).

## 2. Defect register

- [x] 2.1 Retire the defect register `build/runtime/work/beta2/essential-fixes-20261105.md` into
      design Appendix H. Done when each of its 30 rows and each item deferred under rows 21 to 24
      has exactly one disposition there: an owner Change of Decision 2, a 0.3.0 or host owner, a
      closing commit that is an ancestor of `dev`, or a withdrawal. Appendix H gives each of the 30
      rows a disposition, checked at 20:3x against the register headings: closing commits on dev,
      owner Changes of Decision 2, 0.3.0 or host owners, and row 10 withdrawn by the owner on 11-05;
      the deferred items under rows 21 to 24 are mapped with their rows.
