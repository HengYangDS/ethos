"""Sign fixture commits with SSH signers whose protected trust anchors this module creates.

The repository paradigm requires an SSH signature on every commit, so each fixture
repository signs through one signer per test process. A test that changes its signer's trust
or key owns a signer in a directory it names instead, whose anchor trusts that signer or, for
an untrusted signer, nobody yet. Every anchor lives outside every fixture repository, as the
anchor must, and the process signer goes when the process ends.
"""

from __future__ import annotations

import atexit
import functools
import shutil
import subprocess
import tempfile
from pathlib import Path

PRINCIPAL = "fixture@example.invalid"


def _create_signer(
    directory: Path, *, trusted: bool = True, key_type: str = "ed25519"
) -> tuple[str, Path, Path]:
    """Create ssh-keygen's key `signer` in `directory` and its anchor `trust/allowed-signers`."""
    executable = shutil.which("ssh-keygen")
    assert executable is not None
    key = directory / "signer"
    subprocess.run(
        (executable, "-q", "-t", key_type, "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    public = key.with_suffix(".pub")
    trust = directory / "trust"
    trust.mkdir(mode=0o700)
    anchor = trust / "allowed-signers"
    anchor.write_text(
        f'{PRINCIPAL} namespaces="git" {public.read_text()}' if trusted else "", encoding="utf-8"
    )
    anchor.chmod(0o600)
    return executable, public, anchor


@functools.cache
def _signer() -> tuple[str, Path, Path]:
    """Create the process signer once, in a directory that goes when the process ends."""
    directory = Path(tempfile.mkdtemp(prefix="ethos-fixture-signer-"))
    atexit.register(shutil.rmtree, directory, ignore_errors=True)
    return _create_signer(directory)


def configure_fixture_signer(
    repo: Path, own: Path | None = None, *, trusted: bool = True, key_type: str = "ed25519"
) -> Path:
    """Make every commit in the repository carry a fixture SSH signature; return its anchor.

    Without `own` the repository signs as the process signer. With it, the repository signs with
    a new `key_type` signer created in `own`, which its anchor trusts unless `trusted` is false.
    """
    executable, public, anchor = (
        _signer() if own is None else _create_signer(own, trusted=trusted, key_type=key_type)
    )
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", executable),
        ("user.signingkey", str(public)),
        ("gpg.ssh.allowedSignersFile", str(anchor)),
        ("commit.gpgsign", "true"),
    ):
        subprocess.run(("git", "config", name, value), cwd=repo, check=True, capture_output=True)
    return anchor


def fixture_signer_inputs() -> dict[str, str]:
    """Name the fixture signer as the explicit inputs a creator gives formation."""
    executable, public, anchor = _signer()
    return {"signing_key": str(public), "trust_anchor": str(anchor), "signing_program": executable}
