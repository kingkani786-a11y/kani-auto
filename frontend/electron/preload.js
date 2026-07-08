// Minimal, locked-down bridge. No Node APIs are exposed to the web app —
// it runs exactly as it does in a browser. Kept as an explicit security
// boundary and a hook point for future native integrations.
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("desktop", {
  platform: process.platform,
  isElectron: true,
});
