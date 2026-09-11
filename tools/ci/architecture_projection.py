"""Native architecture projection command over the shared producer owner."""

import json
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head
from ethos.repository.policy.projections import observe_projections
from ethos.repository.policy.projections import render_architecture

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/architecture/projection.toml"


def render(source_rel: str) -> str:
    """Render through the producer shared with admission."""
    return render_architecture(source_rel, (ROOT / source_rel).read_text(encoding="utf-8"))


def main() -> int:
    failures: list[dict[str, str]] = []
    projections: list[dict[str, object]] = []
    for relation in observe_projections(ROOT):
        if relation.declaration != CONFIG_PATH.relative_to(ROOT).as_posix():
            continue
        source, output = relation.source, relation.output
        expected = render(source)
        output_path = ROOT / output
        actual = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
        matches = actual == expected
        if not matches:
            failures.append({"id": output, "reason": f"projection drift: {output}"})
        projections.append(
            {
                "id": output,
                "source": source,
                "output": output,
                "matches": matches,
                "truth_boundary": "generated projection, not intent authority",
            }
        )
    payload = {
        "schema_version": 1,
        "kind": "ethos_architecture_projection_drift",
        "verdict": "block" if failures else "pass",
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "projections": projections,
        "failures": failures,
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
