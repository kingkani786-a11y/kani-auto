// Build-time version stamp (runs as npm `prebuild`).
// 1. Rewrites the service-worker CACHE name to the current git commit so every
//    deploy auto-invalidates the PWA cache (no more stale-shell trap).
// 2. Writes public/version.json for the dashboard Build-Version panel.
// Owner's request: cache should key off the build, and the live version must be
// visible on the dashboard so anyone can self-verify which build is running.
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const pub = join(here, "..", "public");

let commit = "unknown";
try { commit = execSync("git rev-parse --short HEAD", { cwd: here }).toString().trim(); } catch {}
const builtAt = new Date().toISOString();
const swVersion = `cat-shell-${commit}`;

// 1. Stamp sw.js CACHE constant
try {
  const swPath = join(pub, "sw.js");
  let sw = readFileSync(swPath, "utf8");
  sw = sw.replace(/const CACHE = "[^"]*";/, `const CACHE = "${swVersion}";`);
  writeFileSync(swPath, sw);
  console.log(`[stamp] sw.js CACHE -> ${swVersion}`);
} catch (e) { console.warn("[stamp] sw.js not stamped:", e.message); }

// 2. version.json for the dashboard
writeFileSync(join(pub, "version.json"),
  JSON.stringify({ commit, builtAt, sw: swVersion }, null, 2));
console.log(`[stamp] version.json -> ${commit} @ ${builtAt}`);
