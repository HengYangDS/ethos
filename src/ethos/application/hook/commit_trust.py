"""Bind the commit trust that an operator supplies to a checkout's local Git configuration.

`hook bind-trust` takes exactly one input: a protected anchor outside the checkout, named by
`--anchor` or by `ETHOS_COMMIT_TRUST_ANCHOR`, or the public material in
`ETHOS_COMMIT_ALLOWED_SIGNERS`, which an apply writes into a protected temporary file. It finds
and generates no signer and takes none from a user identity; without an input it binds nothing.
"""

import os
import shlex
import tempfile
from pathlib import Path

from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.filesystem import remove_owned_path
from ethos.adapters.repo.trust_anchor.filesystem import protect_for_current_identity
from ethos.adapters.repo.trust_anchor.verification import trust_anchor
from ethos.contracts.operations.hook import BindTrustRequest
from ethos.contracts.outcome import outcome_of
from ethos.result import EthosResult

_ANCHOR = "ETHOS_COMMIT_TRUST_ANCHOR"
_MATERIAL = "ETHOS_COMMIT_ALLOWED_SIGNERS"
_KEY = "gpg.ssh.allowedSignersFile"


def bind_commit_trust(root: Path, request: BindTrustRequest) -> EthosResult:
    """Preview the binding of the one supplied commit trust input, or apply it."""
    values = {
        "--anchor": request.anchor,
        _ANCHOR: os.getenv(_ANCHOR, ""),
        _MATERIAL: os.getenv(_MATERIAL, ""),
    }
    inputs = [name for name, value in values.items() if value]
    anchor, gaps = "", ["ci_commit_trust_inputs_ambiguous"] if len(inputs) > 1 else []
    try:
        if len(inputs) == 1:
            bind = _bind_material if inputs == [_MATERIAL] else _bind_anchor
            anchor, gaps = bind(root, values[inputs[0]], apply=request.apply)
    except OSError as error:
        gaps = [*outcome_of(error).gaps]
    planned = bool(inputs) and not gaps and not request.apply
    named = ("--anchor", request.anchor) if request.anchor else ()
    apply = ("ethos", "hook", "bind-trust", *named, "--apply", "--root", root.as_posix(), "--json")
    return EthosResult(
        command="hook bind-trust",
        verdict="block" if gaps else "pass",
        state="blocked" if gaps else "planned" if planned else "bound" if inputs else "unbound",
        summary={"inputs": inputs, "anchor": anchor},
        required_gaps=tuple(gaps),
        next_action=shlex.join(apply) if planned else "",
    )


def _bind_anchor(root: Path, configured: str, *, apply: bool) -> tuple[str, list[str]]:
    """Validate one anchor path; an apply writes the local setting and reads it back."""
    resolved, gaps = trust_anchor(root, configured)
    anchor = str(resolved or "")
    if apply and not gaps:
        run_git(root, "config", "--local", _KEY, anchor, check=False)
        if git_stdout(root, "config", "--local", "--get", _KEY) != anchor:
            gaps = ["ci_commit_trust_projection_failed"]
    return anchor, gaps


def _bind_material(root: Path, material: str, *, apply: bool) -> tuple[str, list[str]]:
    """Validate the public material; an apply binds it from a protected temporary file."""
    if not material.strip():
        return "", ["ci_commit_trust_material_missing"]
    if not apply:
        return "", []
    directory = Path(tempfile.mkdtemp(prefix="ethos-ci-trust-"))
    kept = False
    try:
        anchor = directory / "allowed-signers"
        anchor.write_text(material, encoding="utf-8", newline="\n")
        # A hosted temporary root is shared with other users; both are restricted to this identity.
        protect_for_current_identity(directory)
        protect_for_current_identity(anchor)
        bound = _bind_anchor(root, str(anchor), apply=True)
        kept = not bound[1]
        return bound
    finally:
        if not kept:
            remove_owned_path(directory)
