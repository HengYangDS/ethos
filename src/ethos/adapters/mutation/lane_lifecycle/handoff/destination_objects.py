"""Quarantined Git-object verification and installation for handoff imports."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.lane_lifecycle.handoff.package import verified_package_snapshot
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.digest import is_hex
from ethos.contracts.outcome import require

if TYPE_CHECKING:
    from collections.abc import Generator


def _unbundle(repository: Path, bundle: Path, branch: str, head: str, tree: str) -> None:
    heads = run_git(repository, "bundle", "list-heads", bundle.as_posix()).stdout.splitlines()
    require(heads == [f"{head} refs/heads/{branch}"], "handoff_bundle_identity_mismatch")
    run_git(repository, "bundle", "unbundle", bundle.as_posix())
    actual = tuple(
        run_git(repository, "rev-parse", f"{head}^{{{kind}}}").stdout.strip()
        for kind in ("commit", "tree")
    )
    require(actual == (head, tree), "handoff_bundle_identity_mismatch")


@contextmanager
def import_objects(
    destination: Path,
    package: Path,
    manifest: dict[str, Any],
) -> Generator[tuple[dict[str, str], list[Path]]]:
    """Yield verified alternate-object access and an installable quarantined pack."""
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    object_format = run_git(destination, "rev-parse", "--show-object-format").stdout.strip()
    expected_width = {"sha1": 40, "sha256": 64}.get(object_format)
    require(expected_width is not None, "handoff_object_format_unsupported")
    require(len(head) == expected_width, "handoff_object_format_mismatch")
    with (
        verified_package_snapshot(package=package, manifest=manifest, root=destination) as snapshot,
        tempfile.TemporaryDirectory(prefix="handoff-bare-") as temporary,
    ):
        isolated = Path(temporary) / "repository.git"
        isolated.mkdir()
        run_git(isolated, "init", "--bare", f"--object-format={object_format}", ".")
        _unbundle(
            isolated,
            snapshot / "repository.bundle",
            branch,
            head,
            str(manifest["source_tree"]),
        )
        _verify_import_contract(destination, isolated, manifest)
        environment = object_environment(destination, isolated)
        with _prepared_pack(destination, isolated, head) as pack:
            yield environment, pack


def object_directory(destination: Path) -> Path:
    common = Path(
        run_git(
            destination, "rev-parse", "--path-format=absolute", "--git-common-dir"
        ).stdout.strip()
    )
    objects = Path(
        run_git(
            destination, "rev-parse", "--path-format=absolute", "--git-path", "objects"
        ).stdout.strip()
    )
    require(
        objects == common / "objects"
        and objects.is_dir()
        and not objects.is_symlink()
        and (objects / "pack").is_dir()
        and not (objects / "pack").is_symlink(),
        "handoff_destination_object_store_unsafe",
    )
    return objects


def object_environment(destination: Path, isolated: Path) -> dict[str, str]:
    objects = object_directory(destination)
    alternates = objects / "info" / "alternates"
    configured = alternates.read_text(encoding="utf-8").strip() if alternates.exists() else ""
    require(
        not alternates.is_symlink() and not configured,
        "handoff_destination_alternate_object_store_forbidden",
    )
    return {
        "GIT_OBJECT_DIRECTORY": str(objects),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(isolated / "objects"),
    }


@contextmanager
def _prepared_pack(destination: Path, isolated: Path, head: str) -> Generator[list[Path]]:
    objects = object_directory(destination)
    closure = run_git(
        destination,
        "rev-list",
        "--objects",
        "--missing=print",
        head,
        check=False,
        env={"GIT_OBJECT_DIRECTORY": str(objects)},
    )
    require(closure.returncode in {0, 128}, "handoff_destination_object_store_invalid")
    if closure.returncode == 0 and not any(
        line.startswith("?") for line in closure.stdout.splitlines()
    ):
        yield []
        return
    packed = run_git(
        isolated,
        "pack-objects",
        "--stdout",
        "--revs",
        "--no-thin",
        stdin=f"{head}\n".encode(),
        text=False,
    ).stdout
    require(bool(packed), "handoff_import_object_pack_empty")
    with tempfile.TemporaryDirectory(prefix="handoff-import-", dir=objects) as temporary:
        quarantine = Path(temporary)
        (quarantine / "pack").mkdir()
        installed = run_git(
            destination,
            "index-pack",
            "--stdin",
            "--strict",
            env={"GIT_OBJECT_DIRECTORY": str(quarantine)},
            stdin=packed,
            text=False,
        )
        pack_id = installed.stdout.decode().strip().removeprefix("pack\t")
        candidates = sorted((quarantine / "pack").glob(f"pack-{pack_id}.*"))
        suffixes = {path.suffix for path in candidates}
        require(
            is_hex(pack_id, len(head))
            and {".idx", ".pack"} <= suffixes <= {".idx", ".pack", ".rev"},
            "handoff_import_object_install_failed",
        )
        yield candidates


def install_pack(
    destination: Path,
    candidates: list[Path],
    *,
    commitment_digest: str | None,
    head: str,
    repository_id: str,
) -> dict[str, object]:
    """Atomically link one verified pack into the destination object store."""
    names = tuple(path.name for path in candidates)
    if not candidates:
        return issue_native_effect(
            destination,
            effect=NativeEffect(
                predicate="effect:git-object-install",
                operation="filesystem.link-object-pack",
                command=("link",),
                subject={"head": head, "pack_files": names},
                before={"installed": names},
                after={"installed": names},
            ),
            state="recognized",
            commitment_digest=commitment_digest,
            repository_id=repository_id,
        ).model_dump(mode="json")
    target = object_directory(destination) / "pack"
    by_suffix = {path.suffix: path for path in candidates}
    ordered = [by_suffix[".idx"], *([by_suffix[".rev"]] if ".rev" in by_suffix else [])]
    installed: list[Path] = []
    try:
        for source in ordered:
            os.link(source, target / source.name)
            installed.append(target / source.name)
        os.link(by_suffix[".pack"], target / by_suffix[".pack"].name)
    except OSError:
        try:
            for path in reversed(installed):
                path.unlink()
        except OSError:
            msg = "handoff_import_object_cleanup_failed"
            raise ValueError(msg) from None
        raise
    return issue_native_effect(
        destination,
        effect=NativeEffect(
            predicate="effect:git-object-install",
            operation="filesystem.link-object-pack",
            command=("link",),
            subject={"head": head, "pack_files": names},
            before={"installed": ()},
            after={"installed": names},
        ),
        state="applied",
        commitment_digest=commitment_digest,
        repository_id=repository_id,
    ).model_dump(mode="json")


def _verify_import_contract(
    destination: Path,
    source_objects: Path,
    manifest: dict[str, Any],
) -> None:
    """Reject a package whose committed repository identity differs."""
    try:
        source = repository_identity(source_objects, tree_ref=str(manifest["source_head"]))
        target = repository_identity(destination)
    except ValueError:
        msg = "handoff_repository_identity_invalid"
        raise ValueError(msg) from None
    require(source == target, "handoff_repository_identity_mismatch")
