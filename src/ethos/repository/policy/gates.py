from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from ethos.contracts.gates import DECLARATION_PATH
from ethos.contracts.gates import GateDescriptor
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.normalization.coercion import string_mapping
from ethos.repository.context import is_product_root
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile

_GATE_DECLARATION = load_gate_registry_declaration()
PRODUCT_DEFAULT_GATE_IDS = _GATE_DECLARATION.proof_sets.product_default
PRODUCT_FULL_GATE_IDS = _GATE_DECLARATION.proof_sets.product_full
DEFAULT_GATE_IDS = PRODUCT_DEFAULT_GATE_IDS
ADOPTER_DEFAULT_GATE_IDS = _GATE_DECLARATION.proof_sets.adopter_default


def _product_gate_registry() -> dict[str, GateDescriptor]:
    """Compile the product-owned runtime gate registry."""
    return _GATE_DECLARATION.registry("runtime", python_executable=sys.executable)


def _adopter_gate_overlay(
    root: Path | None,
    product_registry: dict[str, GateDescriptor],
    *,
    tree_ref: str | None = None,
) -> tuple[dict[str, GateDescriptor], tuple[str, ...]]:
    """Compile repository-native gate descriptors from an adopter profile."""
    if not adopter_profile_active(root, tree_ref=tree_ref):
        return {}, ()
    assert root is not None
    declaration = load_repository_profile(root, tree_ref=tree_ref).declaration
    assert declaration is not None
    proof = declaration.proof
    overlay: dict[str, GateDescriptor] = {}
    gaps: list[str] = []
    for gate in proof.gates:
        if gate.id in product_registry:
            gaps.append(f"adopter_gate_descriptor_conflict:{gate.id}")
            continue
        if gate.id in overlay:
            gaps.append(f"adopter_gate_descriptor_duplicate:{gate.id}")
            continue
        overlay[gate.id] = gate

    gaps.extend(
        f"adopter_gate_descriptor_missing:{gate_id}"
        for gate_id in proof.code_correctness_gates
        if gate_id not in product_registry and gate_id not in overlay
    )
    return overlay, tuple(dict.fromkeys(gaps))


def gate_registry(
    root: Path | None = None, *, tree_ref: str | None = None
) -> dict[str, GateDescriptor]:
    """Compile product gates plus a typed repository-native adopter overlay."""
    registry = _product_gate_registry()
    overlay, _ = _adopter_gate_overlay(root, registry, tree_ref=tree_ref)
    return {**registry, **overlay}


def adopter_gate_descriptor_gaps(
    root: Path | None, *, tree_ref: str | None = None
) -> tuple[str, ...]:
    """Return fail-closed gaps for incomplete or invalid adopter gate descriptors."""
    profile = load_repository_profile(root, tree_ref=tree_ref) if root else None
    if profile is not None and profile.state == "invalid":
        return ("adopter_profile_invalid:.ethos/profile.toml",)
    registry = _product_gate_registry()
    _, gaps = _adopter_gate_overlay(root, registry, tree_ref=tree_ref)
    return gaps


def adopter_profile_active(root: Path | None, *, tree_ref: str | None = None) -> bool:
    """Return True only for a VALID adopter profile on a non-product root.

    Keying the floor on bare `.exists` let any `.ethos/profile.toml` — 0-byte, invalid
    TOML, or the product repo's own — downgrade the 19-gate product floor to the 11-gate
    adopter floor, dropping every code-correctness gate with no forgery. Require the
    profile to exist, PARSE (`valid`), and the root to not be the product itself.
    """
    if root is None:
        return False
    if is_product_root(root):
        return False
    profile = load_repository_profile(root, tree_ref=tree_ref)
    return profile.state == "valid"


ADOPTER_MISSING_CODE_CORRECTNESS_GATE = "adopter_profile_missing_code_correctness_gates"

# The genuine code-correctness axes an adopter proof must cover. Deliberately minimal and
# tool-agnostic: every real stack both EXECUTES the code and observes it (behavior) and
# REASONS about the source without executing it (static-analysis). Each axis is
# MAP-OR-WAIVE — a monolithic stack (e.g. a compiler that enforces types inside the test
# run) waives the covered-elsewhere axis with an explicit reason, so we never false-reject
# a legitimately different toolchain.
REQUIRED_CODE_CORRECTNESS_AXES = ("behavior", "static-analysis")

# A mapped gate must carry a trust-bearing verdict whose evidence class is promotion-grade.
# Mirrors the product's own proof/contract line; `diagnostic` (e.g. ruff-style) cannot
# launder a code-correctness claim. This is a FLOOR, not a ceiling — an adopter stricter
# than the product (lint stamped proof) still qualifies.
TRUST_EVIDENCE_CLASSES = frozenset({"proof", "contract"})

# Seed axis vocabulary (adopter-extensible via [proof.code_correctness_axes]). Attribution
# reads a gate's own `kind` + `dimensions` MEANING TOKENS — never a tool name — so any
# stack maps its gates by declaring honest kinds/dimensions.
_SEED_AXIS_TOKENS: dict[str, frozenset[str]] = {
    "behavior": frozenset(
        {"test", "coverage", "behavior", "property", "e2e", "acceptance", "integration"}
    ),
    "static-analysis": frozenset(
        {
            "typing",
            "types",
            "type-check",
            "lint",
            "static-analysis",
            "architecture",
            "import-discipline",
            "complexity",
            "compile",
            "vet",
            "sast",
        }
    ),
}

# POSIX no-ops: a command whose head is one of these is a degenerate gate (shallow, honest
# denylist — cannot catch a real-looking harness over zero tests; that residual is closed
# by governed profile review + DR-0006 re-execution, not here).
_NOOP_EXECUTABLES = frozenset({"true", ":", "echo", "printf", "test", "["})


def _code_correctness_axis_vocab(profile: object) -> dict[str, frozenset[str]]:
    """Seed axis→token map unioned with the adopter's own [proof.code_correctness_axes].

    The adopter may extend an axis's recognized tokens (e.g. add "fuzz" to behavior) so
    their ontology is first-class without ETHOS blessing specific tools. The extension is
    folded into the policy digest (gate_policy_fields), so an adopter cannot silently
    redefine an axis after a proof is stamped.
    """
    vocab = {axis: set(tokens) for axis, tokens in _SEED_AXIS_TOKENS.items()}
    declaration = getattr(profile, "declaration", None)
    extension = declaration.proof.code_correctness_axes if declaration else {}
    for axis, tokens in extension.items():
        if axis in vocab:
            vocab[axis].update(tokens)
    return {axis: frozenset(tokens) for axis, tokens in vocab.items()}


def _gate_axes(gate: GateDescriptor, vocab: dict[str, frozenset[str]]) -> set[str]:
    """The code-correctness axes a gate attributes to, via its kind + dimensions tokens."""
    tokens = {str(gate.kind), *(str(dim) for dim in gate.dimensions)}
    return {axis for axis, axis_tokens in vocab.items() if tokens & axis_tokens}


def _command_is_degenerate(command: tuple[str, ...]) -> bool:
    """True when the gate command is a literal no-op (empty or a POSIX no-op head)."""
    if not command:
        return True
    head = Path(str(command[0])).name
    return head in _NOOP_EXECUTABLES


def _qualifies_for_axis(gate: GateDescriptor, axis: str, vocab: dict[str, frozenset[str]]) -> bool:
    """Whether a gate genuinely backs `axis`: attributed, trust-bearing, promotion-grade
    evidence, and a non-degenerate command. (Adopter-authorship + distinctness are checked
    by the caller, which holds the overlay and the full mapping.)"""
    return (
        axis in _gate_axes(gate, vocab)
        and gate.trust_bearing is True
        and gate.evidence_class in TRUST_EVIDENCE_CLASSES
        and (bool(gate.providers) or not _command_is_degenerate(gate.command))
    )


def _code_correctness_map(profile: object) -> dict[str, dict[str, str]]:
    """Parse [proof.code_correctness_map] into {axis: {"gate": id} | {"waived": reason}}."""
    declaration = getattr(profile, "declaration", None)
    raw = declaration.proof.code_correctness_map if declaration else None
    parsed: dict[str, dict[str, str]] = {}
    if not isinstance(raw, Mapping):
        return parsed
    for axis, entry in raw.items():
        if isinstance(entry, str):
            parsed[str(axis)] = {"gate": entry}
        elif isinstance(entry, Mapping):
            if isinstance(entry.get("gate"), str):
                parsed[str(axis)] = {"gate": str(entry["gate"])}
            elif isinstance(entry.get("waived"), str) and str(entry["waived"]).strip():
                parsed[str(axis)] = {"waived": str(entry["waived"])}
    return parsed


def adopter_code_correctness_gaps(
    root: Path | None, *, tree_ref: str | None = None
) -> tuple[str, ...]:
    """Completeness gaps for an adopter's native code-correctness proof surface.

    Beyond "declared non-empty" (the old single check), this verifies the declared gates
    are genuinely code-correctness-EQUIVALENT, not merely present. For each required axis
    (behavior, static-analysis) the adopter must MAP a native gate or WAIVE with a reason;
    a mapped gate must be adopter-authored, attribute to the axis via its kind/dimensions,
    be trust-bearing with promotion-grade evidence, carry a non-degenerate command, and be
    distinct from the gate mapped to any other axis.

    This is a COMPLETENESS dimension (surfaced via promotion_completeness_gaps), never the
    executable floor. It makes washing an explicit, digest-bound, diff-auditable lie; it
    cannot detect an honest-shaped semantic no-op (a real-looking harness over zero checks)
    — that residual closes via governed profile-diff review and DR-0006 re-execution.
    """
    if not adopter_profile_active(root, tree_ref=tree_ref):
        return ()
    assert root is not None
    profile = load_repository_profile(root, tree_ref=tree_ref)
    proof = cast("RepositoryProfileDeclaration", profile.declaration).proof
    if not proof.code_correctness_gates:
        return (ADOPTER_MISSING_CODE_CORRECTNESS_GATE,)
    overlay, _ = _adopter_gate_overlay(root, _product_gate_registry(), tree_ref=tree_ref)
    vocab = _code_correctness_axis_vocab(profile)
    mapping = _code_correctness_map(profile)
    gaps: list[str] = []
    used_gate_ids: set[str] = set()
    for axis in REQUIRED_CODE_CORRECTNESS_AXES:
        entry = mapping.get(axis)
        if entry is None:
            gaps.append(f"adopter_code_correctness_axis_unmapped:{axis}")
            continue
        if "waived" in entry:
            continue  # explicit, reason-bearing, digest-bound waiver
        gate_id = entry["gate"]
        gate = overlay.get(gate_id)
        if gate is None:
            gaps.append(f"adopter_code_correctness_axis_gate_missing:{axis}:{gate_id}")
            continue
        if gate_id in used_gate_ids:
            gaps.append(f"adopter_code_correctness_axis_gate_reused:{axis}:{gate_id}")
            continue
        if not _qualifies_for_axis(gate, axis, vocab):
            gaps.append(f"adopter_code_correctness_axis_unbacked:{axis}:{gate_id}")
            continue
        used_gate_ids.add(gate_id)
    return tuple(dict.fromkeys(gaps))


def default_gate_ids(
    *, full: bool = False, root: Path | None = None, tree_ref: str | None = None
) -> tuple[str, ...]:
    if adopter_profile_active(root, tree_ref=tree_ref):
        # Adopted repositories expose their proof depth through `.ethos/profile.toml`
        # and repository-native gates. The product code-correctness floor must not
        # assume product-owned `tools/ci/scripts/*` exist in every adopter — but the
        # adopter's DECLARED native code-correctness gates join the executable floor so
        # promotion completeness requires them. The "declared none" case, and the
        # axis-coverage/equivalence checks, are enforced by adopter_code_correctness_gaps
        # (completeness gaps), NOT by a non-executable sentinel here — this set must stay
        # registry-executable for gate_plan.
        assert root is not None
        profile = load_repository_profile(root, tree_ref=tree_ref)
        native = cast(
            "RepositoryProfileDeclaration", profile.declaration
        ).proof.code_correctness_gates
        return (*ADOPTER_DEFAULT_GATE_IDS, *native)
    if full:
        return PRODUCT_FULL_GATE_IDS
    # The product default proof floor is the CODE-CORRECTNESS core (tests + lint +
    # types) alongside governance self-checks. "proven" must mean the ETHOS product
    # code actually passes; adopter roots get the profile floor above instead.
    return PRODUCT_DEFAULT_GATE_IDS


_PYTHON_INTERPRETER_RE = re.compile(r"^python(3(\.\d+)?)?$")


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Collapse the host python-interpreter path in a gate command to the literal
    `"python"`, leaving every other token verbatim.

    A gate's command embeds `sys.executable` at registry-build time (gate_registry does
    `python = sys.executable`), so the SAME gate records a different absolute interpreter
    path on every host/venv. The policy identity must be stable across environments
    (B10): only the interpreter BASENAME family is normalized, unconditionally — never
    gated on equality to the live sys.executable, since the recording interpreter differs
    from the validating interpreter in exactly the cross-environment case B10 exercises.
    Repo-relative script tokens (tools/ci/scripts/*.sh) are kept verbatim so a command
    change (B11) or a script-content change (B12, via policy_source_digest) still moves
    the digest.
    """
    if not command:
        return command
    head, *rest = command
    if _PYTHON_INTERPRETER_RE.match(Path(head).name):
        return ("python", *rest)
    return command


def _committed_blob(root: Path, tree_ref: str, path: str) -> bytes | None:
    """Return `path`'s bytes from the committed tree `tree_ref`, or None if absent.

    `git cat-file blob <tree_ref>:<path>` reads the object store, so the result is a pure
    function of the commit — independent of the working tree the caller happens to be in.
    A missing blob, a non-file object, or any git error maps to None (the caller then
    falls back to a working-tree read or an empty contribution).
    """
    completed = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", f"{tree_ref}:{path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    stdout = completed.stdout
    # capture_output without text= yields bytes for real git; be robust if a caller/test
    # configured text mode (str) so the digest hashes bytes uniformly either way.
    return stdout.encode("utf-8") if isinstance(stdout, str) else stdout


def _committed_registry_and_floor(
    root: Path, tree_ref: str
) -> tuple[dict[str, GateDescriptor], tuple[str, ...]] | None:
    """Compile the gate registry and product floor from `tree_ref`'s `system/gates.toml`.

    The registry declaration is import-cached from cwd at module load, so a promoted
    commit that changed `system/gates.toml` (a gate's command/classification, or the
    proof floor) is invisible to the live `gate_registry()`. For committed-tree digests
    the declaration itself must come from the promoted tree. Returns None (caller falls
    back to the live registry) when the blob is absent or does not parse — the ADOPTER
    floor is not resolved here (it needs the profile), so committed mode only overrides
    the product floor; an adopter root passes tree_ref=None.
    """
    blob = _committed_blob(root, tree_ref, DECLARATION_PATH.as_posix())
    if blob is None:
        return None
    try:
        declaration = GateRegistryDeclaration.model_validate(tomllib.loads(blob.decode("utf-8")))
    except (tomllib.TOMLDecodeError, ValueError, UnicodeDecodeError):
        return None
    return (
        declaration.registry("runtime", python_executable=sys.executable),
        declaration.proof_sets.product_default,
    )


def committed_product_default_gate_ids(root: Path, tree_ref: str) -> tuple[str, ...] | None:
    """Return a product promotion floor from the immutable ``tree_ref`` declaration.

    A local closeout runner is deliberately sourced from accepted truth while it
    audits a candidate checkout.  Its import-time declaration can therefore be
    older than the candidate's ``system/gates.toml``.  Completeness must range
    over the candidate tree's declared floor, just as the policy digest already
    does; otherwise a candidate that legitimately removes a default gate is
    rechecked against the incumbent floor and cannot be closed out.
    """
    committed = _committed_registry_and_floor(root, tree_ref)
    return committed[1] if committed is not None else None


def _policy_registry_and_required(
    root: Path, tree_ref: str | None
) -> tuple[dict[str, GateDescriptor], tuple[str, ...]]:
    """Resolve the (registry, required-floor) pair the policy digest ranges over.

    Working-tree mode (tree_ref=None) uses the live registry and this root's floor
    (product or adopter). Committed mode resolves BOTH from `tree_ref`'s tracked
    declaration for a PRODUCT root, so the digest describes the promoted tree; an adopter
    root (whose floor depends on the working-tree profile) or an unresolvable declaration
    falls back to the live registry + this root's floor.
    """
    if tree_ref is not None and is_product_root(root):
        committed = _committed_registry_and_floor(root, tree_ref)
        if committed is not None:
            return committed
    return (
        gate_registry(root, tree_ref=tree_ref),
        default_gate_ids(full=False, root=root, tree_ref=tree_ref),
    )


def _gate_policy_source_digest(
    gate: GateDescriptor, root: Path, tree_ref: str | None = None
) -> str:
    """Digest repository-owned adapter or provider source for one gate.

    B12: a gate whose command is a repo-relative script (same path, tampered content)
    must change the policy digest. In-process gates (python -m ethos.cli ...) and the
    `ethos` entrypoint carry no repo-owned script, so they contribute ''.

    When ``tree_ref`` is given the script bytes are read from that COMMITTED git tree
    (``git cat-file blob <tree_ref>:<path>``), not the working tree. This is load-bearing
    for the reference-transaction hook: it fires while the accepted worktree still holds
    the OLD tree (the sync `reset` runs after the ref move), yet the digest must describe
    the tree being PROMOTED. Reading committed bytes keyed on the promoted head makes the
    digest a pure function of that immutable tree, so a proof stamped for head H and the
    hook validating a move to H compute the SAME digest regardless of which worktree runs.
    Falls back to the working tree when no tree_ref is given or the blob is unresolvable.
    """
    paths = list(_provider_source_paths(gate.providers))
    canonical = canonical_gate_command(gate.command)
    if canonical and canonical[0] not in ("python", "ethos") and "/" in canonical[0]:
        paths.append(canonical[0])
    sources: list[bytes] = []
    for path in paths:
        blob = _committed_blob(root, tree_ref, path) if tree_ref is not None else None
        live_path = root / path
        source = (
            blob if blob is not None else live_path.read_bytes() if live_path.is_file() else None
        )
        if source is not None:
            sources.append(path.encode("utf-8") + b"\0" + source)
    return hashlib.sha256(b"\0".join(sources)).hexdigest() if sources else ""


def _provider_source_paths(providers: tuple[str, ...]) -> tuple[str, ...]:
    """Map declared product provider modules to their tracked Python sources."""
    return tuple(
        f"src/{reference.partition(':')[0].replace('.', '/')}.py" for reference in providers
    )


def gate_execution_identity(gate: GateDescriptor) -> tuple[str, ...]:
    """Return the stable executed adapter identity recorded in proof evidence."""
    return canonical_gate_command(gate.command) if gate.command else ("provider", *gate.providers)


def gate_policy_fields(
    gate: GateDescriptor, root: Path, *, tree_ref: str | None = None
) -> dict[str, object]:
    """The cross-environment-stable policy identity of a single gate."""
    return {
        "gate_id": gate.id,
        "execution_identity": list(gate_execution_identity(gate)),
        "trust_bearing": gate.trust_bearing,
        "evidence_class": gate.evidence_class,
        "execution_mode": gate.execution_mode,
        "tool_adapter": gate.tool_adapter,
        "policy_source_digest": _gate_policy_source_digest(gate, root, tree_ref),
        "profile_binding": gate.profile,
        "layer": gate.kind,
    }


def gate_policy_digest(root: Path, *, tree_ref: str | None = None) -> str:
    """A stable digest of the required gate set's policy identity for `root`.

    Binds a proof/marker to WHAT the required gates ARE (canonical command, trust
    classification, evidence class, script content, …), not just to the proof's own
    bytes. If a gate's canonical command or classification changes, or a script gate's
    content is tampered, this digest changes and an old proof is stale (B11/B12); a mere
    interpreter-path change does not (B10). Covers the registry-resolvable required ids
    in floor order, including typed repository-native adopter descriptors.

    ``tree_ref`` selects COMMITTED-tree resolution (the registry declaration, required
    floor, and gate scripts are all read from that git tree) so the digest describes the
    tree being promoted rather than whichever worktree happens to invoke it. Without it,
    the working tree is read (the prove/stamp path, where the clean lane HEAD equals the
    working tree). See `_gate_policy_source_digest` for why the hook needs committed reads.
    """
    registry, required = _policy_registry_and_required(root, tree_ref)
    selected_ids = set(required)
    product = is_product_root(root)
    fields = [
        {
            **gate_policy_fields(registry[gate_id], root, tree_ref=tree_ref),
            "effective_dependencies": list(
                effective_gate_dependencies(registry[gate_id], selected_ids, product=product)
            ),
        }
        for gate_id in required
        if gate_id in registry
    ]
    canonical = json.dumps({"gates": fields}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def gate_policy_conformance_gaps(
    runs: object, root: Path, *, tree_ref: str | None = None
) -> list[str]:
    """Gaps where an executed run does not conform to its gate's policy identity.

    Defeats a same-UID forged proof that covers the required action_ids with runs that
    never ran the real gate: a `command=('/bin/true',)` run, or a run mislabeled
    `trust_bearing`/`evidence_class`. For each required gate present in the registry,
    the matching run's CANONICAL command must equal the gate's canonical command
    (canonical-to-canonical, so a legitimate interpreter difference is not flagged) and
    its trust_bearing/evidence_class must match the gate definition. ``tree_ref`` resolves
    the registry and required floor from that committed tree (see `gate_policy_digest`).
    """
    if not isinstance(runs, list):
        return []
    by_action: dict[str, dict[str, object]] = {}
    for run in runs:
        if isinstance(run, dict):
            payload = string_mapping(run)
            by_action.setdefault(str(payload.get("action_id", "")), payload)
    registry, required = _policy_registry_and_required(root, tree_ref)
    gaps: list[str] = []
    for gate_id in required:
        gate = registry.get(gate_id)
        if gate is None:
            continue
        run = by_action.get(gate_id)
        if run is None:
            continue  # absence is the completeness check's concern, not conformance
        run_command = run.get("command")
        command = (
            tuple(str(token) for token in run_command)
            if isinstance(run_command, (list, tuple))
            else ()
        )
        conforms = (
            canonical_gate_command(command) == gate_execution_identity(gate)
            and run.get("trust_bearing") == gate.trust_bearing
            and run.get("evidence_class") == gate.evidence_class
        )
        if not conforms:
            gaps.append(f"proof_gate_not_policy_conformant:{gate_id}")
    return gaps


def effective_gate_dependencies(
    gate: GateDescriptor, selected_ids: set[str], *, product: bool
) -> tuple[str, ...]:
    """Return a gate's selected-proof dependencies after product composition."""
    if product and gate.id == "generated-artifacts":
        return gate.depends_on + tuple(
            gate_id
            for gate_id in ("unit-architecture", "ruff")
            if gate_id in selected_ids and gate_id not in gate.depends_on
        )
    return gate.depends_on


def gate_nodes(
    gate_ids: tuple[str, ...] = (),
    *,
    full: bool = False,
    root: Path | None = None,
    tree_ref: str | None = None,
) -> tuple[tuple[PlanNode, ...], tuple[str, ...]]:
    registry = gate_registry(root, tree_ref=tree_ref)
    selected = gate_ids or default_gate_ids(full=full, root=root, tree_ref=tree_ref)
    selected_ids = set(selected)
    product = root is None or is_product_root(root)
    declaration_gaps = list(adopter_gate_descriptor_gaps(root, tree_ref=tree_ref))
    nodes: list[PlanNode] = []
    for gate_id in selected:
        gate = registry.get(gate_id)
        if gate is None:
            expected_gap = f"adopter_gate_descriptor_missing:{gate_id}"
            if expected_gap not in declaration_gaps:
                declaration_gaps.append(f"unknown_gate:{gate_id}")
            continue
        node = PlanNode(
            id=gate.id,
            kind="check",
            command=gate.command,
            depends_on=gate.depends_on,
        )
        effective_dependencies = effective_gate_dependencies(gate, selected_ids, product=product)
        if effective_dependencies != node.depends_on:
            node = node.model_copy(update={"depends_on": effective_dependencies})
        nodes.append(node)
    return tuple(nodes), tuple(dict.fromkeys(declaration_gaps))
