"use client";
// Route-segment error recovery (V13). Catches render/runtime errors in a page
// and offers recovery — never a white screen.

import { useEffect } from "react";

export default function RouteError({
  error, reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.warn("[RouteError]", error);
  }, [error]);

  return (
    <div className="max-w-md mx-auto mt-20 panel text-center">
      <div className="text-3xl mb-3">⚠️</div>
      <h2 className="text-base font-semibold mb-2">This page hit a problem</h2>
      <p className="text-sm text-terminal-muted mb-5">
        The error was contained — your session and live data are intact.
        Try again, or use the nav to switch pages.
      </p>
      <button
        onClick={reset}
        className="px-5 py-2.5 rounded-lg bg-terminal-accent text-black font-semibold text-sm"
      >
        Reload this page
      </button>
    </div>
  );
}
