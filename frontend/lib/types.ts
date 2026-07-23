export interface Status {
  connected: boolean;
  market_type: "INDEX" | "COMMODITY";
  symbol: string;
  market_open: boolean;
  data_quality: string;
  // V7 Market Independence Phase A (owner, 2026-07-23)
  market_exchanges?: Record<string, {
    status: string; market_type: string; is_open: boolean;
    ist_time?: string; next_open_ist?: string | null; seconds_to_open?: number;
    weekend?: boolean; reason?: string;
  }>;
  auto_market_switch?: boolean;
}

export interface Spot {
  symbol: string;
  ltp: number;
  change: number;
  change_pct?: number;
  high?: number;
  low?: number;
  volume?: number;
  tick_dir: "up" | "down" | "flat";
  ts: number;
}

export interface GreekLeg {
  delta: number; gamma: number; theta: number; vega: number; iv: number;
}

export interface Analytics {
  expiry?: string;
  atm_strike?: number;
  pcr?: number;
  max_pain?: number;
  call_oi?: number;
  put_oi?: number;
  call_oi_change?: number;
  put_oi_change?: number;
  oi?: number;
  volume?: number;
  underlying_flow?: string;
}

export interface ChainRow {
  strike: number;
  ce_ltp: number; ce_oi: number; ce_oi_chg: number; ce_iv: number; ce_volume: number;
  pe_ltp: number; pe_oi: number; pe_oi_chg: number; pe_iv: number; pe_volume: number;
}

export interface Tech {
  trend: string; ema9: number; ema21: number;
  vwap: number; atr: number; adx: number; momentum: number;
  volume_expansion: boolean;
}

export interface Signal {
  signal: string;
  symbol?: string;
  entry?: number;
  stop_loss?: number;
  target1?: number;
  target2?: number;
  target3?: number;
  confidence: number;
  bull_score: number;
  bear_score: number;
  reward_risk?: number;
  reasons: string[];
  confirmations?: string[];
  confirmations_count?: number;
  vetoes?: string[];
  grade?: string;
  grade_score?: number;
  grade_notes?: string[];
  dynamic_confidence?: number;
  confidence_components?: Record<string, number | null>;
  effective_threshold?: number;
  threshold_reason?: string;
  factors?: { bull: Record<string, number>; bear: Record<string, number> };
  tech?: Tech;
  ts?: number;
}

export interface Risk {
  risk_level: string;
  confidence: number;
  trend_strength: string;
  adx: number;
  volatility: string;
  atr_pct: number;
  data_quality: string;
  warnings: string[];
}

export interface SmartMoney {
  activities: string[];
  bias: string;
  underlying?: string;
}

export interface JournalEntry {
  id: string;
  date: string; time: string; market: string; signal: string;
  entry?: number; exit?: number; stop_loss?: number; target?: number;
  pnl?: number; confidence?: number; notes?: string;
}

export interface SymbolInfo {
  symbol: string;
  market_type: string;
  tv_symbol: string;
}

// ---- Cloud AI Trader X ----
export interface LayerScore {
  direction?: string;
  score_bull?: number;
  score_bear?: number;
  notes?: string[];
  [k: string]: unknown;
}

export interface Layers {
  trend?: LayerScore & { ema20?: number; ema50?: number; ema200?: number; adx?: number };
  structure?: LayerScore & { swing?: string; support?: number; resistance?: number; event?: string };
  oi?: LayerScore & { pcr?: number; max_pain?: number };
  smart_money?: LayerScore & { events?: string[]; flow?: string[] };
  greeks?: LayerScore & { atm_iv?: number };
  volume_profile?: LayerScore & { poc?: number; vah?: number; val?: number; state?: string };
  mtf?: LayerScore & { alignment?: number; frames?: Record<string, string> };
  regime?: { regime?: string; score?: number; notes?: string[] };
  probability?: { prob_success?: number; prob_failure?: number; expected_move?: number; expected_range?: [number, number] };
  risk?: Risk;
}

export interface StrikeReco {
  strike: number;
  type: "CE" | "PE";
  premium_entry: number;
  premium_stop_loss: number;
  premium_target1: number;
  premium_target2: number;
  premium_target3: number;
  delta: number;
  iv: number;
  oi: number;
  volume: number;
  spread_pct: number;
  selection_score: number;
}

export interface Warning {
  setup: string;
  preparation: number;
  confidence: number;
  notes: string[];
}

export interface PaperTrade {
  id: string;
  symbol: string;
  side: string;
  qty: number;
  entry: number;
  exit?: number | null;
  stop_loss?: number | null;
  target?: number | null;
  status: string;
  pnl?: number | null;
  unrealized?: number;
  opened_at: string;
  closed_at?: string | null;
  review?: { outcome: string; why: string[]; improve: string[] } | null;
  snapshot?: Record<string, unknown>;
}

export interface BacktestResult {
  symbol: string;
  year: number;
  trades: number;
  win_rate: number;
  avg_reward_risk: number;
  profit_factor: number;
  max_drawdown_pts: number;
  net_points: number;
  sharpe_ratio?: number;
  expectancy_r?: number;
  note: string;
}

export interface LifecycleState {
  state: string;
  direction: string;
  trigger_price?: number | null;
  invalidation_price?: number | null;
  breakout_level?: number | null;
  breakdown_level?: number | null;
  entry?: number | null;
  stop?: number | null;
  targets?: number[];
  targets_hit?: number;
  updated?: number;
  history?: { ts: number; from: string; to: string; note: string }[];
}

export interface Alert {
  id: string;
  ts: string;
  kind: string;
  symbol: string;
  title: string;
  body: string;
}

export interface Decision {
  primary_action?: string;
  market_state: string;
  market_state_label: string;
  opportunity: string;
  conviction: string;
  conviction_label: string;
  action: string;
  is_trade: boolean;
  recommended_lots: number;
  max_safe_lots: number;
  next_add_levels: (number | null)[];
  entry?: number | null;
  stop_loss?: number | null;
  target1?: number | null;
  target2?: number | null;
  target3?: number | null;
  reward_risk?: number | null;
  entry_window: string;
  action_state: string;
  reason: string;
  grade: string;
}

export interface ScanRow {
  symbol: string;
  market_type: string;
  ltp: number;
  change_pct: number;
  volume_surge: boolean;
  oi_shift_pct: number;
  breakout: boolean;
  breakdown: boolean;
  score: number;
  bias: string;
}
