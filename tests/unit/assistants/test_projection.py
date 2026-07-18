from __future__ import annotations

from ethos.assistants.mcp import mcp_manifest
from ethos.assistants.projections import projection_contract


def test_mcp_manifest_exposes_resources_prompts_and_tools() -> None:
    manifest = mcp_manifest()

    assert {"resources", "prompts", "tools"} <= set(manifest)
    assert "ethos.status" in manifest["tools"]
    assert manifest["tools"]["ethos.status"]["capability"] == "mcp_tool_readonly"
    assert "ethos.prove" not in manifest["tools"]
    assert {tool["capability"] for tool in manifest["tools"].values()} == {"mcp_tool_readonly"}
    assert manifest["resources"]["ethos://docs/index"]["capability"] == "mcp_resource"
    assert manifest["prompts"]["ethos.campaign-review"]["capability"] == "mcp_prompt"
    assert "ethos://docs/index" in manifest["resources"]


def test_projection_contract_is_thin_adapter() -> None:
    contract = projection_contract()

    assert contract["truth"] == "repository-source-and-contracts"
    assert "mcp" in contract["surfaces"]
