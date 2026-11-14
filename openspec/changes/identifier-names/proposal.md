# Proposal

## Why

The authored-name rule of the repository paradigm judges every tracked file and directory name:
lowercase kebab-case, a name that an ecosystem or tool fixes, or a directory that holds a module.
Its only way out is to mark a path vendored or generated in Git attributes. Its premise, that every
other tracked name is the repository's to choose, is false for one real shape: an upstream data
contract fixes an identifier, the repository must spell it as a file or directory name, and the
repository's own tracked manifest repeats it as a value.

Measured in one governed repository that packages data products: 133 such names, 105 directories
and 28 files. Resource directories are named by the identifier that a product manifest declares and
by the parts of the namespace that a bundle manifest declares; data directories by a product's raw
name; query files and shared query directories by the paths and query names that the manifests
declare. Those files are authored there, so marking them vendored or generated would be a false
declaration, and the paradigm's deviation mechanism covers integer parameters only. The audit can
therefore never reach zero, and a proof requires a passing audit, so no proof can run in a
repository of that shape.

This is a coverage defect of the name rule, so the name rule's owner fixes it. The Change is the
one defect fix that the 0.2.0-beta.11 batch admits beside its planned rows, and it lands in that
batch before `gap-codes`, which registers the gap code that it adds.

## What Changes

- A repository profile may declare `[[identifier_sources]]`: a glob of tracked manifests, the
  dotted keys in them that hold identifiers, and how a value is read: whole, as dot-separated
  parts, or as a relative path whose segments and file stem each count. An array holds one value
  per element.
- A name outside kebab-case is admitted when it, or for a file its stem before the first dot,
  equals an identifier that a declared key of some matched tracked manifest holds. Every other
  name is judged as before, and the vendored and generated marks stay.
- The paradigm report lists every admission under `name_admissions` with the name, its path and
  the manifest that evidences it.
- A declaration without evidence admits nothing and is a gap,
  `repository_paradigm_identifier_source`: a declared key that no matched, readable manifest
  carries, which includes a glob that matches no tracked file, and a matched manifest that does
  not parse.
- Prewrite admission judges a new file's name by the same evidence.
- A release older than this one refuses a profile that carries the new key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: MODIFIED `Repository-authored names use lowercase kebab-case`.

## Impact

`src/ethos/repository/profile.py`, `src/ethos/repository/paradigm/names.py`,
`src/ethos/repository/paradigm/report.py`, `src/ethos/adapters/admission/paths.py`, one public name
in `src/ethos/repository/policy/references/declared_paths.py`, their tests,
`docs/architecture/adoption-profiles.md` and `CHANGELOG.md`. ETHOS declares no identifier source
and gains no gap. On the measured repository the rule admits 132 of the 133 names with a
declaration of five sources; the one that stays a gap is a fixture file that no manifest names on
purpose.
