"""Read the subjects this host records, and compare a release's recorded predecessors with them.

Each fact is read offline and from one place. The subjects are the Git common directories that the
installations in the host store record as consumers, less the releasing repository's own. A
subject's selection is the build that its `CURRENT` names: a record names the consumer alone, and
one consumer is recorded under each installation it selects or holds for rollback, so the record
does not say which. A development build goes by its distribution version, which no changelog
lists. A subject's pin is the Mise configuration in its accepted branch's tree, where it declares
one. A declaration that cannot be read names no release and changes no selection, so its
repository is a subject by its selection, and such pins are counted by themselves. A subject's
last landed bump is the committer time of the newest accepted commit that changed how often that
file names the pinned release; a subject without a readable pin has none, since a record holds no
time. No repository's path leaves this module. The subjects are ordered by their bumps; those
that no bump dates come last, in the order in which their records are read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import Version

import ethos.adapters.repo.git as git
import ethos.contracts.branch.roles as roles
import ethos.repository.release.pin as pin
import ethos.repository.release.predecessors as predecessors
from ethos.adapters.repo.release import committed_release_version
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.contracts.paradigm.declaration import binding_path
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.release.changelog import released_versions
from ethos.repository.release.configuration import release_config_from_text

if TYPE_CHECKING:
    from pathlib import Path


def read_subjects(root: Path) -> tuple[list[predecessors.Subject], int]:
    """Read every recorded consumer but this repository, newest bump first; count the unreadable.

    A host without a store records no consumer, so it has no subject. A consumer with neither a
    readable pin nor a readable selection is unread.
    """
    store = host_store_root()
    installations = store / "installations" if store is not None else None
    recorded = installations is not None and installations.is_dir()
    commons = {
        common
        for installation in (installations.iterdir() if installations and recorded else ())
        for common in (installation_consumers(installation) or {}).values()
    }
    own = git.git_common_dir(root)
    subjects: list[predecessors.Subject] = []
    unread = 0
    for common in sorted(item for item in commons if item is not None and item.as_posix() != own):
        try:
            found = _subject(common)
        except (OSError, ValueError):
            found = []
        subjects += found
        unread += not found
    subjects.sort(key=lambda subject: subject.bumped or 0, reverse=True)
    return subjects, unread + (None in commons)


def _subject(common: Path) -> list[predecessors.Subject]:
    """Read one repository: its selection, and its accepted pin where it declares one."""
    accepted = roles.BranchRolePolicy().accepted_branch
    config, form = git.committed_file_text(common, accepted, MISE_CONFIG), ""
    try:
        declared = pin.declared_pin(config)
    except ValueError:
        # Only the declaration's text is judged here; a failed Git read stays a failed read.
        declared, form = None, predecessors.UNREADABLE
    try:
        build = current_runtime(common).build
    except (OSError, ValueError):
        build = None
    current = (
        ""
        if build is None
        else build.distribution_version
        if Version(build.distribution_version).is_devrelease
        else build.product_version
    )
    head = git.ref_head(common, accepted)
    if declared is None:
        # A subject by its selection alone: nothing dates its last bump.
        return [predecessors.Subject(head, form, "", current, None)] if current else []
    # A longer version that begins or ends with this one, as `beta.10` begins with `beta.1`, is
    # another release.
    named = f"-S(^|[^0-9.]){declared.version.replace('.', '[.]')}([^0-9]|$)"
    log = ("log", "-1", "--format=%ct", "--pickaxe-regex", named, accepted, "--", MISE_CONFIG)
    bumped = int(git.git_stdout(common, *log))
    return [predecessors.Subject(head, declared.form, declared.version, current, bumped)]


def recorded_upgrade_from(root: Path, head: str) -> dict[str, str] | None:
    """Read what the release binding at `head` records; None where it declares no carrier."""
    binding = git.committed_file_text(root, head, binding_path("release"))
    return predecessors.recorded(release_config_from_text(binding))


def upgrade_from_report(root: Path, head: str) -> dict[str, object]:
    """Derive what the release at `head` upgrades from, and name what its record lacks.

    `counts` and `named` cover the subjects inside the window: how many pin in each form or are
    subjects by selection alone, and how many name the release itself and each predecessor.
    `unlisted` holds the versions they name that the changelog does not list.
    `subjects_with_unreadable_pin` counts, among those by selection alone, the subjects whose
    declared pin cannot be read; none of them is an unread consumer.
    """
    recorded = recorded_upgrade_from(root, head)
    subjects, unread = read_subjects(root)
    version = committed_release_version(root, head)["version"]
    changelog = load_repository_paradigm().release.changelog
    history = released_versions(git.committed_file_text(root, head, changelog))
    derived = predecessors.derive(version, history, subjects)
    missing = ",".join(name for name in derived if name not in (recorded or {}))
    window = predecessors.supported(subjects)
    named = predecessors.named_by(subjects)
    forms = [subject.form if subject.pinned else "selection" for subject in window]
    unreadable = sum(subject.form == predecessors.UNREADABLE for subject in window)
    return {
        "release": version,
        "recorded": recorded,
        "derived": derived,
        "named": {
            name: named.get(name, {"pin": 0, "selection": 0}) for name in (version, *derived)
        },
        "unlisted": {name: count for name, count in named.items() if name not in history},
        "counts": {form: forms.count(form) for form in ("github", "http", "selection")},
        "subjects": [{**subject._asdict(), "supported": subject in window} for subject in subjects],
        "unread": unread,
        "subjects_with_unreadable_pin": unreadable,
        "required_gaps": ["release_upgrade_from_empty"]
        if not recorded
        else [f"release_upgrade_from_incomplete:{missing}"]
        if missing
        else [],
    }
