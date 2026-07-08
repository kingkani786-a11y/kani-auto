"use client";
// Component-level error boundary (V13). Wrap any dashboard card so a single
// module throwing (null data, bad calc, render error) shows a compact fallback
// instead of crashing the whole dashboard. No white screens.

import React from "react";

interface Props {
  name?: string;
  children: React.ReactNode;
}
interface State {
  hasError: boolean;
}

export class SafeBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // silent failure protection — log, never propagate
    if (typeof console !== "undefined") {
      console.warn(`[SafeBoundary${this.props.name ? ` ${this.props.name}` : ""}]`, error);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel border-terminal-border/60 py-4">
          <div className="text-[11px] uppercase tracking-widest text-terminal-muted mb-1">
            {this.props.name || "Panel"}
          </div>
          <div className="text-xs text-terminal-warn">
            ⚠ This panel hit an error and was isolated. The rest of the dashboard is unaffected.
          </div>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="mt-2 px-2.5 py-1 rounded border border-terminal-border text-[11px] hover:border-terminal-accent"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
