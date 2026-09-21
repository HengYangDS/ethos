import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const SOURCE_ROOT = path.resolve(import.meta.dirname, "..", "..");

function stable(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  return `{${Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stable(value[key])}`)
    .join(",")}}`;
}

async function selectedArchive(name) {
  const selected = process.env[name];
  assert.equal(path.isAbsolute(selected ?? ""), true, `${name} must be an absolute path`);
  const stat = await fs.lstat(selected);
  assert.equal(stat.isFile() && !stat.isSymbolicLink(), true, `${name} must be a regular file`);
  return selected;
}

async function selectedPath(name, { directory = false } = {}) {
  const selected = process.env[name];
  assert.equal(path.isAbsolute(selected ?? ""), true, `${name} must be an absolute path`);
  const stat = await fs.lstat(selected);
  assert.equal(
    directory ? stat.isDirectory() : stat.isFile() && !stat.isSymbolicLink(),
    true,
    `${name} must identify the expected local input`,
  );
  return selected;
}

async function installPackages(
  t,
  integrationArchiveVariable = "ETHOS_ARCHITECTURE_PUBLISHER_PACKAGE",
) {
  const coreArchive = await selectedArchive("ARCHITECTURE_PUBLISHER_PACKAGE");
  const ethosArchive = await selectedArchive(integrationArchiveVariable);
  const root = await fs.realpath(
    await fs.mkdtemp(path.join(tmpdir(), "ethos-architecture-publisher-installed-")),
  );
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  const project = path.join(root, "consumer");
  const home = path.join(root, "home");
  const cache = path.join(root, "npm-cache");
  await fs.mkdir(project);
  await fs.mkdir(home);
  await fs.writeFile(
    path.join(project, "package.json"),
    JSON.stringify({ private: true, type: "module" }),
  );
  const installed = spawnSync(
    "npm",
    [
      "install",
      "--offline",
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      "--package-lock=false",
      coreArchive,
      ethosArchive,
    ],
    {
      cwd: project,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: home,
        npm_config_cache: cache,
        npm_config_offline: "true",
        npm_config_registry: "http://127.0.0.1:9/",
        npm_config_update_notifier: "false",
      },
    },
  );
  assert.equal(installed.status, 0, installed.stderr);
  const coreRoot = path.join(project, "node_modules", "architecture-publisher");
  const integrationRoot = path.join(project, "node_modules", "@architecture-publisher", "ethos");
  return {
    project,
    coreRoot,
    integrationRoot,
    sourceApi: await import(pathToFileURL(path.join(coreRoot, "src", "source", "index.mjs")).href),
    adapter: await import(
      pathToFileURL(path.join(integrationRoot, "src", "adapter", "index.mjs")).href
    ),
    edition: await import(
      pathToFileURL(path.join(integrationRoot, "src", "edition", "index.mjs")).href
    ),
    runtime: await import(pathToFileURL(path.join(integrationRoot, "src", "runtime.mjs")).href),
  };
}

function fixture() {
  const commit = "1".repeat(40);
  const tree = "2".repeat(40);
  const graph = {
    schema: "synthetic",
    nodes: {},
    edges: [],
    invariants: [{ statement: "All attempts preserve scope" }],
  };
  const copy = { assertions: { maturity: { text: "Target design, not implementation" } } };
  const view = { node_projection: {}, omitted_nodes: {} };
  const quality = '{"schema":"synthetic-test-only","authority":{"consumers_may_override":false}}\n';
  const selected = {
    copy: "system/copy.json",
    quality_contract: "system/quality.json",
    semantic_graph: "system/graph.json",
    view_profile: "system/view.json",
  };
  const contents = {
    "docs/contract.md": Buffer.from("All attempts MAY retry only after transient failure.\n"),
    "system/copy.json": Buffer.from(JSON.stringify(copy)),
    "system/quality.json": Buffer.from(quality),
    "system/graph.json": Buffer.from(JSON.stringify(graph)),
    "system/view.json": Buffer.from(JSON.stringify(view)),
  };
  const binding = {
    id: "contract",
    path: "docs/contract.md",
    sha256: sha256(contents["docs/contract.md"]),
    authority: "synthetic test meaning",
  };
  const declaration = {
    schema: "ethos.projection-declaration/v1",
    id: "synthetic-ethos-contract",
    title: "Synthetic contract",
    authority: {
      semantic_owner: "docs/contract.md",
      scope: "test only",
      effect_authority: false,
    },
    sources: [{ id: binding.id, path: binding.path, authority: binding.authority }],
    documents: selected,
  };
  const input = {
    schema: "projection.input/v2",
    title: declaration.title,
    authority: declaration.authority,
    source: {
      id: declaration.id,
      revision: commit,
      git: { commit, tree },
      bindings: [binding],
      documents: Object.entries(selected).map(([id, sourcePath]) => ({
        id,
        path: sourcePath,
        sha256: sha256(contents[sourcePath]),
      })),
    },
    documents: { copy, view_profile: view, quality_contract: quality },
    semantics: {
      nodes: {
        attempt: {
          label: "Attempt",
          kind: "subject",
          attributes: { quantifier: "All", maturity: "target" },
          provenance: ["contract"],
        },
      },
      relations: [
        {
          id: "retry",
          from: "attempt",
          to: "attempt",
          kind: "retry",
          attributes: { condition: "transient failure", quantifier: "Any", scope: "attempt" },
          provenance: ["contract"],
        },
      ],
      contracts: { invariants: graph.invariants },
    },
    view: {
      nodes: { attempt: { project: { witness: "maturity" } } },
      relations: { retry: { project: { witness: "maturity" } } },
    },
  };
  const members = [
    { path: "source/LICENSE", content: Buffer.from("Synthetic fixture license notice\n") },
    { path: "projection-input.json", content: Buffer.alloc(0) },
    {
      path: "source/system/projections/terminal-architecture/declaration.json",
      content: Buffer.from(JSON.stringify(declaration)),
    },
    {
      path: "source/tools/projection/export_terminal_architecture.py",
      content: Buffer.from("# Synthetic exporter fixture; never official ETHOS evidence\n"),
    },
    {
      path: "source/src/ethos/repository/policy/projections.py",
      content: Buffer.from("# Synthetic policy owner fixture\n"),
    },
    ...Object.entries(contents).map(([memberPath, content]) => ({
      path: `source/${memberPath}`,
      content,
    })),
  ];
  const refresh = () => {
    delete input.digest;
    input.digest = sha256(`${stable(input)}\n`);
    members.find(({ path: memberPath }) => memberPath === "projection-input.json").content =
      Buffer.from(JSON.stringify(input));
  };
  refresh();
  return { input, members, refresh, source: { id: input.source.id, revision: commit } };
}

test("independently packed integration consumes explicit projection input offline", async (t) => {
  const { project, integrationRoot, sourceApi, adapter, edition, runtime } =
    await installPackages(t);
  const value = fixture();
  const written = await sourceApi.writeSourceBundle(
    path.join(project, "source-bundle"),
    value.source,
    value.members,
  );
  const read = await adapter.readEthosSource(
    written.manifestPath,
    written.manifestSha256,
    value.input.digest,
  );
  const claimModel = adapter.ethosClaimModel(read.projection);

  assert.deepEqual(read.projection, value.input);
  assert.equal(read.officialReplay, "not-performed");
  assert.equal(read.semanticAcceptance, "not-performed");
  assert.equal(claimModel.schema, "architecture.claim-model/v2");
  assert.equal(claimModel.owner, "synthetic-ethos-contract");
  assert.equal(claimModel.entities.attempt.label, "Attempt");
  assert.equal(claimModel.relations.retry.qualifiers.attributes.condition, "transient failure");
  const forbiddenAuthority = new Set([
    "attestation",
    "cas",
    "commitment",
    "govern",
    "lane",
    "permission",
    "proof",
  ]);
  assert.deepEqual(
    [...Object.keys(adapter), ...Object.keys(edition)].filter((name) =>
      (name.match(/[A-Z]?[a-z]+|[A-Z]+(?![a-z])/g) ?? [])
        .map((word) => word.toLowerCase())
        .some((word) => forbiddenAuthority.has(word)),
    ),
    [],
  );
  await assert.rejects(adapter.readEthosSource(written.manifestPath, written.manifestSha256), {
    code: "projection_digest_required",
  });
  value.input.authority.effect_authority = true;
  value.refresh();
  assert.throws(() => adapter.ethosClaimModel(value.input), {
    code: "projection_authority_invalid",
  });

  const closure = await runtime.readEthosExtensionRuntime();
  assert.equal(
    closure.every(({ file }) => file.startsWith(`${integrationRoot}/`)),
    true,
  );
  assert.equal(
    closure.some(({ path: memberPath }) => memberPath === "package.json"),
    true,
  );
});

test("accepted ETHOS source is an explicit semantic successor of the packaged Edition", async (t) => {
  const repository = await selectedPath("ETHOS_REPOSITORY", { directory: true });
  const git = await selectedPath("ETHOS_GIT");
  const python = await selectedPath("ETHOS_PYTHON");
  const xcrun = await selectedPath("ETHOS_XCRUN");
  const staticSansFont = await selectedPath("ETHOS_STATIC_SANS_FONT");
  const baseline = JSON.parse(
    await fs.readFile(
      path.join(SOURCE_ROOT, "integrations", "architecture-publisher", "migration-baseline.json"),
      "utf8",
    ),
  );
  const { project, coreRoot, integrationRoot, sourceApi, adapter } = await installPackages(t);
  const svgApi = await import(
    pathToFileURL(path.join(coreRoot, "renderers", "svg", "index.mjs")).href
  );
  const qualificationApi = await import(
    pathToFileURL(path.join(coreRoot, "src", "qualification", "index.mjs")).href
  );
  const atlas = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "atlas.mjs")).href
  );
  const evolutionApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "evolution.mjs")).href
  );
  const candidateApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "candidate.mjs")).href
  );
  const posterApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "poster.mjs")).href
  );
  const standaloneApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "standalone.mjs")).href
  );
  const naturalOverviewApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "static", "natural-overview.mjs"))
      .href
  );
  const naturalSemanticsApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "static", "natural-semantics.mjs"))
      .href
  );
  const traceApi = await import(
    pathToFileURL(path.join(integrationRoot, "src", "edition", "static", "trace-scene.mjs")).href
  );
  const importProjection = (identity, name) =>
    adapter.importEthosSource({
      repository,
      revision: identity.commit,
      projectionDigest: identity.projectionDigest,
      exporterSha256: identity.exporterSha256,
      ownerSha256: identity.ownerSha256,
      git,
      python,
      output: path.join(project, name),
    });
  const beforeImport = await importProjection(baseline.ethos.editionSource, "edition-source");
  const afterImport = await importProjection(
    baseline.ethos.terminalAcceptedProjection,
    "accepted-source",
  );
  assert.equal(beforeImport.manifestSha256, baseline.ethos.editionSource.sourceManifestSha256);
  assert.equal(beforeImport.officialReplay, "performed");
  assert.equal(afterImport.officialReplay, "performed");
  assert.notEqual(beforeImport.manifestSha256, afterImport.manifestSha256);

  const editionManifest = path.join(
    integrationRoot,
    "src",
    "edition",
    "authoring",
    "manifest.json",
  );
  const beforeSelection = await atlas.readEthosAtlasSelection({
    sourceManifest: beforeImport.manifestPath,
    sourceSha256: beforeImport.manifestSha256,
    projectionDigest: baseline.ethos.editionSource.projectionDigest,
    editionManifest,
    editionSha256: sha256(await fs.readFile(editionManifest)),
  });
  const afterSource = await adapter.readEthosSource(
    afterImport.manifestPath,
    afterImport.manifestSha256,
    baseline.ethos.terminalAcceptedProjection.projectionDigest,
  );
  const beforeDependencies = evolutionApi.selectEthosEditionDependencies(
    beforeSelection.source.projection,
    beforeSelection.pages,
    {},
  );
  const afterDependencies = evolutionApi.selectEthosEditionDependencies(
    afterSource.projection,
    beforeSelection.pages,
    {},
  );
  const evolution = evolutionApi.compileEthosEditionEvolution({
    before: {
      projection: beforeSelection.source.projection,
      sourceManifestSha256: beforeImport.manifestSha256,
      selection: beforeDependencies,
    },
    after: {
      projection: afterSource.projection,
      sourceManifestSha256: afterImport.manifestSha256,
      selection: afterDependencies,
    },
    correspondences: [],
  });

  assert.deepEqual(evolution.ethos.changed.nodes, [
    "adoption_exit",
    "candidate_base_stale",
    "mcp_a2a",
    "skills",
  ]);
  assert.deepEqual(evolution.ethos.changed.relations, ["candidate-state-to-independent"]);
  assert.deepEqual(evolution.ethos.changed.assertions, ["projection", "verification"]);
  assert.deepEqual(evolution.editions.affected[0].unrepresented, []);
  assert.equal(evolution.editions.affected[0].static, true);
  assert.equal(evolution.editions.affected[0].interactive.length, 13);
  assert.equal(evolution.obligations.humanReview.length, 6);
  assert.equal(evolution.obligations.acceptance[0].action, "reaccept");
  assert.equal(evolution.obligations.publication[0].action, "replace");

  const authoring = path.join(integrationRoot, "src", "edition", "refresh.json");
  const prepared = await candidateApi.prepareEthosCandidate({
    previous: {
      sourceManifest: beforeImport.manifestPath,
      sourceSha256: beforeImport.manifestSha256,
      projectionDigest: baseline.ethos.editionSource.projectionDigest,
      editionManifest,
      editionSha256: sha256(await fs.readFile(editionManifest)),
    },
    source: {
      sourceManifest: afterImport.manifestPath,
      sourceSha256: afterImport.manifestSha256,
      projectionDigest: baseline.ethos.terminalAcceptedProjection.projectionDigest,
    },
    authoring,
    authoringSha256: sha256(await fs.readFile(authoring)),
    output: path.join(project, "accepted-candidate"),
  });
  assert.equal(prepared.status, "prepared");
  assert.equal(prepared.pages, 13);
  assert.equal(prepared.semanticAcceptance, "not-performed");
  assert.deepEqual(prepared.evolution.ethos.changed, evolution.ethos.changed);
  assert.equal((await atlas.readEthosAtlasSelection(prepared.atlas)).pages.length, 13);

  const renderedAtlas = await atlas.renderEthosAtlas({
    ...prepared.atlas,
    output: path.join(project, "accepted-atlas"),
  });
  assert.equal(renderedAtlas.pages.length, 13);
  assert.equal(renderedAtlas.semanticAcceptance, "not-performed");
  const standalone = await standaloneApi.renderStandaloneAtlas({
    atlas: {
      ...prepared.atlas,
      outputManifest: path.join(renderedAtlas.output, "manifest.json"),
      outputSha256: renderedAtlas.manifestSha256,
    },
    output: path.join(project, "ETHOS-architecture.html"),
  });
  assert.equal(standalone.pages, 13);
  assert.equal(standalone.semanticAcceptance, "not-performed");

  const posterManifest = path.join(
    integrationRoot,
    "src",
    "edition",
    "static",
    "authoring",
    "manifest.json",
  );
  const posterBundle = await sourceApi.readSourceBundle(
    posterManifest,
    sha256(await fs.readFile(posterManifest)),
  );
  const posterMembers = new Map(
    posterBundle.members.map(({ path: memberPath, content }) => [memberPath, content]),
  );
  const posterEdition = JSON.parse(posterMembers.get("edition.json"));
  posterEdition.schema = "architecture.ethos-poster-candidate/v1";
  posterEdition.source = {
    commit: baseline.ethos.terminalAcceptedProjection.commit,
    projectionDigest: baseline.ethos.terminalAcceptedProjection.projectionDigest,
    manifestSha256: afterImport.manifestSha256,
  };
  delete posterEdition.expected;
  posterEdition.authoring = prepared.posterAuthoring;
  const select = (args) => {
    const result = spawnSync(xcrun, args, { encoding: "utf8", timeout: 30000 });
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  const compiler = select(["--find", "swiftc"]);
  const sdk = await fs.realpath(select(["--show-sdk-path"]));
  const requests = [
    ...prepared.posterAuthoring.carriers.edits.map(({ after: text }) => ({
      text,
      size: 12.5,
      font: "400",
    })),
    {
      text: [prepared.posterAuthoring.refresh.replay, prepared.posterAuthoring.refresh.merge].join(
        " · ",
      ),
      size: 12.5,
      font: "400",
    },
    { text: prepared.posterAuthoring.refresh.pending, size: 12.5, font: "400" },
    { text: "Refresh", size: 12.5, font: "600" },
    { text: "Pending", size: 12.5, font: "600" },
  ].filter(
    (request, index, all) =>
      all.findIndex(
        (candidate) =>
          candidate.text === request.text &&
          candidate.size === request.size &&
          candidate.font === request.font,
      ) === index,
  );
  const measured = await svgApi.measureCoreText({
    compiler: { path: compiler, sha256: sha256(await fs.readFile(compiler)) },
    sdk: {
      path: sdk,
      settingsSha256: sha256(await fs.readFile(path.join(sdk, "SDKSettings.json"))),
    },
    fonts: [
      {
        id: "400",
        path: staticSansFont,
        sha256: sha256(await fs.readFile(staticSansFont)),
        postscript: "AvenirNext-Regular",
        cascade: [],
      },
      {
        id: "600",
        path: staticSansFont,
        sha256: sha256(await fs.readFile(staticSansFont)),
        postscript: "AvenirNext-DemiBold",
        cascade: [],
      },
    ],
    requests,
    output: path.join(project, "fresh-static-metrics"),
  });
  assert.equal(measured.freshMeasurement, "performed");
  const acceptedMetrics = JSON.parse(posterMembers.get("metrics.json"));
  const freshMetrics = JSON.parse(
    await fs.readFile(path.join(project, "fresh-static-metrics", "metrics.json")),
  );
  const metricRecords = new Map([...acceptedMetrics.records, ...freshMetrics.records]);
  const candidateMetrics = {
    ...acceptedMetrics,
    provenance: {
      method: "recorded",
      environment:
        "Accepted historical metrics plus fresh CoreText measurements for this source-bound candidate.",
      fonts: [...new Set([...acceptedMetrics.provenance.fonts, ...freshMetrics.provenance.fonts])],
    },
    records: [...metricRecords].sort(([left], [right]) => left.localeCompare(right)),
  };
  posterMembers.set("metrics.json", Buffer.from(`${JSON.stringify(candidateMetrics, null, 2)}\n`));
  posterEdition.metricsSha256 = sha256(posterMembers.get("metrics.json"));
  posterMembers.set("edition.json", Buffer.from(`${JSON.stringify(posterEdition, null, 2)}\n`));
  const metricReader = svgApi.createMetricReader(candidateMetrics);
  const quality = JSON.parse(afterSource.projection.documents.quality_contract);
  const composition = naturalOverviewApi.composeNaturalOverview(
    afterSource.projection,
    metricReader.measure,
    quality,
    prepared.posterAuthoring,
    afterSource.sourceDocuments,
  );
  const scene = traceApi.compileTraceScene(composition.document, metricReader.measure);
  const svg = Buffer.from(traceApi.renderTraceSvg(scene));
  const geometry = quality.hard_gates.geometry_each_scale;
  const typography = quality.hard_gates.typography_and_accessibility;
  const sourceScale = quality.scales.find(({ name }) => name === "source");
  const qualification = {
    sourceBindings: naturalSemanticsApi.auditNaturalSemantics(
      composition,
      afterSource.projection,
      afterSource.sourceDocuments,
    ),
    separation: qualificationApi.auditNaturalSeparation(scene, composition.separation, quality),
    geometry: qualificationApi.auditScene(scene, {
      minimumFont: Math.max(
        typography.effective_font_px_min_at_reference,
        typography.source_font_px_min === undefined
          ? 0
          : (typography.source_font_px_min * scene.referenceWidth) / sourceScale.width,
      ),
      ownerClearance: geometry.inside_glyph_to_owner_inner_stroke_px_at_reference_min,
      textClearance: geometry.text_to_nonowner_geometry_clearance_px_at_reference_min,
      endpointTolerance: geometry.arrow_tip_error_px_max,
      minimumTerminal: geometry.arrow_terminal_straight_run_px_at_reference_min,
      widthGrowth: geometry.font_width_growth_fraction,
      heightGrowth: geometry.font_height_growth_fraction,
    }),
    emittedEdges: qualificationApi.auditEmittedEdges(svg.toString(), scene, {
      minimumTerminal: geometry.arrow_terminal_straight_run_px_at_reference_min,
      endpointTolerance: geometry.arrow_tip_error_px_max,
    }),
    canvas: qualificationApi.auditCanvasEnvelope(scene, quality),
  };
  assert.deepEqual(
    Object.fromEntries(
      Object.entries(qualification)
        .filter(([, value]) => value.failures.length)
        .map(([name, value]) => [name, value.failures]),
    ),
    {},
  );
  const writtenPoster = await sourceApi.writeSourceBundle(
    path.join(project, "poster-edition"),
    { id: "ethos:poster-authoring", revision: baseline.ethos.terminalAcceptedProjection.commit },
    [...posterMembers].map(([memberPath, content]) => ({ path: memberPath, content })),
  );
  const poster = await posterApi.renderEthosPoster({
    sourceManifest: afterImport.manifestPath,
    sourceSha256: afterImport.manifestSha256,
    projectionDigest: baseline.ethos.terminalAcceptedProjection.projectionDigest,
    editionManifest: writtenPoster.manifestPath,
    editionSha256: writtenPoster.manifestSha256,
    output: path.join(project, "accepted-poster"),
  });
  assert.equal(poster.mode, "candidate");
  assert.equal(poster.semanticAcceptance, "not-performed");
  assert.equal(
    Object.values(poster.checks).every(({ failures }) => failures.length === 0),
    true,
  );

  const acceptedSelection = {
    sourceManifest: beforeImport.manifestPath,
    sourceSha256: beforeImport.manifestSha256,
    projectionDigest: baseline.ethos.editionSource.projectionDigest,
    editionManifest,
    editionSha256: sha256(await fs.readFile(editionManifest)),
  };
  const sourceOwnedAcceptedAtlas = await atlas.renderEthosAtlas({
    ...acceptedSelection,
    output: path.join(project, "source-owned-accepted-atlas"),
  });
  const sourceOwnedAcceptedStandalone = await standaloneApi.renderStandaloneAtlas({
    atlas: {
      ...acceptedSelection,
      outputManifest: path.join(sourceOwnedAcceptedAtlas.output, "manifest.json"),
      outputSha256: sourceOwnedAcceptedAtlas.manifestSha256,
    },
    output: path.join(project, "source-owned-accepted.html"),
  });
  const acceptedPosterManifest = path.join(
    integrationRoot,
    "src",
    "edition",
    "static",
    "authoring",
    "manifest.json",
  );
  const sourceOwnedAcceptedPoster = await posterApi.renderEthosPoster({
    sourceManifest: beforeImport.manifestPath,
    sourceSha256: beforeImport.manifestSha256,
    projectionDigest: baseline.ethos.editionSource.projectionDigest,
    editionManifest: acceptedPosterManifest,
    editionSha256: sha256(await fs.readFile(acceptedPosterManifest)),
    output: path.join(project, "source-owned-accepted-poster"),
  });

  const sourceOwnedArchive = await selectedArchive("ETHOS_ARCHITECTURE_PUBLISHER_PACKAGE");
  const stagingArchive = await selectedArchive("PUBLISHER_STAGING_ETHOS_PACKAGE");
  assert.notEqual(await fs.realpath(sourceOwnedArchive), await fs.realpath(stagingArchive));
  assert.notEqual(
    sha256(await fs.readFile(sourceOwnedArchive)),
    sha256(await fs.readFile(stagingArchive)),
  );
  const staging = await installPackages(t, "PUBLISHER_STAGING_ETHOS_PACKAGE");
  const stagingAtlasApi = await import(
    pathToFileURL(path.join(staging.integrationRoot, "src", "edition", "atlas.mjs")).href
  );
  const stagingPosterApi = await import(
    pathToFileURL(path.join(staging.integrationRoot, "src", "edition", "poster.mjs")).href
  );
  const stagingStandaloneApi = await import(
    pathToFileURL(path.join(staging.integrationRoot, "src", "edition", "standalone.mjs")).href
  );
  const stagingCandidateApi = await import(
    pathToFileURL(path.join(staging.integrationRoot, "src", "edition", "candidate.mjs")).href
  );
  const stagingEditionManifest = path.join(
    staging.integrationRoot,
    "src",
    "edition",
    "authoring",
    "manifest.json",
  );
  const stagingSelection = {
    ...acceptedSelection,
    editionManifest: stagingEditionManifest,
    editionSha256: sha256(await fs.readFile(stagingEditionManifest)),
  };
  const stagingAcceptedAtlas = await stagingAtlasApi.renderEthosAtlas({
    ...stagingSelection,
    output: path.join(staging.project, "staging-accepted-atlas"),
  });
  const stagingAcceptedStandalone = await stagingStandaloneApi.renderStandaloneAtlas({
    atlas: {
      ...stagingSelection,
      outputManifest: path.join(stagingAcceptedAtlas.output, "manifest.json"),
      outputSha256: stagingAcceptedAtlas.manifestSha256,
    },
    output: path.join(staging.project, "staging-accepted.html"),
  });
  const stagingPosterManifest = path.join(
    staging.integrationRoot,
    "src",
    "edition",
    "static",
    "authoring",
    "manifest.json",
  );
  const stagingAcceptedPoster = await stagingPosterApi.renderEthosPoster({
    sourceManifest: beforeImport.manifestPath,
    sourceSha256: beforeImport.manifestSha256,
    projectionDigest: baseline.ethos.editionSource.projectionDigest,
    editionManifest: stagingPosterManifest,
    editionSha256: sha256(await fs.readFile(stagingPosterManifest)),
    output: path.join(staging.project, "staging-accepted-poster"),
  });
  assert.equal(stagingAcceptedAtlas.manifestSha256, sourceOwnedAcceptedAtlas.manifestSha256);
  assert.equal(stagingAcceptedStandalone.sha256, sourceOwnedAcceptedStandalone.sha256);
  assert.equal(stagingAcceptedPoster.svg.sha256, sourceOwnedAcceptedPoster.svg.sha256);
  assert.equal(stagingAcceptedPoster.sceneSha256, sourceOwnedAcceptedPoster.sceneSha256);
  assert.equal(
    stagingAcceptedPoster.output.manifestSha256,
    sourceOwnedAcceptedPoster.output.manifestSha256,
  );

  const stagingAuthoring = path.join(staging.integrationRoot, "src", "edition", "refresh.json");
  await assert.rejects(
    stagingCandidateApi.prepareEthosCandidate({
      previous: stagingSelection,
      source: {
        sourceManifest: afterImport.manifestPath,
        sourceSha256: afterImport.manifestSha256,
        projectionDigest: baseline.ethos.terminalAcceptedProjection.projectionDigest,
      },
      authoring: stagingAuthoring,
      authoringSha256: sha256(await fs.readFile(stagingAuthoring)),
      output: path.join(staging.project, "unsupported-current-candidate"),
    }),
    /Unsupported semantic delta requires authored mapping/,
  );

  const handoffOutput = process.env.ARCHITECTURE_PUBLISHER_HANDOFF_OUTPUT;
  if (handoffOutput) {
    assert.equal(path.isAbsolute(handoffOutput), true);
    const publisherRepository = await selectedPath("ARCHITECTURE_PUBLISHER_REPOSITORY", {
      directory: true,
    });
    const gitValue = (repositoryPath, ...args) => {
      const result = spawnSync(git, ["-C", repositoryPath, ...args], { encoding: "utf8" });
      assert.equal(result.status, 0, result.stderr);
      return result.stdout.trim();
    };
    const coreArchive = await selectedArchive("ARCHITECTURE_PUBLISHER_PACKAGE");
    await fs.writeFile(
      handoffOutput,
      `${JSON.stringify(
        {
          schema: "ethos.architecture-publisher-handoff/v1",
          publisher: {
            core: {
              tree: gitValue(publisherRepository, "rev-parse", "HEAD:packages/publisher"),
              packageSha256: sha256(await fs.readFile(coreArchive)),
            },
            retiredEthosStaging: {
              commit: baseline.publisher.commit,
              tree: baseline.publisher.migrationTree,
              packageSha256: sha256(await fs.readFile(stagingArchive)),
            },
          },
          ethos: {
            integration: {
              tree: gitValue(SOURCE_ROOT, "rev-parse", "HEAD:integrations/architecture-publisher"),
              packageSha256: sha256(await fs.readFile(sourceOwnedArchive)),
            },
          },
          acceptedParity: {
            sourceManifestSha256: beforeImport.manifestSha256,
            atlasManifestSha256: sourceOwnedAcceptedAtlas.manifestSha256,
            standaloneSha256: sourceOwnedAcceptedStandalone.sha256,
            posterSvgSha256: sourceOwnedAcceptedPoster.svg.sha256,
            posterSceneSha256: sourceOwnedAcceptedPoster.sceneSha256,
            posterManifestSha256: sourceOwnedAcceptedPoster.output.manifestSha256,
          },
          terminalCandidate: {
            projectionDigest: baseline.ethos.terminalAcceptedProjection.projectionDigest,
            sourceManifestSha256: afterImport.manifestSha256,
            atlasManifestSha256: renderedAtlas.manifestSha256,
            standaloneSha256: standalone.sha256,
            posterSvgSha256: poster.svg.sha256,
            posterSceneSha256: poster.sceneSha256,
            posterManifestSha256: poster.output.manifestSha256,
          },
          semanticSuccessor: {
            nodes: evolution.ethos.changed.nodes,
            relations: evolution.ethos.changed.relations,
            assertions: evolution.ethos.changed.assertions,
            humanReviewPredicates: evolution.obligations.humanReview.length,
            acceptance: evolution.obligations.acceptance[0].action,
            publication: evolution.obligations.publication[0].action,
          },
          limits: [
            "semantic acceptance not performed",
            "browser acceptance not performed",
            "human visual review not performed",
            "raster publication not performed",
          ],
        },
        null,
        2,
      )}\n`,
    );
  }
});
