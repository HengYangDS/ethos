"""Project an operator-supplied commit trust anchor into the CI checkout.

The runner or operator supplies either a protected anchor path or its public material
outside the checkout; without either, nothing is bound. No signer is discovered,
generated or taken from a user identity.
"""

from __future__ import annotations

import os
from pathlib import Path

from tools.ci.toolchain.environment import bind_commit_trust
from tools.ci.toolchain.environment import bind_commit_trust_material


def main() -> int:
    """Bind the one supplied trust input to the current checkout."""
    path = os.getenv("ETHOS_COMMIT_TRUST_ANCHOR")
    material = os.getenv("ETHOS_COMMIT_ALLOWED_SIGNERS")
    if path and material:
        message = "ci_commit_trust_inputs_ambiguous"
        raise ValueError(message)
    if material:
        bind_commit_trust_material(Path.cwd(), material)
    elif path:
        bind_commit_trust(Path.cwd(), Path(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
