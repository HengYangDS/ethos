"""Verify native Git signatures against one immutable, still-current trust input set."""

from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from typing import cast

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.trust_anchor.filesystem import protected_from_untrusted_write

_ANCHOR = "gpg.ssh.allowedsignersfile"
_REVOCATION = "gpg.ssh.revocationfile"
_CHANGED = "git_object_trust_changed_during_verification"
_SSH_STATUS = re.compile(
    r'^Good "git" signature for (?P<principal>.+) with \S+ key '
    r"(?P<fingerprint>SHA256:[A-Za-z0-9+/=]+)\r?$",
    re.MULTILINE,
)


def trust_anchor(root: Path, configured: str) -> tuple[Path | None, list[str]]:
    """Resolve one protected repository-external OpenSSH trust anchor."""
    if not configured:
        return None, ["git_object_trust_anchor_missing"]
    anchor = Path(configured).expanduser()
    if not anchor.is_absolute():
        return None, ["git_object_trust_anchor_not_absolute"]
    resolved: Path | None = None
    gaps: list[str] = []
    try:
        resolved = anchor.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except FileNotFoundError:
        gaps = ["git_object_trust_anchor_missing"]
    except ValueError:
        resolved = anchor.resolve()
    else:
        gaps = ["git_object_trust_anchor_inside_repository"]
    if resolved is not None and not gaps:
        gaps = (
            ["git_object_trust_anchor_missing"]
            if not resolved.is_file()
            else ["git_object_trust_anchor_unprotected"]
            if not protected_from_untrusted_write(resolved)
            else []
        )
    return resolved, gaps


def configured_commit_trust_anchor(root: Path) -> tuple[Path | None, list[str]]:
    """Observe the native commit trust anchor independently of any candidate signature."""
    configured = run_git(root, "config", "--path", "--get", _ANCHOR, check=False).stdout.strip()
    anchor, gaps = trust_anchor(root, configured)
    return anchor, [_commit_gap(gap) for gap in gaps]


@dataclass(frozen=True, slots=True)
class _TrustInputs:
    """Ephemeral native configuration and exact external verification material."""

    configuration: tuple[tuple[str, str], ...]
    anchor: Path
    anchor_bytes: bytes
    revocation: Path | None
    revocation_bytes: bytes

    @classmethod
    def read(cls, root: Path) -> _TrustInputs:
        result = run_git(root, "config", "--null", "--get-regexp", r"^gpg\.", check=False)
        if result.returncode not in {0, 1}:
            message = "git_object_trust_configuration_unavailable"
            raise ValueError(message)
        configuration = tuple(
            (name.lower(), value)
            for row in result.stdout.split("\0")
            if row
            for name, separator, value in (row.partition("\n"),)
            if separator
        )
        paths: dict[str, Path | None] = {}
        for key in (_ANCHOR, _REVOCATION):
            configured = run_git(root, "config", "--path", "--get", key, check=False).stdout.strip()
            if not configured and key == _REVOCATION:
                paths[key] = None
                continue
            path, gaps = trust_anchor(root, configured)
            if gaps:
                raise ValueError(gaps[0])
            paths[key] = path
        anchor = cast("Path", paths[_ANCHOR])
        revocation = paths[_REVOCATION]
        return cls(
            configuration,
            anchor,
            anchor.read_bytes(),
            revocation,
            revocation.read_bytes() if revocation is not None else b"",
        )

    def arguments(self, directory: Path) -> tuple[str, ...]:
        """Pin native verification to owned snapshots, leaving the original files untouched."""
        entries = {
            "gpg.ssh.program": "ssh-keygen",
            "gpg.mintrustlevel": "undefined",
            **dict(self.configuration),
        }
        for key, content in ((_ANCHOR, self.anchor_bytes), (_REVOCATION, self.revocation_bytes)):
            path = directory / key
            path.write_bytes(content)
            path.chmod(0o600)
            entries[key] = str(path)
        return tuple(part for key, value in entries.items() for part in ("-c", f"{key}={value}"))


def verify_git_object_trust(
    root: Path, revision: str | tuple[str, ...], kind: Literal["commit", "annotated-tag"]
) -> dict[str, object]:
    """Verify exact objects in bounded native batches under one current trust input set."""
    revisions = (revision,) if isinstance(revision, str) else revision
    verifier = "verify-tag" if kind == "annotated-tag" else "verify-commit"
    report: dict[str, object] = {
        "verdict": "block",
        "revision": revision,
        "anchor": "",
        "trust_anchor_sha256": "",
        "verifier": f"git {verifier}",
        "verifier_version": run_git(root, "version", check=False).stdout.strip(),
        "required_gaps": [],
        "principal": "",
        "fingerprint": "",
        "status": "",
    }
    if not revisions:
        report["required_gaps"] = ["git_object_trust_selection_empty"]
        return report
    try:
        inputs = _TrustInputs.read(root)
        report.update(
            anchor=str(inputs.anchor),
            trust_anchor_sha256=hashlib.sha256(inputs.anchor_bytes).hexdigest(),
        )
        with tempfile.TemporaryDirectory(prefix="ethos-trust-") as directory:
            arguments = inputs.arguments(Path(directory))
            gaps, statuses, matches = [], [], []
            for start in range(0, len(revisions), 128):
                selected = revisions[start : start + 128]
                completed = run_git(
                    root, *arguments, verifier, "--raw", *selected, check=False, timeout=30
                )
                status = completed.stderr.strip() or completed.stdout.strip()
                found = list(_SSH_STATUS.finditer(status))
                statuses.append(status)
                if completed.returncode or len(found) != len(selected):
                    gaps = [
                        "git_object_signature_untrusted"
                        if completed.returncode
                        else "git_object_signature_observation_unavailable"
                    ]
                    break
                matches.extend(found)
            if _TrustInputs.read(root) != inputs:
                gaps = [_CHANGED]
            report.update(required_gaps=gaps, status="\n".join(statuses))
            if not gaps:
                report.update(verdict="pass")
                if len(matches) == 1:
                    report.update(
                        principal=matches[0].group("principal"),
                        fingerprint=matches[0].group("fingerprint"),
                    )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report["required_gaps"] = [
            str(error)
            if isinstance(error, ValueError)
            else "git_object_trust_observation_unavailable"
        ]
        report["status"] = str(error)
    return report


def verify_commit_trust(root: Path, revision: str | tuple[str, ...]) -> dict[str, object]:
    """Project native object verification through the commit admission gap vocabulary."""
    report = verify_git_object_trust(root, revision, "commit")
    return {
        **report,
        "required_gaps": [
            _commit_gap(str(gap)) for gap in cast("list[object]", report["required_gaps"])
        ],
    }


def _commit_gap(gap: str) -> str:
    return {
        "git_object_trust_anchor_missing": "commit_trust_anchor_missing",
        "git_object_trust_anchor_not_absolute": "commit_trust_anchor_not_absolute",
        "git_object_trust_anchor_inside_repository": "commit_trust_anchor_inside_repository",
        "git_object_trust_anchor_unprotected": "commit_trust_anchor_unprotected",
        "git_object_signature_untrusted": "commit_signature_untrusted",
        "git_object_signature_observation_unavailable": "commit_signature_untrusted",
        _CHANGED: "commit_trust_changed_during_verification",
    }.get(gap, gap)
