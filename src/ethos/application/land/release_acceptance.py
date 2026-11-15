"""Accept, on the releasing host, the release that the invoking installation is.

The command runs in the installation that was invoked, as the hook installation does, so the
bytes that run are the bytes it accepts. It refuses unless that installation is a release build of
the version the accepted branch commits, built from the commit that the version's tag names. The
accepted identity binds the release's checksum file; the wheel and the Attestation are written once.
"""

import shlex
from pathlib import Path

from packaging.version import Version

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.release import committed_release_version
from ethos.adapters.repo.runtime.materialization.input_resolution import selected_runtime_source
from ethos.adapters.repo.runtime.materialization.input_resolution import selected_runtime_wheel
from ethos.adapters.repo.runtime.transition import admit_explicit_release
from ethos.adapters.repo.runtime.transition import materialize_explicit_release
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.codes.gaps import repair_for
from ethos.contracts.operations.release import AcceptRequest
from ethos.contracts.outcome import outcome_of
from ethos.contracts.outcome import refuse
from ethos.contracts.outcome import require
from ethos.repository.release.configuration import is_product_root
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import is_release_build
from ethos.result import EthosResult

_COMMAND = "release accept"


def _installed_release(root: Path) -> tuple[Path, BuildIdentity]:
    """Return the invoking installation's wheel and the build that the release's tag requires."""
    require(is_product_root(root), "release_acceptance_product_only")
    installed = selected_runtime_source(Path(__file__))
    if installed is None or not is_release_build(installed.build):
        refuse("release_installation_absent")
    accepted = ref_head(root, load_branch_role_policy(root).accepted_branch)
    version = committed_release_version(root, accepted)["version"]
    held = installed.build.product_version
    if Version(held) < Version(version):
        refuse(f"release_installation_older:{held}")
    if Version(held) > Version(version):
        refuse(f"release_installation_newer:{held}")
    commit = git_stdout(root, "rev-parse", "--verify", f"refs/tags/v{version}^{{commit}}")
    require(commit, f"release_tag_missing:v{version}")
    tree = current_tree(root, commit)
    required = build_identity(product=version, source_commit=commit, source_tree=tree, release=True)
    return selected_runtime_wheel(installed), required


def accept_release(root: Path, request: AcceptRequest) -> EthosResult:
    """Run `release.accept.preview` and `release.accept.apply`; only `invoke` calls it."""
    try:
        wheel, build = _installed_release(root)
        release, held = admit_explicit_release(
            root, wheel, expected_build=build, checksums=request.checksums
        )
        if request.apply and not held:
            materialize_explicit_release(
                root,
                wheel,
                expected_build=build,
                collision="release_wheel_digest_collision",
                checksums=request.checksums,
            )
    except OSError:
        return _refused("release_acceptance_input_unreadable")
    except ValueError as error:
        return _refused(*outcome_of(error).gaps)
    # The apply names the file by its absolute path, so it runs from any working directory.
    checksums = str(request.checksums.resolve())
    apply = ("ethos", *_COMMAND.split(), "--checksums", checksums, "--apply")
    return EthosResult(
        command=_COMMAND,
        verdict="pass",
        state="unchanged" if held else "accepted" if request.apply else "ready",
        next_action=""
        if held or request.apply
        else shlex.join((*apply, "--root", str(root), "--json")),
        data={"identity": release.projection()},
    )


def _refused(*gaps: str) -> EthosResult:
    """Return the refusal that names each gap and the registered repair of the first."""
    return EthosResult(
        command=_COMMAND,
        verdict="block",
        state="gapped",
        required_gaps=gaps,
        next_action=repair_for(gaps[0]) or "repair the reported gap, then preview again",
    )
