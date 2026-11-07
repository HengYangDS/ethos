"""The process actor: the one reader of `ETHOS_ACTOR` and its local default."""

from __future__ import annotations

import os

ACTOR_VARIABLE = "ETHOS_ACTOR"
LOCAL_ISSUER = "agent:local:process:ethos"


def process_actor() -> str:
    """Return the actor this process declares, stripped; empty when it declares none."""
    return os.environ.get(ACTOR_VARIABLE, "").strip()


def process_issuer() -> str:
    """Return the actor that issues this process's records, or the local process default."""
    return process_actor() or LOCAL_ISSUER
