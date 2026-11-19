/** Ask the official Prettier API which of the named files an ignore file excludes, in one run. */
import path from "node:path";
import { pathToFileURL } from "node:url";

const [entry, ignorePath, root] = process.argv.slice(2);
const prettier = await import(pathToFileURL(entry));
let named = "";
for await (const chunk of process.stdin) {
  named += chunk;
}
const asked = JSON.parse(named);
const infos = await Promise.all(
  asked.map((relative) =>
    prettier.getFileInfo(path.join(root, relative), {
      ignorePath,
      resolveConfig: false,
    }),
  ),
);
const ignored = asked.filter((_relative, index) => infos[index].ignored);
process.stdout.write(JSON.stringify(ignored));
