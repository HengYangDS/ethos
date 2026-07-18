from __future__ import annotations

from pathlib import Path

from ethos.repository.profile import load_repository_profile


def profile_identity(repo: Path) -> str:
    """Return the repository profile id used for adopter-specific parity, if any."""
    profile = load_repository_profile(repo)
    return profile.identity.get("profile_id", "")


def adopter_product_root(
    repo: Path, status_payload: dict[str, object], explicit_product_root: Path | None
) -> Path:
    """Resolve the external product root used for adopter shadow parity."""
    if explicit_product_root is not None:
        return explicit_product_root.resolve()
    runtime = status_payload.get("runtime_binding")
    if isinstance(runtime, dict):
        runner_source_root = str(runtime.get("runner_source_root") or "")
        if runner_source_root:
            runner_root = Path(runner_source_root).resolve()
            if runner_root != repo.resolve():
                return runner_root
    profile = load_repository_profile(repo)
    external_backend = profile.tables.get("external_backend", {})
    configured = external_backend.get("product_root")
    if isinstance(configured, str) and configured:
        return (repo / configured).resolve()
    return repo.resolve()


def parity_scope(
    *,
    product_profile: bool,
    adopter: str,
    generic_gap_count: int,
    adopter_gap_count: int,
) -> dict[str, object]:
    if product_profile or not adopter:
        return {
            "generic_gap_count": generic_gap_count,
            "domain_profile_parity_closed": False,
            "note": (
                "Generic command parity does not claim domain profile parity "
                "or adopter-specific retirement readiness."
            ),
        }
    return {
        "generic_gap_count": generic_gap_count,
        "adopter": adopter,
        "adopter_gap_count": adopter_gap_count,
        "domain_profile_parity_closed": adopter_gap_count == 0,
        "note": (
            "Adopter shadow parity is profile-specific evidence. Generic command parity "
            "remains a product migration signal and does not block adopter report routing."
        ),
    }
