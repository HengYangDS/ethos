# Design

## Context

See [proposal.md](proposal.md). The paradigm's root catalog admits `CONTRIBUTING.md` as an entry
document but requires only `AGENTS.md` and `README.md`. Its release conventions already require
`VERSION` and a Keep a Changelog `CHANGELOG.md` once the release binding declares release tags, and
its license section checks a `LICENSE` only when one is tracked. The peer-remote check reports every
peer whose `git_remote` differs from its id.

## Goals / Non-Goals

**Goals:**

- One declaration, the paradigm, owns which documents a repository root keeps, selected by facts the
  repository already declares, and ETHOS reads the same declaration for itself.
- `origin` is accepted exactly when it is unambiguous.

**Non-Goals:**

- A security policy (`SECURITY.md`); no governed repository keeps one, and who owns its common text
  is undecided.
- Writing a repository's contributor guide; the guide describes the repository's own scope.
- Removing `release_policy_report`, which has no production caller but whose tests cover the
  publication topology.

## Decisions

- **Facts select the documents.** People and agents contribute to every governed repository, so each
  keeps a contributor guide beside the agent entry and the reader entry. A repository that tags
  releases distributes its work, so it keeps a license grant. Rejected: one list for every
  repository, which would give a repository that never releases a license it has not chosen; a
  repository-type switch, which decision D26 rejects as an input.
- **The paradigm owns the list; ETHOS's audit derives from it.** The release-file list becomes the
  paradigm's required documents, its license carrier, its changelog and the release binding, so
  ETHOS cannot require of itself what it does not require of a governed repository with the same
  facts.
- **Repair does not write the guide.** Its content is the repository's own scope and boundaries; a
  generated stub would only repeat the workflow that ETHOS's shipped quickstart already owns.
- **`origin` names only a sole remote.** With one peer the name is unambiguous and is what Git and
  the forges' CI clones use. With two or more, `origin` would single out one peer and hide which
  forge it is, so each remote takes its peer id. A repository that adds a second peer receives the
  rename gap with the exact `git remote rename`. The paradigm's release conventions declare the
  clone name (`clone_remote`), as Git's `clone.defaultRemoteName` defaults it; the check reads the
  declaration. Rejected: reading each host's Git configuration, which would make a tracked binding
  conform on one machine and not on another.

## Risks / Trade-offs

- [Four adopters gain a gap when they upgrade: `architecture-publisher`, `ddwg-introduction-film`,
  `ethos-film` and `ethos-introduction-film`] → The gap names the file, and their owners have the
  list.
- [A sole-peer repository renames its remote when it adds a second peer] → The paradigm reports the
  rename, and `git remote rename` moves its tracking references.
