/** Exercise the installed source-owned Provider through Publisher's public contract. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fixture, installPackages, sha256 } from "./support/publisher.mjs";

test("the installed ETHOS package exposes its sole Provider materializer", async (t) => {
  const { importPublic } = await installPackages(t);
  const provider = await importPublic("@architecture-publisher/ethos/provider");
  assert.deepEqual(Object.keys(provider), ["materializeEditionProvider"]);
});

test("the Provider preserves source meaning through isolated native materialization", async (t) => {
  const { project, integrationRoot, importPublic, adapter, sourceApi } = await installPackages(t);
  const provider = await importPublic("@architecture-publisher/ethos/provider");
  const protocol = await importPublic("architecture-publisher/provider");
  const semantics = await importPublic("architecture-publisher/semantics");
  const editions = await importPublic("architecture-publisher/edition");
  const original = fixture();
  const expected = adapter.ethosClaimModel(original.input);
  const claims = Object.keys(expected.claims);
  const selection = {
    static: { label: "Overview", nodes: ["attempt"], relations: ["retry"], claims },
    pages: [
      { id: "overview", label: "Overview", nodes: ["attempt"], relations: ["retry"], claims },
    ],
    narrative: ["overview"],
  };
  const value = {
    source: original.source,
    projectionDigest: original.input.digest,
    members: original.members.map(({ path: name, content }) => ({
      path: name,
      contentBase64: content.toString("base64"),
    })),
    selection,
    evolution: null,
  };
  const identity = { id: "ethos-provider", revision: "fixture" };
  const requestFor = (body) => {
    const bytes = Buffer.from(JSON.stringify(body));
    return protocol.validateProviderRequest({
      schema: "architecture.edition-provider-request/v1",
      provider: identity,
      subject: original.source,
      inputs: [
        {
          id: "edition",
          mediaType: "application/json",
          bytes: bytes.length,
          sha256: sha256(bytes),
          contentBase64: bytes.toString("base64"),
        },
      ],
    });
  };
  const request = requestFor(value);
  const reply = protocol.validateProviderReply(await provider.materializeEditionProvider(request));
  assert.deepEqual(await provider.materializeEditionProvider(request), reply);
  assert.deepEqual(request, requestFor(value));
  const members = reply.source.members.map(({ path: name, contentBase64 }) => ({
    path: name,
    content: Buffer.from(contentBase64, "base64"),
  }));
  const model = JSON.parse(members.find((member) => member.path === reply.semanticMember).content);
  assert.deepEqual(model, expected);
  assert.equal(model.relations.retry.qualifiers.attributes.condition, "transient failure");
  const source = await sourceApi.writeSourceBundle(
    path.join(project, "expected"),
    original.source,
    members,
  );
  const edition = editions.validateEdition(
    model,
    JSON.parse(Buffer.from(reply.edition.contentBase64, "base64")),
  );
  assert.equal(edition.source.manifestSha256, source.manifestSha256);
  assert.deepEqual(edition.requiredClaims, claims.toSorted());
  assert.equal(reply.evolution, null);
  for (const changed of [
    { ...value, acceptance: "pass" },
    { ...value, source: { ...value.source, id: "foreign" } },
    { ...value, members: value.members.slice(1) },
    { ...value, projectionDigest: "0".repeat(64) },
  ])
    await assert.rejects(() => provider.materializeEditionProvider(requestFor(changed)));

  const bytes = Buffer.from(JSON.stringify(value));
  const inputFile = path.join(project, "edition-input.json");
  await fs.writeFile(inputFile, bytes);
  const packageBytes = await fs.readFile(path.join(integrationRoot, "package.json"));
  const packageInfo = JSON.parse(packageBytes);
  const manifest = {
    schema: "architecture.edition-provider/v1",
    provider: identity,
    subject: original.source,
    contracts: {
      sourceBundle: "architecture.source-bundle/v1",
      claimModel: "architecture.claim-model/v2",
      edition: "architecture.edition/v1",
      evolution: null,
    },
    delivery: {
      kind: "executable",
      package: {
        name: packageInfo.name,
        version: packageInfo.version,
        packageJsonSha256: sha256(packageBytes),
        contentSha256: await protocol.editionProviderPackageDigest(integrationRoot),
        entrypoint: "./provider",
      },
      inputs: [
        {
          id: "edition",
          path: "edition-input.json",
          mediaType: "application/json",
          bytes: bytes.length,
          sha256: sha256(bytes),
        },
      ],
    },
    expected: {
      sourceManifestSha256: source.manifestSha256,
      claimModelDigest: semantics.claimModelDigest(model),
      editionDigest: editions.editionDigest(model, edition),
      evolutionSha256: null,
    },
    limits: { inputs: 1, inputBytes: bytes.length, replyBytes: 1024 * 1024, timeoutMs: 10000 },
  };
  const manifestPath = path.join(project, "provider.json");
  const manifestBytes = Buffer.from(JSON.stringify(protocol.validateEditionProvider(manifest)));
  await fs.writeFile(manifestPath, manifestBytes);
  const actual = await protocol.materializeExecutableProvider(
    {
      providerManifest: manifestPath,
      providerManifestSha256: sha256(manifestBytes),
      providerPackageRoot: integrationRoot,
    },
    { verifyDeterminism: true },
  );
  assert.equal(actual.receipt.execution.deterministic, true);
  assert.equal(actual.receipt.execution.kind, "child-process");
  assert.deepEqual(actual.receipt.materialized, manifest.expected);
  const relocated = await installPackages(t);
  const relocatedManifest = path.join(relocated.project, "provider.json");
  await fs.writeFile(relocatedManifest, manifestBytes);
  await fs.copyFile(inputFile, path.join(relocated.project, "edition-input.json"));
  const relocatedProtocol = await relocated.importPublic("architecture-publisher/provider");
  const repeated = await relocatedProtocol.materializeExecutableProvider(
    {
      providerManifest: relocatedManifest,
      providerManifestSha256: sha256(manifestBytes),
      providerPackageRoot: relocated.integrationRoot,
    },
    { verifyDeterminism: true },
  );
  assert.deepEqual(repeated.receipt.materialized, actual.receipt.materialized);
});
