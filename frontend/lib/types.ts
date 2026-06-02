export type SystemStatus = {
  app_name?: string;
  env?: string;
  data_source?: string;
  status?: string;
};

export type WatchlistItem = {
  rank?: number;
  enhanced_rank?: number;
  code: string;
  name?: string;
  total_score?: number;
  base_total_score?: number;
  capital_flow_adjustment?: number;
  capital_flow_source?: string;
  news_alpha_adjustment?: number;
  ai_adjustment?: number;
  enhanced_score?: number;
  ai_reasons?: string | string[];
  reasons?: string;
  top_news_events?: NewsEvent[];
};

export type AnalyzeTopItem = WatchlistItem & {
  original_rank?: number;
  new_rank?: number;
  original_score?: number;
  ai_adjusted_score?: number;
  fetched_news_count?: number;
  valid_alpha_event_count?: number;
  news_alpha_summary?: string;
  risk_flags?: string[];
  confidence?: number;
};

export type NewsEvent = {
  title?: string;
  source?: string;
  publish_time?: string;
  event_type?: string;
  impact_direction?: string;
  relevance_score?: number;
  importance_score?: number;
  freshness_score?: number;
  confidence?: number;
};

export type TradePlan = {
  id?: number;
  trade_date: string;
  watch_symbols: string[];
  focus_sectors: string[];
  market_view: string;
  bull_case: string;
  bear_case: string;
  max_position: number;
  planned_trades: unknown[];
  risk_notes: string[];
};

export type DailyReview = {
  id?: number;
  review_date: string;
  status?: string;
  market_score: number;
  market_environment: string;
  emotion_score: number;
  execution_score: number;
  discipline_score: number;
  daily_pnl: number;
  max_drawdown: number;
  largest_winner: string;
  largest_loser: string;
  mistakes: string[];
  good_decisions: string[];
  lessons_learned: string[];
  tomorrow_plan: string;
};

export type TradeLog = {
  id?: number;
  trade_date: string;
  symbol: string;
  action: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  planned_trade: boolean;
  actual_reason: string;
  result_score: number;
  notes: string;
};

export type PlanDrift = {
  discipline_score: number;
  violations: Array<{ type?: string; symbol?: string; severity?: number; message?: string }>;
  summary: string;
};

export type ReviewStats = {
  days: number;
  win_rate: number;
  average_pnl: number;
  max_drawdown: number;
  average_discipline_score: number;
  consecutive_profit_days: number;
  consecutive_loss_days: number;
};

export type AIReviewSummary = {
  strengths: string[];
  weaknesses: string[];
  repeated_mistakes: string[];
  discipline_score: number;
  risk_score: number;
  suggestions: string[];
};
