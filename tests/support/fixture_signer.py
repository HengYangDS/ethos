"""Sign every fixture commit with one SSH signer and its protected trust anchor.

The repository paradigm requires an SSH signature on every commit, so each fixture
repository signs through one signer per test process. The signer and its trust anchor
live outside every fixture repository, as the anchor must, and go when the process ends.
"""

from __future__ import annotations

import atexit
import functools
import shutil
import subprocess
import tempfile
from pathlib import Path

PRINCIPAL = "fixture@example.invalid"


@functools.cache
def _signer() -> tuple[str, Path, Path]:
    """Create the process signer once: ssh-keygen, the public key and the trust anchor."""
    executable = shutil.which("ssh-keygen")
    assert executable is not None
    directory = Path(tempfile.mkdtemp(prefix="ethos-fixture-signer-"))
    atexit.register(shutil.rmtree, directory, ignore_errors=True)
    key = directory / "signer"
    subprocess.run(
        (executable, "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
        capture_output=True,
        timeout=15,
    )
    public = key.with_suffix(".pub")
    anchor = directory / "allowed-signers"
    anchor.write_text(f'{PRINCIPAL} namespaces="git" {public.read_text()}', encoding="utf-8")
    anchor.chmod(0o600)
    return executable, public, anchor


def configure_fixture_signer(repo: Path) -> None:
    """Make every commit in the repository carry the trusted fixture SSH signature."""
    executable, public, anchor = _signer()
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", executable),
        ("user.signingkey", str(public)),
        ("gpg.ssh.allowedSignersFile", str(anchor)),
        ("commit.gpgsign", "true"),
    ):
        subprocess.run(("git", "config", name, value), cwd=repo, check=True, capture_output=True)


def fixture_signer_inputs() -> dict[str, str]:
    """Name the fixture signer as the explicit inputs a creator gives formation."""
    executable, public, anchor = _signer()
    return {"signing_key": str(public), "trust_anchor": str(anchor), "signing_program": executable}
