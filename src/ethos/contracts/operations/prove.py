"""The `ethos prove` request and the five proof operations its selectors choose between."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch
from ethos.contracts.proof.plan import AcceptancePurpose


class ProofRequest(CommandRequest):
    """One proof request: its scope, gates and execution, and the head and Change it binds."""

    objective: str = described("ethos proof", "The objective the proof Attestation records.")
    scope: str = described("repository", "The scope proved; any but `repository` is focused.")
    execute: bool = switch("Run the planned gates instead of previewing them.")
    gate: tuple[str, ...] = described((), "Run only this gate, a focused proof; repeat for more.")
    full: bool = switch("Run every gate under the repository's proof slot.")
    change: str | None = described(None, "Prove this active OpenSpec Change.")
    expect_head: str | None = described(None, "The lane head the proof must observe.")
    host: bool = switch("Run the gates on this host, without proof authority.")
    probe: bool = switch("Record this host's readiness boundary beside the plan.")
    readiness: bool = switch("Run only the readiness gates, without an Attestation.")
    acceptance_purpose: AcceptancePurpose = described(
        "repository", "What the proof accepts: `repository`, or a full `local-source` proof."
    )


COMMAND = Command(
    name="prove",
    summary="Produce proof readiness or one executed generic proof Attestation.",
    request=ProofRequest,
    operations=(
        operation(
            "proof.preview",
            "Preview the proof plan and its readiness without running a gate.",
            select="execute=false readiness=false",
            request="objective scope gate full change expect_head host probe acceptance_purpose",
            effects="read",
            exit_kind="verdict",
        ),
        operation(
            "proof.execute",
            "Run the planned gates and issue the proof Attestation.",
            select="execute=true full=false host=false readiness=false",
            request="objective scope gate change expect_head",
            effects="read execute local-evidence-write",
            exit_kind="verdict",
        ),
        operation(
            "proof.run",
            "Run the full proof under the proof slot and issue its Attestation.",
            select="execute=true full=true host=false readiness=false",
            request="objective scope gate change expect_head acceptance_purpose",
            effects="read execute local-evidence-write",
            exit_kind="verdict",
        ),
        operation(
            "proof.readiness",
            "Run the readiness gates alone, without an Attestation.",
            select="readiness=true execute=true host=false",
            request="change expect_head",
            effects="read execute",
            exit_kind="verdict",
        ),
        operation(
            "proof.host",
            "Run the selected gates on this host, without proof authority.",
            select="host=true execute=true readiness=false",
            request="gate full change expect_head",
            effects="read execute",
            exit_kind="verdict",
        ),
    ),
)
