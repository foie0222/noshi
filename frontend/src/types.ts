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
  item: string;
  relationship: string;
  memo: string;
}

/** 相手（人）。同名でも別人を ID で区別する（#47）。 */
export interface Party {
  id: string;
  name: string;
  relationship: string;
}

export interface EventView {
  id: string;
  status: string;
  record_id: string;
  party_id: string;
  party_name: string;
  purpose: string;
  amount: number;
  direction: Direction;
  occurred_at: string;
  item: string;
  relationship: string;
  due_at: string | null;
  due_default: string | null;
  due_overridden: boolean;
  days_left: number | null;
  suggestion_id: string | null;
  image_url: string | null;
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
  // 楽天カタログ由来の拡張（バックエンドが規約24h−1hの23hマスク済みのものだけ送る）
  price?: number;
  price_fetched_at?: string;
  sale_note?: string;
  image_url?: string;
  shop_name?: string;
  rating?: number;
  review_count?: number;
  item_code?: string;
  bucket?: string;
  position?: number;
  rel_group?: string; // 配信時の続柄グループ（クリック計測で echo する）
}

export interface CaptureCandidates {
  amount: number | string;
  party_name: string;
  relationship: string;
  purpose: string;
  occurred_at: string;
  item: string; // 品物（読めたら自動入力、ダメなら空で手入力）
}

// 非同期OCR: capture は pending（job_id+status のみ）を返し、worker 完了後に
// GET /capture/{job_id} で候補が入る。完了時のみ candidates 以下が存在する。
export interface CaptureResponse {
  job_id: string;
  status: string; // pending / completed / failed
  candidates?: CaptureCandidates;
  confidence?: number;
  field_confidence?: Record<string, number>;
  field_review?: Record<string, boolean>;
  needs_review?: boolean;
}

// --- クライアント側で組み立てる作業用オブジェクト ---

/** 撮影確認〜保存中の下書き（抽出候補＋方向・要確認・画像・相手ID）。 */
export type Draft = CaptureCandidates & {
  direction: Direction;
  field_review: Record<string, boolean>;
  image: string;
  party_id: string; // 選択/作成した相手（#47）
  item: string; // もらった/あげた品物（例: 現金/メガネ。任意）
};

/** 半返し画面の表示データ（算出結果＋元の金額・用途）。 */
export type Range = HalfReturn & { amount: number; purpose: string };

/** 記録修正フォーム。相手は party_id で付け替える（#47）。 */
export interface EditDraft {
  amount: string;
  purpose: string;
  occurred_at: string;
  party_id: string;
  item: string;
}

/** 続柄マスタ（システム既定＋世帯独自）。#1 */
export interface RelationshipMaster {
  options: string[];
  defaults: string[];
}

/** 不明な例外から表示用メッセージを取り出す。 */
export function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "エラーが発生しました";
}
