---
subject: ethos:decision:branch-names-declared
role: decision
state: canonical
decision_id: DR-0032
decision_status: accepted
date: 2026-11-18
relations:
  current_owner: ../../openspec/specs/repository-paradigm/spec.md
  updates: DR-0012
---

# DR-0032: Branch Roles Are Fixed; Their Names Are a Repository's Declaration

Purpose: preserve why the paradigm fixes the branch roles and no longer fixes their names, what a
repository may declare, whose declaration governs, and what stays the paradigm's.

See also: [DR-0012: Repository paradigm](dr-0012-repository-paradigm.md), whose item on branch
conventions this record updates; the [product design
contract](../governance/product-design-contract.md), which already says that a repository maps
physical names to roles; and the [study of branch
names](../research/change-surfaces/branch-names.md).

## Context

DR-0012 put "commit, branch and release conventions" into one paradigm on 2026-10-14, after an
inventory of thirteen governed repositories found three branch-prefix vocabularies among other
incompatible encodings. It rejected "Per-repository conventions" "because they recreate the
drift this decision removes".

One day later the names became constants of the product. The commit that did it gives an
engineering reason: while ETHOS read the names from a table of the workspace binding, a rename
meant teaching every command which table owned the names, the incumbent's or a Work Lane's own.
The accepted requirement followed on 2026-10-19: the paradigm "SHALL fix the branch role names",
and ETHOS reads nothing from the retired table.

The contract was not changed with it. It kept saying that names are mapped by the repository. On
2026-11-18 the owner stated the product's meaning in his own words, `是的，角色固定，名字由仓库声明，范式给默认值`:
the role model is fixed, a repository declares its names, and the paradigm gives the defaults. A
study of the same day found no common standard for branch names across the practices it read, so
a fixed name is a preference and not a norm.

## Decision

1. The paradigm fixes the five branch roles (release, accepted, candidate, Work Lane, proposal),
   the one carrier that names them, the validity of a name, and a default name for each.
2. A repository has exactly one name for each role: the one its trusted base declares, else the
   default. A declared name is a value the obligation asks for, as the release mirror is. It is
   not an exception, and DR-0012's sentence "A repository cannot declare an exception" stands.
3. The declaration that governs is the one committed at the head of the accepted branch that a
   clone's anchor names. The anchor is held outside every tree. No Work Lane's tree and no
   uncommitted text decides the names that judge it.
4. A name is valid when it is a well-formed ref name, the five are distinct, both prefixes end
   in a slash and neither lies inside the other, no exact name lies under a prefix, and none is
   the word that marks a detached head. A declaration that a reader cannot honor is refused; it
   never selects the defaults.
5. A rename is a Change that lands under the old names and is carried out as one ref
   transaction at accepted closeout. Removing a declaration is a rename to the defaults.
6. Sameness of names across repositories is no longer an obligation of the paradigm. The
   product reports a repository's difference from the defaults as information. A fleet that
   wants one vocabulary keeps that as its own rule, with its own carrier and reader.

## Alternatives Rejected

- **Names fixed for every repository (the state since 2026-10-15):** rejected because it
  contradicts the contract, makes an arriving repository rename its default branch on every
  forge before it can be governed, and fixes a preference where no common standard exists.
- **Names declared, with the declaration of the tree at hand governing:** rejected because a
  Work Lane could then rename its way out of protection. The trusted base governs, as for every
  other policy.
- **Only the release and accepted names declared, for good:** rejected as an end state. It is
  the first step in which a declaration is honored, because those two are the names a
  repository arrives with; the candidate name and the two prefixes follow on a stated need.
- **A per-repository table in the workspace binding, as before 2026-10-15:** rejected. The
  retired table is not revived; the names sit in the release binding beside the release mirror
  and the protected tag patterns, where every released runtime refuses a key it does not know.

## Consequences and Boundary

- Why this is not the drift that DR-0012 removed: that drift was several incompatible encodings
  of one thing, each with its own reader. Here the roles, the carrier, the reader, the validity
  and every default are the paradigm's and the same in every repository; a value differs.
- The names become declarable in three steps, each after 0.2.0: one reading path that still
  refuses every declaration that differs from the defaults; then the release and accepted names,
  with the general rename; then the candidate name and the two prefixes, on a stated need.
- The requirement "Branch roles and Work Lanes use the standard names" changes with each step
  and states each step's refusals. Until a step ships, the names stay fixed in behavior, a
  repository with other names renames them first, and a release's entry names that divergence
  from the contract among its known defects.
- The fixed names of any release before those steps are no compatibility promise.
- The contract's meaning stays. Its words change where they name the default names as if they
  were the only names, and where they give the mapping to profiles.

## Evidence and Revisit

- The owner's decisions of 2026-11-18: the direction, the six items above, and the three steps;
  and the review of the design by three seats (contract and law; admission and security;
  adopters, agents and release), each accepting it after changes.
- Read on the release head of that day: the role reader takes names from the paradigm alone; a
  key under the release binding that no reader consults is a blocking gap, so a released runtime
  refuses a repository that declares a name it cannot honor; thirteen of fourteen governed
  repositories read on the releasing host held the default names.

Revisit when a governed or arriving repository states a need for another candidate name or
another prefix, and when the general rename has run once on a forge.
