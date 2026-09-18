/** Preserve concrete reference destinations through the official archive projection. */
import { readFileSync } from "node:fs";
import { mkdtemp, realpath, rm, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [entry] = process.argv.slice(2);
const require = createRequire(pathToFileURL(entry));
const { parse, preprocess, postprocess } = await import(
  pathToFileURL(require.resolve("micromark"))
);
const { decodeString } = await import(
  pathToFileURL(require.resolve("micromark-util-decode-string"))
);
const source = JSON.parse(readFileSync(0, "utf8"));
const files = new Set(Object.keys(source.files));
const postimageFiles = new Set(Object.keys(source.postimage_files));
const replacements = new Map(source.moves);
const local = path.posix;

function fail(reason, file, target = "") {
  throw new Error("archive_reference_" + reason + ":" + file + (target ? ":" + target : ""));
}

function mappedTarget(target) {
  for (const [before, after] of replacements) {
    if (target === before || target.startsWith(before + "/")) {
      return after + target.slice(before.length);
    }
  }
  return target;
}

function relocated(raw, before, after) {
  const decoded = decodeString(raw);
  if (!decoded || /^(?:[a-z][a-z\d+.-]*:|\/\/|\/|#|\?)/i.test(decoded)) return raw;
  const suffixAt = decoded.search(/[?#]/);
  const pathname = suffixAt < 0 ? decoded : decoded.slice(0, suffixAt);
  const suffix = suffixAt < 0 ? "" : decoded.slice(suffixAt);
  let unescaped;
  try {
    unescaped = decodeURIComponent(pathname);
  } catch {
    fail("encoding_invalid", before, raw);
  }
  const target = local.normalize(local.join(local.dirname(before), unescaped));
  if (target === ".." || target.startsWith("../") || /[\0\\]/.test(unescaped)) {
    fail("target_outside_repository", before, raw);
  }
  if (!files.has(target) && ![...files].some((p) => p.startsWith(target + "/"))) {
    fail("target_missing", before, target);
  }
  const desired = mappedTarget(target);
  for (const [candidate, entries] of [
    [target, source.files],
    [desired, source.postimage_files],
  ]) {
    const parts = candidate.split("/");
    for (let i = 1; i <= parts.length; i++) {
      const mode = entries[parts.slice(0, i).join("/")];
      if (mode && !["100644", "100755"].includes(mode))
        fail("target_kind_unsupported", before, candidate);
    }
  }
  if (
    !postimageFiles.has(desired) &&
    ![...postimageFiles].some((p) => p.startsWith(desired + "/"))
  ) {
    fail("postimage_target_missing", before, desired);
  }
  const unchanged = local.normalize(local.join(local.dirname(after), unescaped));
  if (unchanged === desired) return raw;
  return (
    local
      .relative(local.dirname(after), desired)
      .split("/")
      .map((part) =>
        encodeURIComponent(part).replace(
          /[!'()*]/g,
          (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase(),
        ),
      )
      .join("/") + suffix.replaceAll("&", "&amp;")
  );
}

function relocate(text, before, after) {
  const events = postprocess(
    parse()
      .document()
      .write(preprocess()(text, "utf8", true)),
  );
  const changes = [];
  for (const [kind, token, context] of events) {
    if (kind !== "enter") continue;
    if (token.type === "htmlFlow" || token.type === "htmlText") {
      const html = context.sliceSerialize(token);
      if (/\b(?:href|src)\s*=/i.test(html)) fail("html_unsupported", before);
    }
    if (!["resourceDestinationString", "definitionDestinationString"].includes(token.type))
      continue;
    const start = token.start.offset;
    const end = token.end.offset;
    const raw = text.slice(start, end);
    const replacement = relocated(raw, before, after);
    if (replacement !== raw) changes.push([start, end, replacement]);
  }
  for (const [start, end, value] of changes.reverse()) {
    text = text.slice(0, start) + value + text.slice(end);
  }
  return text;
}

const result = { documents: [], canonical: [] };
let owned;
try {
  for (const doc of source.documents) {
    result.documents.push({
      path: doc.after,
      content: relocate(doc.content, doc.before, doc.after),
    });
  }
  for (const doc of source.canonical) {
    const adjusted = relocate(doc.delta, doc.before, doc.after);
    if (adjusted === doc.delta) continue;
    if (!owned)
      owned = await realpath(await mkdtemp(path.join(tmpdir(), "ethos-archive-reference-")));
    const module = new URL("../dist/core/specs-apply.js", pathToFileURL(entry));
    const { buildUpdatedSpec } = await import(module.href);
    const from = path.join(owned, "delta.md");
    const target = path.join(owned, "canonical.md");
    if (doc.previous === null) await rm(target, { force: true });
    else await writeFile(target, doc.previous);
    const update = {
      id: doc.id,
      source: from,
      target,
      sourceRoot: owned,
      targetRoot: owned,
      exists: doc.previous !== null,
    };
    await writeFile(from, doc.delta);
    const original = await buildUpdatedSpec(update, source.change, { silent: true });
    await writeFile(from, adjusted);
    const expected = await buildUpdatedSpec(update, source.change, { silent: true });
    if (original.warnings.length || expected.warnings.length) {
      fail("canonical_warning", doc.after);
    }
    result.canonical.push({
      path: doc.after,
      original: original.rebuilt,
      content: expected.rebuilt,
    });
  }
  process.stdout.write(JSON.stringify(result));
} finally {
  if (owned) await rm(owned, { recursive: true, force: true });
}
