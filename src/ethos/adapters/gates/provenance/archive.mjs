/** Native SRI/TAR observation over already bounded immutable byte inputs. */
import path from "node:path";
import { createRequire } from "node:module";
import { gunzipSync } from "node:zlib";

const native = createRequire(process.argv[2]);
const ssri = native("ssri");
const tar = native("tar");
const cacache = native("cacache");
const contentPath = native("cacache/lib/content/path.js");
const NativeConfig = native("@npmcli/config");
const definitions = native("@npmcli/config/lib/definitions/index.js");
const BLOCK = 512;
// Transport ceiling only. The Python observation owner supplies tighter operation budgets.
const MAX_TRANSPORT_BYTES = 192 * 1024 * 1024;

function invalid(reason) {
  throw new Error(reason);
}

function bounded(value, limit, reason) {
  if (!Number.isSafeInteger(value) || value < 0 || value > limit) invalid(reason);
}

function integrity(value, limits) {
  if (typeof value !== "string") invalid("locked_integrity_invalid");
  const parsed = ssri.parse(value, { strict: true });
  if (!parsed) invalid("locked_integrity_invalid");
  const algorithm = parsed.pickAlgorithm();
  if (!["sha256", "sha384", "sha512"].includes(algorithm)) invalid("locked_integrity_invalid");
  bounded(
    Object.values(parsed).reduce((count, hashes) => count + hashes.length, 0),
    limits.digests,
    "locked_integrity_budget_exceeded",
  );
  return parsed;
}

function decoded(value, limit) {
  if (
    typeof value !== "string" ||
    value.length > 4 * Math.ceil(limit / 3) ||
    value.length % 4 !== 0 ||
    /[^A-Za-z0-9+/=]/.test(value)
  ) {
    invalid("archive_input_bytes_invalid");
  }
  const bytes = Buffer.from(value, "base64");
  if (bytes.toString("base64") !== value) invalid("archive_input_bytes_invalid");
  bounded(bytes.length, limit, "archive_input_size_exceeded");
  return bytes;
}

async function cacheSelection(archives, limits) {
  // Native defaults and explicit cache environment only: never candidate/user credential files.
  const env = Object.fromEntries(
    Object.entries(process.env).filter(
      ([key]) =>
        ["HOME", "USERPROFILE", "APPDATA"].includes(key) || /^npm_config_cache$/i.test(key),
    ),
  );
  const config = new NativeConfig({
    ...definitions,
    npmPath: path.dirname(path.dirname(process.argv[2])),
    env,
    argv: [process.execPath, process.argv[2]],
  });
  config.loadDefaults();
  config.loadEnv();
  const cache = path.resolve(config.flat.cache);
  const selected = [];
  for (const entry of archives) {
    if (typeof entry.reference !== "string") {
      invalid("archive_cache_reference_invalid");
    }
    const found = await cacache.get.hasContent(cache, integrity(entry.integrity, limits));
    if (!found?.sri || !found.stat?.isFile()) invalid("archive_supply_missing");
    bounded(found.size, limits.archive_bytes, "archive_size_exceeded");
    selected.push({
      reference: entry.reference,
      integrity: found.sri.toString({ strict: true }),
      path: contentPath(cache, found.sri),
      root: cache,
      size: found.size,
    });
  }
  return { selected };
}

function framing(bytes, limits, budget) {
  let offset = 0;
  let extended;
  let global;
  let pending = false;
  while (offset + BLOCK <= bytes.length) {
    const block = bytes.subarray(offset, offset + BLOCK);
    if (block.every((value) => value === 0)) {
      if (
        pending ||
        bytes.length - offset < 2 * BLOCK ||
        bytes.length % BLOCK !== 0 ||
        !bytes.subarray(offset).every((value) => value === 0)
      ) {
        invalid("archive_eof_or_trailing_invalid");
      }
      return;
    }
    const header = new tar.Header(bytes, offset, extended, global);
    if (!header.cksumValid || header.nullBlock) invalid("archive_header_invalid");
    bounded(header.size, limits.archive_bytes, "archive_member_size_exceeded");
    budget.entries += 1;
    bounded(budget.entries, limits.entries, "archive_entry_budget_exceeded");
    const body = offset + BLOCK;
    const end = body + BLOCK * Math.ceil(header.size / BLOCK);
    if (end > bytes.length) invalid("archive_body_incomplete");
    const metadata = [
      "ExtendedHeader",
      "OldExtendedHeader",
      "GlobalExtendedHeader",
      "NextFileHasLongPath",
      "OldGnuLongPath",
      "NextFileHasLongLinkpath",
    ].includes(header.type);
    if (metadata) {
      budget.metadata += header.size;
      bounded(budget.metadata, limits.metadata_bytes, "archive_metadata_budget_exceeded");
      if (header.size === 0) invalid("archive_metadata_empty");
      const text = bytes.subarray(body, body + header.size).toString("utf8");
      if (["ExtendedHeader", "OldExtendedHeader"].includes(header.type)) {
        extended = tar.Pax.parse(text, extended, false);
        pending = true;
      } else if (header.type === "GlobalExtendedHeader") {
        global = tar.Pax.parse(text, global, true);
      } else {
        extended ??= {};
        extended[header.type === "NextFileHasLongLinkpath" ? "linkpath" : "path"] = text.replace(
          /\0.*/,
          "",
        );
        pending = true;
      }
    } else {
      extended = undefined;
      pending = false;
    }
    offset = end;
  }
  invalid("archive_eof_missing");
}

async function memberBytes(raw, requested, limits, budget) {
  let bytes = raw;
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    bytes = gunzipSync(bytes, { maxOutputLength: limits.expanded_bytes - budget.expanded });
  }
  budget.expanded += bytes.length;
  bounded(budget.expanded, limits.expanded_bytes, "archive_expanded_budget_exceeded");
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) invalid("archive_nested_compression_unsupported");
  framing(bytes, limits, budget);
  const wanted = new Set(Object.values(requested).map((relation) => relation.member));
  const found = new Map();
  const names = new Set();
  await new Promise((resolve, reject) => {
    const parser = new tar.Parser({
      strict: true,
      brotli: false,
      zstd: false,
      maxMetaEntrySize: limits.metadata_bytes,
    });
    let failed = false;
    const fail = (reason) => {
      if (!failed) {
        failed = true;
        reject(new Error(reason));
        parser.abort(new Error(reason));
      }
    };
    parser.on("error", (error) => fail(error.message));
    parser.on("warn", (code) => fail(code));
    parser.on("ignoredEntry", () => fail("archive_member_unsupported"));
    parser.on("entry", (entry) => {
      const name = entry.path.replace(/\/$/, "");
      if (
        !name ||
        name.includes("\\") ||
        path.posix.isAbsolute(name) ||
        /^[A-Za-z]:/.test(name) ||
        path.posix.normalize(name) !== name ||
        !(name.startsWith("package/") || (name === "package" && entry.type === "Directory")) ||
        names.has(name) ||
        !["File", "OldFile", "Directory"].includes(entry.type)
      ) {
        fail("archive_member_identity_invalid");
        return;
      }
      names.add(name);
      if (wanted.has(name)) {
        if (!["File", "OldFile"].includes(entry.type)) {
          fail("archive_member_not_regular");
          return;
        }
        const chunks = [];
        entry.on("data", (chunk) => chunks.push(chunk));
        entry.on("end", () => found.set(name, Buffer.concat(chunks)));
      } else {
        entry.resume();
      }
    });
    parser.on("end", resolve);
    parser.end(bytes);
  });
  if (found.size !== wanted.size) invalid("archive_member_missing");
  return found;
}

try {
  const chunks = [];
  let inputSize = 0;
  for await (const chunk of process.stdin) {
    inputSize += chunk.length;
    bounded(inputSize, MAX_TRANSPORT_BYTES, "archive_request_size_exceeded");
    chunks.push(chunk);
  }
  const request = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  const limits = request.limits;
  if (!limits || !Array.isArray(request.archives)) invalid("archive_request_invalid");
  for (const key of [
    "archive_bytes",
    "raw_bytes",
    "input_bytes",
    "expanded_bytes",
    "metadata_bytes",
    "entries",
    "digests",
  ]) {
    if (!Number.isSafeInteger(limits[key]) || limits[key] <= 0) invalid("archive_limits_invalid");
  }
  bounded(inputSize, limits.input_bytes, "archive_request_size_exceeded");
  bounded(request.archives.length, limits.entries, "archive_request_count_exceeded");
  if (request.select_cache === true) {
    process.stdout.write(JSON.stringify(await cacheSelection(request.archives, limits)));
  } else {
    const matched = [];
    const budget = { raw: 0, expanded: 0, metadata: 0, entries: 0, members: 0 };
    for (const entry of request.archives) {
      const bytes = decoded(
        entry.data,
        Math.min(limits.archive_bytes, limits.raw_bytes - budget.raw),
      );
      budget.raw += bytes.length;
      const parsed = integrity(entry.integrity, limits);
      const verified = ssri.checkData(bytes, parsed, { strict: true, error: true });
      if (
        entry.selected_integrity &&
        verified.toString({ strict: true }) !== entry.selected_integrity
      ) {
        invalid("archive_cache_identity_mismatch");
      }
      const members = await memberBytes(bytes, entry.members, limits, budget);
      for (const [artifact, relation] of Object.entries(entry.members)) {
        budget.members += 1;
        bounded(budget.members, limits.entries, "archive_member_count_exceeded");
        const expected = decoded(relation.expected, limits.raw_bytes - budget.raw);
        budget.raw += expected.length;
        if (!members.get(relation.member)?.equals(expected))
          invalid("archive_member_bytes_mismatch");
        matched.push(artifact);
      }
    }
    process.stdout.write(JSON.stringify({ matched: matched.sort() }));
  }
} catch (error) {
  process.stderr.write(error instanceof Error ? error.message : "archive_observation_invalid");
  process.exitCode = 1;
}
