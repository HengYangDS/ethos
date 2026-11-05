# Proposal

## Why

ETHOS publishes a governed repository to more than one Forge peer. A private-class network address
in shared content tells every peer, the public ones included, where another peer or other internal
infrastructure lives. A remote URL in a test, a merge message or a tag message is enough. Nothing in
ETHOS refuses such an address today: the secret scan has no rule for it, and commit admission reads
only the subject line, so a message body or a tag message passes unchecked.

## What Changes

- The paradigm declares one structural pattern for private-class network addresses: RFC 1918 and
  RFC 4193 literals, loopback and link-local literals, and the private-use names `.local`,
  `.internal`, `.lan` and `.home.arpa` in host position. The pattern names address classes, never
  an address, so documentation ranges, reserved example names and the declared public distribution
  identity pass.
- ETHOS's own Gitleaks configuration carries the same pattern, so its staged scan and its scan of
  the tracked files refuse a private-class address. Neither scan reads history.
- Commit admission applies the pattern to the whole message: in the `commit-msg` hook above Git's
  scissors line, in ETHOS's commit creation, and in every introduced commit range. Tag admission
  applies it to the tag message. The gaps name the class and the revision, never the address.
- ETHOS's tracked content moves to reserved forms. The kernel schema identifiers move from the
  `ethos.local` namespace to `ethos.invalid`, test sockets bind the `localhost` name, and test
  fixtures use RFC 2606 names and RFC 5737 addresses.
- The design fixes the redaction form that an immutable record may carry in place of a private
  literal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: tracked content and commit and tag messages carry no private-class network
  address.
- `command-plane`: commit-message admission judges the whole message above the scissors line.

## Impact

- `src/ethos/contracts/paradigm/`: `paradigm.toml` declares the pattern and `declaration.py`
  compiles and applies it.
- `.config/checks/gitleaks/gitleaks.toml`: the `private-network-address` rule.
- `src/ethos/repository/policy/boundary/catalog.py`: the product boundary takes its address
  classes from the paradigm's pattern.
- `src/ethos/adapters/repo/`: `commit/admission.py`, `commit/creation.py`, `git_object.py` and
  `release.py`.
- `src/ethos/contracts/plan.py` and `system/schemas/kernel/`: the schema identifiers.
- The rule, commit admission and tag admission tests, and the moved test fixtures.
- `CONTRIBUTING.md` and the command reference describe the message rule.
- Out of scope: `forge_repository`, artifacts, release notes, the changelog link format and the
  GitLab image source, which belong to `peer-neutral-artifacts`; a push-time exact check of named
  peer hosts and project paths; adopters' own content scans and records.
