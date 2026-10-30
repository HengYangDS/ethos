"""The gaps that block one publication request before its remote effect."""

from collections.abc import Mapping
from pathlib import Path

import ethos.adapters.repo.git as git
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.repo.git_object import zero_oid
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence


def _remote_ref_observation(
    observations: Mapping[str, Mapping[str, object]], peer_id: str, target_ref: str
) -> dict[str, object]:
    """Return one nested peer ref observation without leaking storage shape."""
    peer = string_mapping(observations.get(peer_id))
    refs = string_mapping(peer.get("refs"))
    return string_mapping(refs.get(target_ref))


def publication_admission_gaps(
    *,
    repo: Path,
    target_refs: tuple[str, ...],
    source_object_oid: str,
    remotes: Mapping[str, str],
    observations: Mapping[str, Mapping[str, object]],
    effect_gaps: tuple[str, ...],
    proof_admission: Mapping[str, object],
    retire: bool = False,
) -> tuple[tuple[str, ...], dict[str, dict[str, object]]]:
    """Admit the push of each target ref to each peer whose current ref was observed."""
    reports: dict[str, dict[str, object]] = {}
    for peer_id, remote in remotes.items():
        for target_ref in target_refs:
            observation = _remote_ref_observation(observations, peer_id, target_ref)
            object_oid = observation.get("object_oid")
            if (
                observation.get("state") not in {"present", "absent"}
                or not isinstance(object_oid, str)
                or (not object_oid)
            ):
                continue
            reports[f"{peer_id}:{target_ref}"] = push_admission_report(
                root=repo,
                target_ref=target_ref,
                pushed_head=zero_oid(repo) if retire else source_object_oid,
                remote_head=object_oid,
                remote_name=remote,
                proof_admission=proof_admission,
            )
    proof_gaps = set(string_sequence(proof_admission.get("required_gaps")))
    gaps = tuple(
        dict.fromkeys(
            (
                *effect_gaps,
                *(
                    gap if gap in proof_gaps else f"{gap}:{peer_id}"
                    for peer_id, report in reports.items()
                    for gap in string_sequence(report.get("required_gaps"))
                ),
            )
        )
    )
    return (gaps, reports)


def publication_request_gaps(
    *,
    repo: Path,
    current_head: str,
    target_refs: tuple[str, ...],
    remotes: Mapping[str, str],
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    receipt: str | None,
    probe_remote: bool,
) -> list[str]:
    """Return invocation and source facts required before publication effects."""
    conditions = (
        (expect_head is None, "expect_head_required"),
        (apply and (not authorize), "authorization_required"),
        (expect_head is not None and expect_head != current_head, "expect_head_mismatch"),
        (receipt is not None and (not apply), "remote_publication_receipt_apply_required"),
        (receipt is None and (not probe_remote), "publication_remote_probe_required"),
        (not target_refs, "publication_target_ref_required"),
        (len(target_refs) != len(set(target_refs)), "publication_target_ref_duplicate"),
        (not remotes, "publication_peers_missing"),
    )
    gaps = [gap for blocked, gap in conditions if blocked]
    gaps.extend(
        f"publication_target_ref_invalid:{target_ref}"
        for target_ref in target_refs
        if not target_ref.startswith(("refs/heads/", "refs/tags/"))
        or git.run_git(repo, "check-ref-format", target_ref, check=False).returncode != 0
    )
    return gaps
