# Design

## Context

See the [proposal](proposal.md). `authored_name_gaps` in `src/ethos/repository/paradigm/names.py`
judges every tracked carrier once, and `name_path_gaps` judges one new file's own name for prewrite
admission, with no repository access. The paradigm report returns its non-blocking facts beside
`gaps`, as it does for parameter `deviations`. The repository profile is a strict typed binding
that refuses unknown keys.

## Goals / Non-Goals

Goals:

- A name that an upstream contract fixes passes only on evidence that the repository tracks.
- Every admission is visible in the report with the manifest that evidences it.
- A declaration that the tracked manifests do not support is a gap, never a silent exemption.
- The whole-tree report and prewrite admission decide by the same evidence.

Non-Goals:

- A blanket exemption of a directory, a suffix or a name pattern.
- Any change to the kebab-case grammar, the fixed names or the vendored and generated marks.
- Validating a manifest against its own schema, which its owner does.
- A resource-structure rule; the structure design adopts this rule for resource names.

## Decisions

1. The declaration lives in the profile as `[[identifier_sources]]` rows with `manifests`, `keys`
   and `values`. The profile already declares the repository's own roots and record roots, and its
   strict model refuses a misspelled field.
2. `manifests` is one glob over tracked paths, matched by `repository_path_matches`, which already
   matches the profile's `openspec.material_paths`. A basename alone would also select an
   unrelated file of the same name elsewhere in the tree, so a basename is written `**/<name>`.
   No second matcher is added; in this matcher `*` also crosses `/`.
3. A key is a dotted path of exact segments, where `*` names every key of one table and an array
   of tables or of strings is read by element, so an array of strings holds one value per element.
   `field_values` in `repository/policy/references/declared_paths.py` already reads the paradigm's
   own declared path fields this way, so it becomes public and is reused. There is no recursive
   wildcard and no pattern inside a segment.
4. `values` names one of three readings and nothing is guessed from a value's shape: `whole` is
   the value itself, `dotted` is each dot-separated part, and `path` is each segment of a relative
   path and the stem of its file name before the first dot. An identifier is never empty and never
   holds `/`.
5. Evidence is global: some matched tracked manifest carries the identifier. A nearest-manifest
   rule fails the measured shape, where a data directory is evidenced by a manifest in another
   tree, a namespace level lies above its manifest, and fixture query files are evidenced by a
   catalog in a sibling tree.
6. A name is admitted when it, or for a file its stem before the first dot, equals an identifier.
   The rule runs only after every existing rule has refused the name, so no existing verdict
   changes when no source is declared.
7. Admissions are data in the report: `name_admissions` rows of `name`, `carrier` and `manifest`,
   beside `deviations`.
8. The guards use one new obligation, `identifier-source`, with two carriers:
   `<profile>:identifier_sources.<glob>:<key>` for a key that no matched, readable manifest
   carries, which covers a glob that matches no tracked file, and the manifest's path for one that
   does not parse as TOML, or as JSON when its name ends in `.json`. The `authored-name`
   obligation is not reused, because its carrier is a path to rename.
9. Prewrite admission passes the rule a reader that it calls only for a name that would otherwise
   be refused, so a repository without sources pays nothing and others pay one index listing per
   refused name. The reader takes the manifests that the index tracks, at their working-tree text,
   as the report does.

## Risks / Trade-offs

- A broad declaration, such as a glob over every manifest with a `*` key, admits many names. Each
  admission is listed with its manifest, and the declaration is a reviewed profile change.
- Evidence is by equality of strings, not by position, so an identifier admits its name anywhere
  in the tree. The measured shape needs this; the report shows where each admission applies.
- A new file whose manifest is not tracked yet is refused at prewrite. The author tracks the
  manifest first.
- A release older than this one refuses a profile that carries `identifier_sources`, so a
  repository adds the key only after it binds this release, and removes it before binding an
  older one.
- The report reads each matched manifest once per source that matches it.
