"use client";
// Last-resort boundary for errors in the root layout itself (V13). Must render
// its own <html>/<body>. Guarantees there is never a blank white screen.

export default function GlobalError({
  error, reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#0a0e14", color: "#8b96a8",
        fontFamily: "ui-monospace, Menlo, monospace", height: "100vh",
        display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", padding: "2rem" }}>
          <div style={{ fontSize: "2rem" }}>⚠️</div>
          <h1 style={{ color: "#22d3ee", fontSize: "1.1rem", letterSpacing: ".05em" }}>
            CLOUD AI TRADER X PRO
          </h1>
          <p style={{ fontSize: ".85rem", lineHeight: 1.6 }}>
            The app encountered an unexpected error and recovered safely.<br />
            No data was lost. Reload to continue.
          </p>
          <button onClick={reset} style={{ marginTop: "1.2rem", background: "#22d3ee",
            color: "#000", border: 0, borderRadius: ".6rem", padding: ".6rem 1.4rem",
            fontWeight: 700, fontSize: ".8rem", cursor: "pointer" }}>
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
