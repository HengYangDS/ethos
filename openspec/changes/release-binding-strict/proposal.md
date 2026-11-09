# Proposal

## Why

The release binding's `[release]` table has one reader, the branch role policy, which reads
`mirror` alone. A governed repository's `version_source` and `tag_pattern` there are declarations
that nothing consults: the version comes from `VERSION` and the tag rule from
`[protected_refs] tags`. The paradigm reports neither, so a release-looking binding hides a
repository that declares no release, as web-ingestion-benchmark showed.

## What Changes

- The paradigm reports every key of `[release]` other than `mirror` as `release-binding`, and
  `ethos lane repair-paradigm --apply` deletes the key, or the table once it holds nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the release binding's `[release]` table declares only `mirror`.

## Impact

- `src/ethos/contracts/branch/roles.py` (the keys its reader consults, named once), the paradigm
  report and its repair handlers.
- The repair tests, whose release fixtures declare the two unread keys.
- Adopters: web-ingestion-benchmark carries both keys and drops them in its own lane; the other
  governed repositories declare `mirror` alone.
