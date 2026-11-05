# Design

## Context

See [proposal.md](proposal.md). The owner's direction on 2026-11-05 is to fix a defect class at its
existing owner, never with a parallel check, and to remove every instance in the same Change. The
residue audit of `ea72a93bb` supplies the instances and the owners; its tables are in the ETHOS
session's record, so the decisions are restated here.

## Goals / Non-Goals

Goals:

- Each existing owner catches the dead carriers in its own domain, and its test shows the red run
  on the real instance.
- Every listed instance is removed or kept with a recorded consumer.

Non-goals:

- Consolidating parallel implementations, such as the closure's own Git reads, into one process
  owner. That belongs to Change `one-process-owner`.
- The audit rows recorded under Follow-ups below.

## Decisions

1. **Reference closure owns declared paths.** `references/declared_paths.py` holds each field that
   `REPOSITORY_PATH_FIELDS` names to content at `HEAD`, read from `git ls-files`:
   - a tracked file;
   - a directory that holds a tracked file other than a README;
   - a glob that matches such a file, with the product's `path_matches`.

   A dead value is `semantic_declaration_missing:path:<value>:<declaration>`, and it blocks the
   product audit as every closure finding does.

2. **The declaration owner names the path fields.** `REPOSITORY_PATH_FIELDS` sits beside the
   declaration table in `references/carriers.py`. It is a positive contract: each declaration kind
   lists the fields that name the declaring repository's own content. The packaged gate registry,
   the paradigm and the artifact topology are shipped catalogs that name adopter paths, so they
   have no row. The rules binding joins the declaration table as kind `rules`.

   A generic walk over every slash-bearing value was rejected. In adopter profiles it would read
   output paths, template strings and external origins as repository paths: aigw-cli, alphasim,
   architecture-publisher and the proxy all have such values.

3. **Prefix matching follows content.** A reference to a directory consumes the retired files
   under it only while that directory holds no other content. Deleting one file under a live
   directory never makes references to the directory consumers. Deletion admission applies the
   same rule to a script input that names a directory, judged against the patch's effective files.
4. **README disposition covers every tracked README.** Outside the documentation root, only the
   `docs_readme_without_children` rule applies, under the same gap code. The local-route rule stays
   a documentation-navigation rule (DR-0011): a package README outside `docs/` may be prose
   without links.
5. **The surfaces schema is closed.** It refuses unknown top-level keys and unknown surface
   fields. The surface fields are `name`, `purpose` and `carrier`.
6. **Format roots must admit content of their format.** A root must hold a tracked file of the
   format it admits, not just any file. The JSONL root `build/` can never hold a tracked file, so it
   goes, leaving `jsonl_allowed_roots = []` with the same effect: tracked JSONL is refused. The
   `.config/ci/` YAML root has held no YAML since `2e07e1dfc` (2026-09-20), when CUE became the
   sole hosted projection source.
7. **`packages` stays.** It is in `PRODUCT_SURFACES`, the artifact topology and the topology
   document. All three are catalogs that apply to every adopter, and di-effect (3,365 tracked files)
   and alphasim (939) track `packages/`. A catalog row with adopter consumers is not a dead
   carrier.
8. **The skill reference names the current owner.** The test-attempt isolation paragraph now
   names `behavior_report` in `src/ethos/adapters/gates/python_quality.py` and describes what it
   does: a fresh owned scratch directory for each attempt, with the source tree bound before and
   after. The package digest is recomputed with `compute_skill_package_digest`.

## Risks / Trade-offs

- **Adopter reports.** An adopter's closure report can gain `semantic_declaration_missing`
  findings for dead rule globs; alphasim's `sql/**` is one. Adopter closure is reported beside the
  audit and never changes its verdict.
- **Non-carrier survivors.** Deletion admission judges a directory input against the patch's
  effective reference files. A directory that keeps only non-carrier files, such as `.cue` or
  images, after a patch deletes its carrier files would be refused. Not observed in any governed
  repository.
- **An unobservable index** (no Git repository) skips the declaration check rather than reporting
  every path dead.

## Follow-ups

These come from audit rows 9–11, 13 and 14. Each is named with its next action:

- **Schemas with no reader.** Five kernel schemas are listed only in `repository/audit.py`:
  `assistant-projection`, `provenance`, `lane-lease`, `mutation-decision` and `host-capability`.
  `result` is read only by tests, and `independent-verification-receipt` is named only in docs.
  Next action: a schema-binding Change that binds a reader to each or removes it.
- **Gate fields read only by tests.** `network_policy` and `version_source` in the gate registries
  are read only by tests. They go into the same Change.
- **`shell-lint` with no subject.** ETHOS tracks no `*.sh`, so the gate, its session, its pre-commit
  hook and `.shellcheckrc` have nothing to check in ETHOS. The rows that ship to adopters stay.
  This moves to Change `one-check-one-gate`.
- **Retired ETHOS roots named in product code**, such as `tools/ci/scripts` and `evidence/`, and
  guards for retired names. The owner decides per name whether it is a catalog entry or residue.
