// Compila ogni famiglia di card in un file a sé: src/<famiglia>/index.js
// diventa ../custom_components/domo/www/domo-<famiglia>-card.js
import { readdirSync, existsSync } from "node:fs";
import { build } from "esbuild";

const SRC = new URL("./src/", import.meta.url);
const OUT = new URL("../custom_components/domo/www/", import.meta.url);

const families = readdirSync(SRC, { withFileTypes: true })
  .filter((d) => d.isDirectory() && existsSync(new URL(`${d.name}/index.js`, SRC)))
  .map((d) => d.name);

for (const family of families) {
  await build({
    entryPoints: [new URL(`${family}/index.js`, SRC).pathname],
    outfile: new URL(`domo-${family}-card.js`, OUT).pathname,
    bundle: true,
    minify: true,
    format: "esm",
    target: "es2020",
  });
  console.log(`built domo-${family}-card.js`);
}
