import type { CapacitorConfig } from "@capacitor/cli";

// Android + iOS wrapper. The static export in ./out is bundled into the app;
// it talks to the hosted backend via NEXT_PUBLIC_API_BASE (baked at build time).
const config: CapacitorConfig = {
  appId: "com.cloudaitraderxpro.app",
  appName: "Cloud AI Trader X Pro",
  webDir: "out",
  backgroundColor: "#0a0e14",
  server: {
    androidScheme: "https",
    // For live-reload during dev, set CAP_SERVER_URL to your dev machine:
    ...(process.env.CAP_SERVER_URL
      ? { url: process.env.CAP_SERVER_URL, cleartext: true }
      : {}),
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      backgroundColor: "#0a0e14",
      showSpinner: false,
      androidScaleType: "CENTER_CROP",
    },
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
  },
};

export default config;
