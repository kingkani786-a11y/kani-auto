// Regenerate every raster icon from the single SVG master.
// Usage: npm run icons   (requires the dev dependency `sharp`)
import sharp from "sharp";
import { readFileSync } from "node:fs";

const icon = readFileSync("public/icons/icon.svg");
const mask = readFileSync("public/icons/maskable.svg");
const D = { density: 300 };

const jobs = [
  [icon, 192, "public/icons/icon-192.png"],
  [icon, 512, "public/icons/icon-512.png"],
  [icon, 1024, "public/icons/icon-1024.png"],
  [icon, 180, "public/icons/apple-touch-icon.png"],
  [mask, 512, "public/icons/maskable-512.png"],
  [icon, 1024, "electron/build/icon.png"],
];

for (const [src, size, out] of jobs) {
  await sharp(src, D).resize(size, size).png().toFile(out);
  console.log("✓", out);
}
console.log("All icons regenerated from public/icons/icon.svg");
