import type { Metadata, Viewport } from "next";
import "./globals.css";
import { MarketProvider } from "@/lib/store";
import { StatusBar } from "@/components/StatusBar";
import { PWARegister } from "@/components/PWARegister";

export const metadata: Metadata = {
  applicationName: "Cloud AI Trader X Pro",
  title: "Cloud AI Trader X Pro",
  description: "Institutional AI Trading Terminal — index, stock & commodity market intelligence.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "AI Trader X",
  },
  icons: {
    icon: [
      { url: "/icons/icon.svg", type: "image/svg+xml" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",      // respect iOS safe-area / notch in standalone mode
  themeColor: "#0a0e14",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <PWARegister />
        <MarketProvider>
          <div className="min-h-screen flex flex-col">
            <StatusBar />
            <main className="flex-1 max-w-[1500px] w-full mx-auto px-3 sm:px-5 py-4">
              {children}
            </main>
            <footer className="text-center text-[10px] text-terminal-muted py-3 px-4">
              <span className="text-terminal-accent font-semibold tracking-wide">
                Evidence decides. Assumptions wait.
              </span>
              {" · "}Analytics & signals are informational only — not investment advice. No orders
              are ever placed by this system.
            </footer>
          </div>
        </MarketProvider>
      </body>
    </html>
  );
}
