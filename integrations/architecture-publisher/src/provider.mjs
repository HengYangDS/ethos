/** Materialize ETHOS-owned standard values; Publisher owns every later stage. */
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fail, writeSourceBundle } from "architecture-publisher/source";
import { exact, validateClaimModel } from "architecture-publisher/semantics";
import { compileEditionEvolution, validateEdition } from "architecture-publisher/edition";
import { validateEthosMembers } from "./adapter/projection.mjs";
import { ethosClaimModel } from "./adapter/semantics.mjs";
import { createEthosEdition } from "./edition/evolution.mjs";

/** Consume the standard request already admitted by Publisher's Provider owner. */
export async function materializeEditionProvider(request) {
  if (
    request.inputs.length !== 1 ||
    request.inputs[0].id !== "edition" ||
    request.inputs[0].mediaType !== "application/json"
  )
    fail("ethos_provider_input_selection_invalid");
  const input = JSON.parse(Buffer.from(request.inputs[0].contentBase64, "base64").toString("utf8"));
  if (!exact(input, ["source", "projectionDigest", "members", "selection", "evolution"]))
    fail("ethos_provider_input_fields_invalid");
  if (input.source.id !== request.subject.id || input.source.revision !== request.subject.revision)
    fail("ethos_provider_subject_mismatch");
  const members = input.members.map(({ path: name, contentBase64 }) => ({
    path: name,
    content: Buffer.from(contentBase64, "base64"),
  }));
  const { projection } = validateEthosMembers(
    { source: input.source, members },
    input.projectionDigest,
  );
  const model = validateClaimModel(ethosClaimModel(projection));
  const semanticMember = "semantics/claim-model.json";
  members.push({ path: semanticMember, content: Buffer.from(JSON.stringify(model)) });
  if (input.evolution !== null) compileEditionEvolution(input.evolution);
  const scratch = await fs.mkdtemp(
    path.join(await fs.realpath(os.tmpdir()), "ethos-edition-provider-"),
  );
  try {
    const source = await writeSourceBundle(path.join(scratch, "source"), input.source, members);
    const edition = validateEdition(
      model,
      createEthosEdition(projection, source.manifestSha256, input.selection),
    );
    const encoded = (value) => ({
      contentBase64: Buffer.from(JSON.stringify(value)).toString("base64"),
    });
    return {
      schema: "architecture.edition-provider-reply/v1",
      source: {
        ...input.source,
        members: members.map(({ path: name, content }) => ({
          path: name,
          contentBase64: content.toString("base64"),
        })),
      },
      semanticMember,
      edition: encoded(edition),
      evolution: input.evolution === null ? null : encoded(input.evolution),
    };
  } finally {
    await fs.rm(scratch, { recursive: true, force: true });
  }
}
