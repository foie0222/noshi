// API レスポンス / ドメインの型定義（backend の各レスポンス形に対応）。

export type Direction = "received" | "given";

export interface GiftRecord {
  id: string;
  user_id: string;
  party_name: string;
  amount: number;
  purpose: string;
  direction: Direction;
  occurred_at: string;
  relationship: string;
  memo: string;
}

export interface EventView {
  id: string;
  status: string;
  record_id: string;
  party_name: string;
  purpose: string;
  amount: number;
  direction: Direction;
  occurred_at: string;
  due_at: string | null;
  due_default: string | null;
  due_overridden: boolean;
  days_left: number | null;
  suggestion_id: string | null;
  letter_id: string | null;
}

export interface PartySummary {
  received: number;
  given: number;
  diff: number;
}

export interface HomeResponse {
  pending: EventView[];
  recent: GiftRecord[];
}

export interface LedgerResponse {
  records: GiftRecord[];
  party_summary: Record<string, PartySummary>;
}

export interface GiftTax {
  total: number;
  remaining: number;
  over: boolean;
  exemption: number;
  year: number;
}

export interface AnnualSummary {
  year: number;
  received_count: number;
  received_total: number;
  given_count: number;
  given_total: number;
  party_count: number;
}

export interface Member {
  user_id: string;
  role: string;
  email: string;
}

export interface Household {
  id: string;
  name: string;
  invite_code: string;
  members: Member[];
}

export interface Relationship {
  party_name: string;
  received: number;
  given: number;
  diff: number;
  last_at: string;
  status: string;
  attention: boolean;
}

export interface HalfReturn {
  recommended: number;
  low: number;
  high: number;
  ratio: number;
  rationale: string;
  gift_unneeded: boolean;
}

export interface Suggestion {
  title: string;
  summary: string;
  price_band: string;
  external_ref: string;
}

export interface Letter {
  id: string;
  event_id: string;
  tone: string;
  body_text: string;
}

export interface CaptureCandidates {
  amount: number | string;
  party_name: string;
  relationship: string;
  purpose: string;
  occurred_at: string;
}

export interface CaptureResponse {
  job_id: string;
  status: string;
  candidates: CaptureCandidates;
  confidence: number;
  field_confidence: Record<string, number>;
  field_review: Record<string, boolean>;
  needs_review: boolean;
}

// --- クライアント側で組み立てる作業用オブジェクト ---

/** 撮影確認〜保存中の下書き（抽出候補＋方向・要確認・画像）。 */
export type Draft = CaptureCandidates & {
  direction: Direction;
  field_review: Record<string, boolean>;
  image: string;
};

/** 半返し画面の表示データ（算出結果＋元の金額・用途）。 */
export type Range = HalfReturn & { amount: number; purpose: string };

/** 記録修正フォーム。 */
export interface EditDraft {
  amount: string;
  purpose: string;
  party_name: string;
  occurred_at: string;
}

/** 不明な例外から表示用メッセージを取り出す。 */
export function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "エラーが発生しました";
}
