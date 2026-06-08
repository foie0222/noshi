// noshi API クライアント。本番は Cognito の Bearer トークン、ローカルはスタブ認証（X-User-Id）。

import { authEnabled, getIdToken } from "./lib/cognito";

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

async function req(path: string, init: RequestInit = {}) {
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
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "リクエストに失敗しました");
  }
  return res.json();
}

export interface RecordInput {
  amount: number;
  purpose: string;
  party_name: string;
  direction: "received" | "given";
  occurred_at?: string;
  relationship?: string;
}

export const api = {
  home: () => req("/home"),
  ledger: () => req("/ledger"),
  capture: (image?: string) =>
    req("/capture", { method: "POST", body: JSON.stringify({ image: image ?? null }) }),
  createRecord: (r: RecordInput) => req("/records", { method: "POST", body: JSON.stringify(r) }),
  updateRecord: (recordId: string, r: { amount: number; purpose: string; party_name: string }) =>
    req(`/records/${recordId}`, { method: "PATCH", body: JSON.stringify(r) }),
  halfReturn: (amount: number, purpose: string) =>
    req(`/returns/half-return?amount=${amount}&purpose=${encodeURIComponent(purpose)}`),
  suggestions: (eventId: string, budget: number, relationship: string, purpose: string) =>
    req(
      `/events/${eventId}/suggestions?budget=${budget}&relationship=${encodeURIComponent(relationship)}&purpose=${encodeURIComponent(purpose)}`,
    ),
  selectSuggestion: (eventId: string, s: any) =>
    req(`/events/${eventId}/suggestion`, { method: "POST", body: JSON.stringify(s) }),
  letter: (eventId: string, purpose: string, relationship: string, tone: string) =>
    req(`/events/${eventId}/letter`, {
      method: "POST",
      body: JSON.stringify({ purpose, relationship, tone }),
    }),
  setStatus: (eventId: string, status: string) =>
    req(`/events/${eventId}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  getEvent: (eventId: string) => req(`/events/${eventId}`),
  eventForRecord: (recordId: string) => req(`/records/${recordId}/event`),
  giftTax: () => req(`/gift-tax`),
  annual: (year?: number) => req(`/annual${year ? `?year=${year}` : ""}`),
  household: () => req(`/household`),
  joinHousehold: (code: string) =>
    req(`/household/join`, { method: "POST", body: JSON.stringify({ code }) }),
  leaveHousehold: () => req(`/household/leave`, { method: "POST" }),
  removeMember: (userId: string) =>
    req(`/household/members/${encodeURIComponent(userId)}`, { method: "DELETE" }),
  relationships: () => req(`/relationships`),
};
