# Cloud AI Trader X Pro — Multi-Platform Deployment

One codebase → Web (PWA), Android, iOS, Windows, macOS. Trading engines,
APIs, routes, and dashboard are unchanged; this is purely a packaging layer.

> **Decision-support only.** No build of this app ever places orders.

---

## Capability matrix — what builds where

| Target | Artifact | Buildable on | Needs |
|---|---|---|---|
| **Web / PWA** | hosted site, installable | any OS | Node 20+ (✅ done & verified here) |
| **Android** | `.apk`, `.aab` | macOS/Linux/Win | Android Studio + SDK + JDK 17 |
| **iOS** | `.ipa` | **macOS only** | Xcode + **Apple Developer account** (signing) |
| **Windows** | `.exe`, `.msi` | Windows (or CI) | electron-builder; signing cert for distribution |
| **macOS** | `.dmg`, `.pkg` | **macOS only** | electron-builder; Apple Developer ID to notarize |

The binaries cannot be produced in this sandbox (no Android SDK, no Apple
Developer account, no Windows host, no domain registrar). Every config and
script below is ready — run them on a provisioned machine or CI and the
artifacts drop out. The **PWA is fully built and verified** here.

---

## 0. One-time backend prerequisite

Packaged apps have no Next.js proxy, so they call the backend directly.
Deploy the FastAPI backend somewhere public (Railway/Render/Fly), then build
the frontend with that origin baked in:

```bash
export NEXT_PUBLIC_API_BASE="https://api.cloudaitraderxpro.com"
export NEXT_PUBLIC_WS_URL="wss://api.cloudaitraderxpro.com/ws"
```

Set `CAT_FRONTEND_ORIGIN` on the backend to your app origins and keep
`CAT_APP_PASSWORD` set (login gate). Broker tokens stay server-side — never
shipped in any binary.

---

## 1. Web + PWA  (done & verified)

```bash
cd frontend
npm install
npm run build && npm start          # SSR + /api proxy (Vercel-style)
```

- Installable: manifest + service worker + icons are live. Chrome/Edge/Android
  show "Install"; iOS uses Share → Add to Home Screen.
- Offline shell at `/offline.html`; SW never caches API/WS (security).
- **Public URL:** deploy `frontend/` to Vercel, point `app.cloudaitraderxpro.com`
  at it (buy the domain at any registrar, add the CNAME Vercel shows).

Regenerate all icons from the SVG master anytime: `npm run icons`.

---

## 2. Android  (Capacitor)

```bash
cd frontend
npm i -D @capacitor/cli @capacitor/core @capacitor/android
npm run build:static                 # -> ./out (static export)
npx cap add android
npm run cap:android                  # builds, syncs, opens Android Studio
npx @capacitor/assets generate --android   # icons/splash from public/icons/icon.svg
```

In Android Studio: **Build → Generate Signed Bundle / APK** → choose **AAB**
(Play Store) or **APK** (sideload). Home-screen icon is automatic on install.

---

## 3. iOS  (Capacitor, macOS only)

```bash
cd frontend
npm i -D @capacitor/cli @capacitor/core @capacitor/ios
npm run build:static
npx cap add ios
npx @capacitor/assets generate --ios
npm run cap:ios                      # opens Xcode
cd ios/App && pod install
```

In Xcode: set your Team (Apple Developer account), then **Product → Archive →
Distribute App** for the `.ipa` / App Store upload. Push notifications: enable
the Push capability and add your APNs key.

---

## 4. Windows  (Electron)

```bash
cd frontend
npm i -D electron electron-builder electron-updater
npm run desktop:build  # or: npm run desktop:win   (run on Windows or CI)
```

Outputs `.exe` (NSIS) and `.msi` in `dist-desktop/`. NSIS installer creates a
**desktop shortcut + Start-menu entry** automatically. Sign with a code-signing
cert for SmartScreen trust. Auto-update works once `publish:` is added to
`electron-builder.yml` (e.g. GitHub releases) — the `electron-updater` hook in
`electron/main.js` is already wired.

## 5. macOS  (Electron, macOS only)

```bash
cd frontend
npm run desktop:mac
```

Outputs universal `.dmg` and `.pkg` (Apple Silicon + Intel) in `dist-desktop/`.
For distribution, set `CSC_LINK`/`CSC_KEY_PASSWORD` (Developer ID cert) and
notarize with `notarytool`. Dock icon comes from `electron/build/icon.png`.

Try the desktop shell instantly against the live site (no packaging):

```bash
APP_URL="https://app.cloudaitraderxpro.com" npm run desktop:dev
```

---

## Splash & icons

Single source: `frontend/public/icons/icon.svg` (+ `maskable.svg`). PNG sizes
(192/512/1024/180) are generated into `public/icons/` and `electron/build/`.
Capacitor splash shows on app launch (config in `capacitor.config.ts`); the web
splash is the manifest `background_color` + icon. Branding is identical across
all platforms because every target derives from the same SVG.

---

## Deployment validation checklist

- [ ] Backend reachable at `NEXT_PUBLIC_API_BASE`; CORS allows the app origin
- [ ] Login works (token stored client-side, sent via header, never in URLs)
- [ ] Market data + WebSocket stream in the packaged app
- [ ] Chart, decision cards, scanner, replay render on phone + tablet + desktop
- [ ] PWA installs and the offline shell appears with no network
- [ ] Trading engines unchanged (signals still multi-layer; NO TRADE preserved)
