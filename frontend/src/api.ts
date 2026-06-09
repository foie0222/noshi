// noshi API クライアント。本番は Cognito の Bearer トークン、ローカルはスタブ認証（X-User-Id）。

import { authEnabled, getIdToken } from "./lib/cognito";
import type {
  AnnualSummary,
  CaptureResponse,
  Direction,
  EventView,
  GiftRecord,
  GiftTax,
  HalfReturn,
  HomeResponse,
  Household,
  LedgerResponse,
  Letter,
  Relationship,
  RelationshipMaster,
  Suggestion,
} from "./types";

// 開発用: 家族共有を体験できるよう識別子を切替可能（localStorage）。本番はトークンの sub を使う。
export function currentUserId(): string {
  return localStorage.getItem("noshi-user") || "demo-user";
}
export function setCurrentUserId(id: string) {
  localStorage.setItem("noshi-user", id.trim() || "demo-user");
}

// 本番は CloudFront とは別オリジンの API Gateway を叩く（ビルド時に VITE_API_BASE を注入）。
// 未設定（ローカル）は同一オリジンの /api を Vite プロキシ経由で叩く。
const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

export class UnauthorizedError extends Error {}

function authHeaders(): Record<string, string> {
  // Cognito 有効時は Bearer トークン。それ以外は開発用スタブ。
  if (authEnabled()) return { Authorization: `Bearer ${getIdToken()}` };
  return { "X-User-Id": currentUserId() };
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers || {}),
    },
  });
  if (res.status === 401) throw new UnauthorizedError("ログインが必要です");
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(typeof body.detail === "string" ? body.detail : "リクエストに失敗しました");
  }
  return res.json() as Promise<T>;
}

export interface RecordInput {
  amount: number;
  purpose: string;
  party_name: string;
  direction: Direction;
  occurred_at?: string;
  relationship?: string;
}

export const api = {
  home: () => req<HomeResponse>("/home"),
  ledger: () => req<LedgerResponse>("/ledger"),
  capture: (image?: string) =>
    req<CaptureResponse>("/capture", {
      method: "POST",
      body: JSON.stringify({ image: image ?? null }),
    }),
  createRecord: (r: RecordInput) =>
    req<{ record: GiftRecord; event: EventView | null }>("/records", {
      method: "POST",
      body: JSON.stringify(r),
    }),
  updateRecord: (
    recordId: string,
    r: {
      amount: number;
      purpose: string;
      party_name: string;
      occurred_at?: string;
      relationship?: string;
    },
  ) =>
    req<{ record: GiftRecord }>(`/records/${recordId}`, {
      method: "PATCH",
      body: JSON.stringify(r),
    }),
  setEventDue: (eventId: string, dueAt: string | null) =>
    req<{ event: EventView }>(`/events/${eventId}/due`, {
      method: "PUT",
      body: JSON.stringify({ due_at: dueAt }),
    }),
  halfReturn: (amount: number, purpose: string) =>
    req<HalfReturn>(`/returns/half-return?amount=${amount}&purpose=${encodeURIComponent(purpose)}`),
  suggestions: (eventId: string, budget: number, relationship: string, purpose: string) =>
    req<{ suggestions: Suggestion[] }>(
      `/events/${eventId}/suggestions?budget=${budget}&relationship=${encodeURIComponent(relationship)}&purpose=${encodeURIComponent(purpose)}`,
    ),
  selectSuggestion: (eventId: string, s: Suggestion) =>
    req<{ suggestion: Suggestion }>(`/events/${eventId}/suggestion`, {
      method: "POST",
      body: JSON.stringify(s),
    }),
  letter: (eventId: string, purpose: string, relationship: string, tone: string) =>
    req<{ letter: Letter }>(`/events/${eventId}/letter`, {
      method: "POST",
      body: JSON.stringify({ purpose, relationship, tone }),
    }),
  setStatus: (eventId: string, status: string) =>
    req<{ event: EventView }>(`/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  getEvent: (eventId: string) => req<{ event: EventView }>(`/events/${eventId}`),
  eventForRecord: (recordId: string) => req<{ event: EventView }>(`/records/${recordId}/event`),
  giftTax: () => req<GiftTax>("/gift-tax"),
  annual: (year?: number) => req<AnnualSummary>(`/annual${year ? `?year=${year}` : ""}`),
  household: () => req<{ household: Household }>("/household"),
  joinHousehold: (code: string) =>
    req<{ household: Household }>("/household/join", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  leaveHousehold: () => req<{ household: Household }>("/household/leave", { method: "POST" }),
  removeMember: (userId: string) =>
    req<{ household: Household }>(`/household/members/${encodeURIComponent(userId)}`, {
      method: "DELETE",
    }),
  relationships: () => req<{ relationships: Relationship[] }>("/relationships"),
  relationshipMaster: () => req<RelationshipMaster>("/relationship-master"),
  addRelationship: (name: string) =>
    req<RelationshipMaster>("/relationship-master", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  removeRelationship: (name: string) =>
    req<RelationshipMaster>(`/relationship-master/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
};
