"""Quarantined Git-object verification and installation for handoff imports."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.lane_lifecycle.handoff.package import require
from ethos.adapters.mutation.lane_lifecycle.handoff.package import verified_package_snapshot
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Iterator


def _unbundle(repository: Path, bundle: Path, branch: str, head: str, tree: str) -> None:
    heads = run_git(repository, "bundle", "list-heads", bundle.as_posix()).stdout.splitlines()
    require("handoff_bundle_identity_mismatch", holds=heads == [f"{head} refs/heads/{branch}"])
    run_git(repository, "bundle", "unbundle", bundle.as_posix())
    actual = tuple(
        run_git(repository, "rev-parse", f"{head}^{{{kind}}}").stdout.strip()
        for kind in ("commit", "tree")
    )
    require("handoff_bundle_identity_mismatch", holds=actual == (head, tree))


@contextmanager
def import_objects(
    destination: Path,
    package: Path,
    manifest: dict[str, Any],
) -> Iterator[tuple[dict[str, str], list[Path]]]:
    """Yield verified alternate-object access and an installable quarantined pack."""
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    object_format = run_git(destination, "rev-parse", "--show-object-format").stdout.strip()
    expected_width = {"sha1": 40, "sha256": 64}.get(object_format)
    require("handoff_object_format_unsupported", holds=expected_width is not None)
    require("handoff_object_format_mismatch", holds=len(head) == expected_width)
    with (
        verified_package_snapshot(package=package, manifest=manifest, root=destination) as snapshot,
        tempfile.TemporaryDirectory(
            prefix="handoff-bare-", ignore_cleanup_errors=True
        ) as temporary,
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
        _verify_import_contract(isolated, manifest)
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
        "handoff_destination_object_store_unsafe",
        holds=objects == common / "objects"
        and objects.is_dir()
        and not objects.is_symlink()
        and (objects / "pack").is_dir()
        and not (objects / "pack").is_symlink(),
    )
    return objects


def object_environment(destination: Path, isolated: Path) -> dict[str, str]:
    objects = object_directory(destination)
    alternates = objects / "info" / "alternates"
    configured = alternates.read_text(encoding="utf-8").strip() if alternates.exists() else ""
    require(
        "handoff_destination_alternate_object_store_forbidden",
        holds=not alternates.is_symlink() and not configured,
    )
    return {
        "GIT_OBJECT_DIRECTORY": str(objects),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(isolated / "objects"),
    }


@contextmanager
def _prepared_pack(destination: Path, isolated: Path, head: str) -> Iterator[list[Path]]:
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
    require("handoff_destination_object_store_invalid", holds=closure.returncode in {0, 128})
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
    require("handoff_import_object_pack_empty", holds=bool(packed))
    with tempfile.TemporaryDirectory(
        prefix="handoff-import-", dir=objects, ignore_cleanup_errors=True
    ) as temporary:
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
            "handoff_import_object_install_failed",
            holds=len(pack_id) == len(head)
            and all(character in "0123456789abcdef" for character in pack_id)
            and {".idx", ".pack"} <= suffixes <= {".idx", ".pack", ".rev"},
        )
        yield candidates


def install_pack(destination: Path, candidates: list[Path]) -> None:
    """Atomically link one verified pack into the destination object store."""
    if not candidates:
        return
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


def _verify_import_contract(repository: Path, manifest: dict[str, Any]) -> None:
    try:
        load_lease_bound_commitment(
            repository,
            lease=manifest
            | {
                "expected_head": manifest["source_head"],
                "expected_tree": manifest["source_tree"],
            },
        )
    except ValueError as error:
        gap = {
            "lease_expected_tree_mismatch": "handoff_base_commitment_tree_mismatch",
            "lease_base_commitment_path_mismatch": "handoff_base_commitment_path_mismatch",
            "lease_base_commitment_bytes_mismatch": "handoff_base_commitment_bytes_mismatch",
            "lease_base_commitment_digest_mismatch": "handoff_base_commitment_digest_mismatch",
        }.get(str(error), "handoff_base_commitment_invalid")
        raise ValueError(gap) from None
