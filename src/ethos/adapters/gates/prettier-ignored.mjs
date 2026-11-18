/** Ask the official Prettier API which of the named files an ignore file excludes, in one run. */
import path from "node:path";
import { pathToFileURL } from "node:url";

const [entry, ignorePath, root] = process.argv.slice(2);
const prettier = await import(pathToFileURL(entry));
let named = "";
for await (const chunk of process.stdin) {
  named += chunk;
}
const ignored = [];
for (const relative of JSON.parse(named)) {
  const info = await prettier.getFileInfo(path.join(root, relative), {
    ignorePath,
    resolveConfig: false,
  });
  if (info.ignored) {
    ignored.push(relative);
  }
}
process.stdout.write(JSON.stringify(ignored));
