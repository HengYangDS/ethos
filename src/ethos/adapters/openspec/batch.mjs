/** Run a bounded read batch through the selected package's official CLI program. */
import { readFileSync, writeSync } from "node:fs";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [entry] = process.argv.slice(2);
const { program } = await import(
  pathToFileURL(createRequire(pathToFileURL(entry)).resolve("@fission-ai/openspec")).href
);
const commands = JSON.parse(readFileSync(0, "utf8"));
let active;

function finish(code) {
  if (!active) return;
  const packet = Buffer.from(JSON.stringify({ ...active, exit_code: code }) + "\n");
  for (let offset = 0; offset < packet.length;) {
    offset += writeSync(1, packet, offset);
  }
  active = undefined;
}

function capture(name) {
  return (chunk, encoding, callback) => {
    if (active) {
      active[name] += Buffer.isBuffer(chunk)
        ? chunk.toString(typeof encoding === "string" ? encoding : "utf8")
        : String(chunk);
    }
    if (typeof encoding === "function") encoding();
    else if (typeof callback === "function") callback();
    return true;
  };
}

process.stdout.write = capture("stdout");
process.stderr.write = capture("stderr");
process.once("exit", finish);
for (const [index, args] of commands.entries()) {
  active = { index, args, stdout: "", stderr: "" };
  process.argv = [process.execPath, entry, ...args];
  process.exitCode = 0;
  await program.parseAsync(args, { from: "user" });
  finish(process.exitCode ?? 0);
}
process.exitCode = 0;
