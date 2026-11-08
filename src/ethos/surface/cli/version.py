"""Public human and machine renderings of the invoking build identity."""

from __future__ import annotations

import json
import sys

from ethos.application.result_projection import version_result
from ethos.application.result_projection import with_runtime


def version_text() -> str:
    """Render one identity result for Cyclopts' built-in version surface.

    The human line reads only the identity result, so it never reads the committed build.
    """
    result = version_result()
    if "--json" in sys.argv[1:]:
        payload = with_runtime(result).to_dict()
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    identity = result.data["identity"]
    source_commit = str(identity["source_commit"]) if isinstance(identity, dict) else ""
    return (
        f"ethos {result.summary['product_version']} "
        f"({result.summary['distribution_version']}; {source_commit[:12]}; "
        f"OpenSpec {result.data['openspec_version']})"
    )
