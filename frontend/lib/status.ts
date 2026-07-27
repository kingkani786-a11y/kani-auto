// Central friendly-status translator. The UI must NEVER show raw backend
// exceptions, parser errors, or JSON. Every message is mapped to a calm,
// user-facing status here (defense-in-depth — backend also sends friendly text).

export function friendlyMessage(raw?: string | null): string {
  const m = (raw || "").toLowerCase().trim();
  if (!m) return "";

  if (m.includes("market closed") || m.includes("live price unavailable"))
    return "🟡 Market Closed — waiting for the next trading session";
  if (m.includes("subscri") || m.includes("data api"))
    return "📡 Data Subscription Required — live market feed unavailable";
  if (m.includes("token") || m.includes("401") || m.includes("authentication") || m.includes("unauthor"))
    return "🔑 Authentication Required — update your Dhan Access Token";
  if (m.includes("rate limit") || m.includes("rate-limit") || m.includes("cooldown") || m.includes("429"))
    return "⏳ Waiting — broker rate limit reached, retrying automatically";
  if (m.includes("unreachable") || m.includes("network") || m.includes("timeout") || m.includes("reconnect"))
    return "🌐 Reconnecting…";
  if (m.includes("no price") || m.includes("contains no price") || m.includes("unexpected ltp")
      || m.includes("parser") || m.includes("keyerror") || m.includes("typeerror")
      || m.includes("valueerror") || m.includes("traceback") || m.includes("empty data"))
    return "⏳ Waiting for live market data…";
  if (m.includes("broker"))
    return "🟠 Broker issue — retrying automatically";

  // Allow only short, clean, non-technical text through; otherwise a calm default.
  const technical = /[{}\[\]<>]|exception|error:|\bat \w+\.|stack/i.test(raw || "");
  return (raw && raw.length <= 80 && !technical) ? raw : "⏳ Working…";
}
