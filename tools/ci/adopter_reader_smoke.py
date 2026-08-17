"""Package-only smoke for the deployed terminal-v1 adopter reader."""

import hashlib
import json
import shutil
from pathlib import Path

from ethos.adapters.repo.git import run_command

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/adopter-terminal-v1"


def check(ethos: Path, adopter: Path, git: str) -> dict[str, str]:
    """Project the deployed profile, then require installed status and plan."""
    for source in FIXTURE.iterdir():
        shutil.copy2(source, adopter / ".ethos" / source.name)
    for args in (("add", ".ethos"), ("commit", "--quiet", "-m", "project adopted reader")):
        run_command(adopter, (git, *args), check=True)
    run_command(adopter, (git, "branch", "-f", "main", "HEAD"), check=True)
    candidate = adopter.parent / f"{adopter.name}-candidate-dev"
    args = (git, "worktree", "add", "--quiet", "-b", "candidate/dev", str(candidate))
    run_command(adopter, args, check=True)
    observed: dict[str, dict[str, object]] = {}
    for command in (("status",), ("plan", "--changed")):
        result = run_command(adopter, (str(ethos), *command, "--root", str(adopter), "--json"))
        if result.returncode or "Traceback" in result.stdout + result.stderr:
            message = "installed adopted reader command failed"
            raise RuntimeError(message)
        observed[command[0]] = json.loads(result.stdout)
    compatibility = observed["plan"].get("data", {}).get("commitment_compatibility", {})
    expected = {
        "carrier": ".ethos/commitment.toml",
        "carrier_bytes_sha256": hashlib.sha256(
            (adopter / ".ethos/commitment.toml").read_bytes()
        ).hexdigest(),
        "mode": "terminal_v1_read_only",
        "mutation_authority": False,
        "proof_authority": False,
    }
    if any(x.get("verdict") != "pass" for x in observed.values()) or compatibility != expected:
        message = "installed adopted reader projection drifted"
        raise RuntimeError(message)
    return {"status": "pass", "plan": "pass", "mode": "terminal_v1_read_only"}
