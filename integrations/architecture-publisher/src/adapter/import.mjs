import fs from "node:fs/promises";
import path from "node:path";
import { devNull } from "node:os";
import { spawnSync } from "node:child_process";
import { writeSourceBundle } from "architecture-publisher/source";
import { fail, isDigest, portablePath } from "architecture-publisher/source";
import {
  SOURCE_PATHS,
  sha256,
  validateEthosMembers,
  validateProjectionEnvelope,
} from "./projection.mjs";

/** This explicit adapter executes only caller-selected trusted source code. */
export async function importEthosSource(plan) {
  const fields = [
    "repository",
    "revision",
    "projectionDigest",
    "exporterSha256",
    "ownerSha256",
    "git",
    "python",
    "output",
  ];
  if (
    !plan ||
    typeof plan !== "object" ||
    Object.keys(plan).length !== fields.length ||
    fields.some((k) => typeof plan[k] !== "string" || !plan[k])
  )
    fail("import_plan_invalid");
  if (!/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/.test(plan.revision)) fail("source_revision_required");
  for (const key of ["projectionDigest", "exporterSha256", "ownerSha256"])
    if (!isDigest(plan[key])) fail("source_digest_required");
  for (const key of ["git", "python"])
    if (!path.isAbsolute(plan[key])) fail("executable_path_required");
  for (const key of ["repository", "output"])
    if (!path.isAbsolute(plan[key])) fail("source_path_required");
  try {
    await fs.lstat(plan.output);
    fail("output_exists");
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  const env = {
    PATH: path.dirname(plan.git),
    LC_ALL: "C.UTF-8",
    GIT_CONFIG_GLOBAL: devNull,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_NO_REPLACE_OBJECTS: "1",
    GIT_OPTIONAL_LOCKS: "0",
    GIT_TERMINAL_PROMPT: "0",
    PYTHONDONTWRITEBYTECODE: "1",
  };
  function run(executable, args, input) {
    const r = spawnSync(executable, args, {
      cwd: plan.repository,
      env,
      input,
      timeout: 30000,
      maxBuffer: 32 * 1024 * 1024,
    });
    if (r.error || r.status !== 0) fail("source_process_failed", r.error?.code ?? String(r.status));
    return r.stdout;
  }
  const git = (...args) => run(plan.git, args);
  const commit = git("rev-parse", plan.revision + "^{commit}")
    .toString()
    .trim();
  const tree = git("rev-parse", plan.revision + "^{tree}")
    .toString()
    .trim();
  if (commit !== plan.revision) fail("source_revision_required");
  const blob = (p) => {
    portablePath(p);
    return git("show", plan.revision + ":" + p);
  };
  const exporter = blob(SOURCE_PATHS.exporter),
    owner = blob(SOURCE_PATHS.owner);
  if (sha256(exporter) !== plan.exporterSha256 || sha256(owner) !== plan.ownerSha256)
    fail("source_code_digest_mismatch");
  const raw = run(plan.python, [
    "-I",
    "-B",
    "-c",
    exporter.toString("utf8"),
    "--root",
    plan.repository,
    "--revision",
    plan.revision,
  ]);
  let input;
  try {
    input = JSON.parse(raw.toString("utf8"));
  } catch {
    fail("projection_json_invalid");
  }
  validateProjectionEnvelope(input, plan.projectionDigest);
  if (input.source.git.commit !== commit || input.source.git.tree !== tree)
    fail("projection_source_invalid");
  const selected = new Set([
    ...Object.values(SOURCE_PATHS),
    ...input.source.bindings.map((b) => b.path),
    ...input.source.documents.map((d) => d.path),
  ]);
  const members = [
    { path: "projection-input.json", content: raw },
    ...[...selected].sort().map((p) => ({ path: "source/" + p, content: blob(p) })),
  ];
  const source = { id: input.source.id, revision: commit };
  validateEthosMembers({ source, members }, plan.projectionDigest);
  const written = await writeSourceBundle(plan.output, source, members);
  return {
    ...written,
    source,
    projectionDigest: input.digest,
    officialReplay: "performed",
    semanticAcceptance: "not-performed",
    replay: {
      exporterSha256: plan.exporterSha256,
      ownerSha256: plan.ownerSha256,
      sourceCommit: commit,
      sourceTree: tree,
    },
  };
}
