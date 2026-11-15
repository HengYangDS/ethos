# Proposal

## Why

`release-acceptance` makes `ethos publish` refuse a release tag while the release policy report
holds a required gap, and it limits that refusal to the repository that declares the ETHOS product
profile. The report was written for the product: it requires a Python project whose version is
dynamic, release tags that are exactly `v*`, the host profile's surfaces and one attestation
format. A governed repository of another shape fails it. `release-acceptance` measured a root that
declares `v*` tags and holds every required release file and no Python project: its role policy
report passes, and the product report gives three gaps.

For a governed repository the refusal would be a new refusal of a tree that passed its
predecessor. DR-0029 admits such a rule only when an earlier release reported it and the refusing
release ships its repair. No release has reported these gaps to a governed repository.

## What Changes

- A governed repository's publication of a release tag reports the release policy gaps that apply
  to its shape, for one release, before any refusal. The report blocks nothing.
- The gaps are sized first: which of the product report's checks hold for every governed
  repository, and which are the product's own.
- A refusal, if the reports support one, is a later Change that ships each gap's repair.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The release configuration's report, the publication inspection and the distribution
specification's requirement on what public channels consume. It adds no rule for a governed
repository while it reports.

Owner: the release lead. Next action: size the report with the first reports after the rule row.
Read again: after 0.2.0.
