// Migrated from legacy Archify pair-delivery.mjs at d2910a5e.
// Historical subject rules remain unchanged. Reads are supplied from explicit
// verified evidence bytes; stored scripts are never executed by this verifier.
import path from "node:path";
import { createHash } from "node:crypto";
const sha = (b) => createHash("sha256").update(b).digest("hex");
const equal = (a, b, why) => {
  if (a !== b) throw Error(why);
};
const sameSet = (actual, expected, why) =>
  equal(JSON.stringify([...actual].sort()), JSON.stringify([...expected].sort()), why);
function relative(root, file) {
  if (
    typeof file !== "string" ||
    !file ||
    path.isAbsolute(file) ||
    file.includes("\\") ||
    file.split("/").some((p) => !p || p === "." || p === "..")
  )
    throw Error("Invalid relative path");
  return path.join(root, file);
}
export async function verifyHistoricalReaderReview(
  o,
  atlas,
  manifest,
  source,
  read,
  json,
  selectionPath,
) {
  const e = o.evidence,
    reviewFile = relative(o.atlasRoot, e.review),
    review = await read(reviewFile);
  const applicability = await json(relative(o.atlasRoot, e.reviewApplicability));
  const formats = [
    "system.architecture.json",
    "system.bindings.json",
    "preview.svg",
    "preview.png",
  ];
  async function priorReview(report, record, reviewed, current, pages) {
    equal(sha(report), record.review?.sha256, "Review applicability independent review drift");
    equal(record.status, "PASS", "Review applicability is unresolved");
    sameSet(
      record.checks.map((c) => c.page + "/" + c.file),
      pages.flatMap((p) => [...formats, "visible-document"].map((f) => p.id + "/" + f)),
      "Review applicability coverage incomplete",
    );
    for (const c of record.checks) {
      const page = pages.find((p) => p.id === c.page);
      if (c.file === "visible-document") {
        const strip = (b) => b.toString().replace(/<script\b[^>]*>[\s\S]*?<\/script>/g, "");
        if (
          c.same !== true ||
          strip(await read(path.join(reviewed, "publication", page.path))) !==
            strip(await read(path.join(current, "publication", page.path)))
        )
          throw Error("Review applicability visible-document mismatch");
      } else {
        equal(
          sha(await read(path.join(current, "authoring", page.id, c.file))),
          c.current,
          "Review applicability current hash mismatch",
        );
        equal(
          sha(await read(path.join(reviewed, "authoring", page.id, c.file))),
          c.old,
          "Review applicability reviewed hash mismatch",
        );
        equal(c.old, c.current, "Review applicability changed meaning");
      }
    }
  }
  const reviewed = relative(o.atlasRoot, e.reviewedAtlas);
  if (applicability.schema !== "ethos.reader-review-binding/v1") {
    await priorReview(review, applicability, reviewed, atlas, manifest.pages);
    return { review, additionalFiles: [] };
  }
  const r = applicability;
  for (const field of ["commit", "tree", "digest"])
    equal(r.subject?.source?.[field], source[field], "Reader review source mismatch");
  equal(r.subject.atlasRoot, o.atlasCandidate, "Reader review candidate root mismatch");
  equal(
    r.subject.atlasManifest?.path,
    path.posix.join(o.atlasCandidate, "atlas-manifest.json"),
    "Reader review manifest path mismatch",
  );
  equal(
    r.subject.atlasManifest?.sha256,
    sha(await read(path.join(atlas, "atlas-manifest.json"))),
    "Reader review manifest mismatch",
  );
  equal(
    r.reviewVerdict,
    "No remaining P0/P1/P2 finding within inspected scope",
    "Reader review has unresolved findings",
  );
  if (
    r.verifier?.processExitCode !== 0 ||
    r.verifier.readOnlyReported !== true ||
    r.verifier.marker !== "RECEIVED_READER_CLARITY_REVIEW" ||
    !review.toString().startsWith(r.verifier.marker + "\n")
  )
    throw Error("Reader review completion is unbound");
  if (r.browserAcceptance !== "UNVERIFIED" || r.documentsPromoted !== false)
    throw Error("Reader review must not amplify browser or publication claims");
  if (
    !Array.isArray(r.evidenceFiles) ||
    new Set(r.evidenceFiles.map((f) => f.path)).size !== r.evidenceFiles.length
  )
    throw Error("Reader review evidence coverage duplicated or absent");
  const bound = new Map();
  for (const f of r.evidenceFiles) {
    const bytes = await read(relative(o.atlasRoot, f.path));
    equal(sha(bytes), f.sha256, "Reader review evidence hash mismatch");
    equal(bytes.length, f.bytes, "Reader review evidence size mismatch");
    bound.set(f.path, bytes);
  }
  if (!e.review.endsWith(".md")) throw Error("Reader review report must be a Markdown path");
  const logPath = e.review.replace(/\.md$/, ".log"),
    promptPath = e.review.replace(/\.md$/, ".prompt.txt");
  if (new Set([e.review, logPath, promptPath]).size !== 3)
    throw Error("Reader review report, log and prompt must be distinct");
  const selection = await json(relative(o.atlasRoot, selectionPath));
  for (const file of [
    e.review,
    logPath,
    promptPath,
    e.ownerVisualAcceptance,
    e.priorReview,
    e.priorReviewApplicability,
    "scripts/native-atlas.mjs",
    selection.sourceInput,
  ]) {
    relative(o.atlasRoot, file);
    if (!bound.has(file)) throw Error("Reader review evidence coverage incomplete: " + file);
  }
  if (
    !bound.get(logPath).toString().includes(bound.get(promptPath).toString().trim()) ||
    !bound.get(logPath).toString().includes(review.toString().trim())
  )
    throw Error("Reader review log does not bind prompt and report");
  // Consume the reviewer's own subject, not merely a parent-written binding.
  // This verifies agreement of retained evidence; it is not a signed attestation.
  const blocks = [...review.toString().matchAll(/^```text\n([\s\S]*?)^```/gm)];
  if (blocks.length !== 1) throw Error("Reader review report subject mismatch");
  const pairs = [...blocks[0][1].matchAll(/^([^\n]+)\n([a-f0-9]{40}|[a-f0-9]{64})$/gm)].map((m) => [
      m[1],
      m[2],
    ]),
    reported = new Map(pairs);
  if (reported.size !== pairs.length) throw Error("Reader review report subject mismatch");
  for (const [label, value] of [
    ["Source commit", source.commit],
    ["Source tree", source.tree],
    ["Declared source digest", source.digest],
    [selection.sourceInput, sha(bound.get(selection.sourceInput))],
    [r.subject.atlasManifest.path, r.subject.atlasManifest.sha256],
    ["scripts/native-atlas.mjs", sha(bound.get("scripts/native-atlas.mjs"))],
  ])
    equal(reported.get(label), value, "Reader review report subject mismatch: " + label);
  const overview = manifest.pages.find((p) => p.id === "overview");
  equal(
    reported.get(path.posix.join(o.atlasCandidate, "publication", overview.path)),
    overview.htmlSha256,
    "Reader review report subject mismatch: overview",
  );
  if (!Array.isArray(r.pages)) throw Error("Reader review page coverage absent");
  sameSet(
    r.pages.map((p) => p.id),
    manifest.pages.map((p) => p.id),
    "Reader review page coverage incomplete",
  );
  for (const p of manifest.pages) {
    const row = r.pages.find((c) => c.id === p.id);
    equal(row.path, p.path, "Reader review page path mismatch");
    equal(row.htmlSha256, p.htmlSha256, "Reader review page hash mismatch");
    equal(
      sha(await read(relative(path.join(atlas, "publication"), p.path))),
      row.htmlSha256,
      "Reader review current HTML mismatch",
    );
  }
  const predecessor = relative(o.atlasRoot, e.predecessorAtlas),
    priorManifest = await json(path.join(predecessor, "atlas-manifest.json"));
  equal(priorManifest.sourceDigest, source.digest, "Reader review predecessor source mismatch");
  sameSet(
    priorManifest.pages.map((p) => p.id + "/" + p.path),
    manifest.pages.map((p) => p.id + "/" + p.path),
    "Reader review predecessor page coverage differs",
  );
  await priorReview(
    bound.get(e.priorReview),
    JSON.parse(bound.get(e.priorReviewApplicability)),
    reviewed,
    predecessor,
    priorManifest.pages,
  );
  if (!Array.isArray(r.diagramComparisons)) throw Error("Reader review diagram coverage absent");
  sameSet(
    r.diagramComparisons.map((c) => c.page + "/" + c.file),
    manifest.pages.flatMap((p) => formats.map((f) => p.id + "/" + f)),
    "Reader review diagram coverage incomplete",
  );
  for (const c of r.diagramComparisons) {
    const expected = [e.reviewedAtlas, e.predecessorAtlas, o.atlasCandidate].map((p) =>
      path.posix.join(p, "authoring", c.page, c.file),
    );
    if (!Array.isArray(c.paths)) throw Error("Reader review diagram paths absent");
    sameSet(c.paths, expected, "Reader review diagram paths incomplete");
    for (const file of c.paths)
      equal(
        sha(await read(relative(o.atlasRoot, file))),
        c.sha256,
        "Reader review diagram identity mismatch",
      );
  }
  return {
    review,
    additionalFiles: [
      ["reader-review.log", logPath],
      ["reader-review.prompt.txt", promptPath],
      ["owner-visual-acceptance.json", e.ownerVisualAcceptance],
      ["prior-independent-review.md", e.priorReview],
      ["prior-review-applicability.json", e.priorReviewApplicability],
    ],
  };
}
