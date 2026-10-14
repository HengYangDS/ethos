/** Invoke the official Markdownlint API on exact content with explicit native policy. */
import { readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [entry, configuration, root, selected] = process.argv.slice(2);
const { main } = await import(pathToFileURL(entry));
const directory = path.dirname(entry);
const contents = Object.fromEntries(
  JSON.parse(selected).map((relative) => [
    path.join(directory, relative),
    readFileSync(path.join(root, relative), "utf8"),
  ]),
);
process.exitCode = await main({
  directory,
  argv: ["--config", configuration],
  noGlobs: true,
  noImport: true,
  nonFileContents: contents,
  optionsOverride: { fix: false, noInlineConfig: true },
  logMessage: console.log,
  logError: console.error,
});
