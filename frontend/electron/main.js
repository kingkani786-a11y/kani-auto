// Cloud AI Trader X Pro — Electron desktop shell (Windows + macOS).
// Loads the static export (../out) or a hosted URL via APP_URL. Native window,
// multi-monitor aware, resizable, with auto-update hook.
const { app, BrowserWindow, shell, Menu } = require("electron");
const path = require("path");

const APP_URL = process.env.APP_URL || null;             // e.g. https://app.cloudaitraderxpro.com
const isDev = !!process.env.ELECTRON_DEV;

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 640,
    backgroundColor: "#0a0e14",
    title: "Cloud AI Trader X Pro",
    icon: path.join(__dirname, "build", process.platform === "win32" ? "icon.ico" : "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,         // security: renderer has no Node access
      sandbox: true,
    },
  });

  // open external links in the system browser, not inside the app
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (APP_URL) {
    win.loadURL(APP_URL);
  } else {
    win.loadFile(path.join(__dirname, "..", "out", "index.html"));
  }

  if (isDev) win.webContents.openDevTools({ mode: "detach" });
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);      // clean, app-like chrome
  createWindow();

  // optional auto-update (electron-updater) when packaged & configured
  if (!isDev && !APP_URL) {
    try {
      const { autoUpdater } = require("electron-updater");
      autoUpdater.checkForUpdatesAndNotify().catch(() => {});
    } catch (_) {
      /* electron-updater not installed — skip */
    }
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
