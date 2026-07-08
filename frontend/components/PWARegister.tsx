"use client";
// Registers the service worker once on the client. No-op during SSR/build.

import { useEffect } from "react";

export function PWARegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    // Don't register inside Capacitor/Electron native shells (they serve local files).
    const isNative = (window as any).Capacitor?.isNativePlatform?.() ||
      navigator.userAgent.includes("Electron");
    if (isNative) return;
    const onLoad = () => navigator.serviceWorker.register("/sw.js").catch(() => {});
    window.addEventListener("load", onLoad);
    return () => window.removeEventListener("load", onLoad);
  }, []);
  return null;
}
