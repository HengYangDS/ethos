import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

async function visit(directory, prefix, members) {
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    const file = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw Error("ETHOS extension runtime symlink");
    if (entry.isDirectory()) await visit(file, relative, members);
    else if (entry.isFile()) {
      const bytes = await fs.readFile(file);
      members.push({ file, path: relative, bytes: bytes.length, sha256: sha256(bytes) });
    } else throw Error("Unsupported ETHOS extension runtime member");
  }
}

/** Return the exact installed extension closure for publication dependency binding. */
export async function readEthosExtensionRuntime() {
  const members = [];
  await visit(path.join(root, "src"), "src", members);
  const manifest = path.join(root, "package.json");
  const bytes = await fs.readFile(manifest);
  members.push({
    file: manifest,
    path: "package.json",
    bytes: bytes.length,
    sha256: sha256(bytes),
  });
  return members.sort((left, right) => left.path.localeCompare(right.path));
}
