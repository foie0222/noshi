import { useEffect, useState } from "react";
import { api, RecordInput } from "./api";
import { yen, statusLabel, daysLeftLabel } from "./lib/format";
import { toneOf } from "./lib/tone";
import { seasonOf, seasonNudge } from "./lib/season";
import { otoshidamaRange } from "./lib/otoshidama";
import { validateImageFile, fileToDataUrl } from "./lib/image";
import { copyText } from "./lib/clipboard";

type Screen =
  | "login" | "home" | "capture" | "review" | "ledger"
  | "half" | "suggest" | "letter" | "event" | "mypage";

const TrustNote = () => (
  <div className="trustnote">🔒 ここに入れた情報は<b>あなただけ</b>が見られます。暗号化して保存します。</div>
);

export function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [toast, setToast] = useState<string>("");
  const [home, setHome] = useState<any>(null);
  const [ledger, setLedger] = useState<any>(null);
  const [giftTax, setGiftTax] = useState<any>(null);
  const [annual, setAnnual] = useState<any>(null);
  const [relationships, setRelationships] = useState<any[] | null>(null);
  const [otoshiAge, setOtoshiAge] = useState<string>("");
  const [draft, setDraft] = useState<any>(null);            // 抽出/手入力中のレコード
  const [event, setEvent] = useState<any>(null);            // 進行中のお返し対象
  const [range, setRange] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [letterText, setLetterText] = useState<string>("");
  const [fontLarge, setFontLarge] = useState<boolean>(() => localStorage.getItem("noshi-font") === "large");
  const [celebrate, setCelebrate] = useState<boolean>(false); // 水引の完了演出
  const [capturedImage, setCapturedImage] = useState<string>(""); // 撮影/選択した画像(dataURL)
  const [extracting, setExtracting] = useState<boolean>(false);
  const [editDraft, setEditDraft] = useState<any>(null);     // 記録の修正中(AI抽出の訂正)

  async function onPickImage(file: File | null) {
    const err = validateImageFile(file);
    if (err) { notify(err); return; }
    try {
      const dataUrl = await fileToDataUrl(file as File);
      setCapturedImage(dataUrl);
    } catch { notify("画像を読み込めませんでした。"); }
  }

  const notify = (m: string) => { setToast(m); setTimeout(() => setToast(""), 1500); };
  const go = (s: Screen) => setScreen(s);
  const nudge = seasonNudge(seasonOf(new Date().getMonth() + 1));

  function toggleFont() {
    const next = !fontLarge;
    setFontLarge(next);
    localStorage.setItem("noshi-font", next ? "large" : "normal");
  }

  async function loadHome() { setHome(await api.home()); }
  async function loadLedger() { setLedger(await api.ledger()); }

  useEffect(() => {
    if (screen === "home") loadHome().catch((e) => notify(e.message));
    if (screen === "ledger") loadLedger().catch((e) => notify(e.message));
    if (screen === "mypage") {
      api.giftTax().then(setGiftTax).catch((e) => notify(e.message));
      api.annual().then(setAnnual).catch((e) => notify(e.message));
      api.relationships().then((r) => setRelationships(r.relationships)).catch((e) => notify(e.message));
    }
  }, [screen]);

  // ---- 撮影 → 抽出 ----
  async function doCapture() {
    if (!capturedImage) { notify("先に写真を撮るか、画像を選んでください。"); return; }
    setExtracting(true);
    try {
      // 画像から AI 抽出（MVP はモック。実プロバイダは OcrLlmPort で差し替え）。
      const job = await api.capture();
      setDraft({ ...job.candidates, direction: "received", field_review: job.field_review || {}, image: capturedImage });
      go("review");
    } catch (e: any) { notify(e.message); }
    finally { setExtracting(false); }
  }

  function startCapture() {
    setCapturedImage("");
    go("capture");
  }

  async function saveRecord() {
    try {
      const input: RecordInput = {
        amount: Number(draft.amount), purpose: draft.purpose,
        party_name: draft.party_name, direction: draft.direction,
        occurred_at: draft.occurred_at || "", relationship: draft.relationship || "",
      };
      const res = await api.createRecord(input);
      setEvent(res.event);
      notify("記録しました");
      go("home");
    } catch (e: any) { notify(e.message); }
  }

  // ---- イベントを開く（相手・用途・金額つき） ----
  async function openEvent(eventId: string) {
    try { const r = await api.getEvent(eventId); setEvent(r.event); setEditDraft(null); go("event"); }
    catch (e: any) { notify(e.message); }
  }
  async function openEventForRecord(recordId: string) {
    try { const r = await api.eventForRecord(recordId); setEvent(r.event); setEditDraft(null); go("event"); }
    catch (e: any) { notify(e.message); }
  }

  // ---- 記録の修正（AI抽出の誤りを本人が訂正）----
  function startEdit() {
    setEditDraft({ amount: String(event.amount), purpose: event.purpose, party_name: event.party_name });
  }
  async function saveEdit() {
    try {
      const amount = Number(editDraft.amount);
      if (!amount || amount <= 0) { notify("金額は1円以上で入力してください。"); return; }
      if (!editDraft.purpose.trim() || !editDraft.party_name.trim()) { notify("用途と相手は必須です。"); return; }
      await api.updateRecord(event.record_id, {
        amount, purpose: editDraft.purpose.trim(), party_name: editDraft.party_name.trim(),
      });
      const r = await api.getEvent(event.id);   // 修正後の表示を取り直す
      setEvent(r.event);
      setEditDraft(null);
      notify("修正しました");
    } catch (e: any) { notify(e.message); }
  }

  // ---- お返し ----
  async function startReturn(ev: any) {
    setEvent(ev);
    const r = await api.halfReturn(ev.amount, ev.purpose);
    setRange({ ...r, amount: ev.amount, purpose: ev.purpose });
    go("half");
  }
  async function loadSuggestions() {
    const r = await api.suggestions(event.id, range.recommended, "友人", range.purpose);
    setSuggestions(r.suggestions);
    go("suggest");
  }
  async function chooseSuggestion(s: any) {
    await api.selectSuggestion(event.id, s);
    notify("お返しを選びました");
    go("letter");
  }
  async function makeLetter() {
    // 弔事(香典等)は弔事トーンで生成。慶事と同じ文面にしない。
    const tone = toneOf(range.purpose) === "mourning" ? "弔事" : "丁寧";
    const r = await api.letter(event.id, range.purpose, "友人", tone);
    setLetterText(r.letter.body_text);
  }
  async function complete() {
    await api.setStatus(event.id, "done");
    setCelebrate(true);                       // 水引が結ばれる演出（reduced-motion 尊重）
    setTimeout(() => { setCelebrate(false); go("home"); }, 1600);
  }

  const Bar = ({ title, back }: { title: string; back?: Screen }) => (
    <div className="appbar">
      {back ? <div className="back" onClick={() => go(back)}>‹</div> : <div style={{ width: 28 }} />}
      <div className="title">{title}</div>
      <div style={{ width: 28 }} />
    </div>
  );

  return (
    <div className={"phone" + (fontLarge ? " font-large" : "")}>
      {celebrate && (
        <div className="celebrate" role="status" aria-label="お返しを完了しました">
          <svg width="160" height="90" viewBox="0 0 160 90">
            <path className="mizu1" d="M20 60 C 55 15, 105 15, 140 60" fill="none" stroke="#b23a2e" stroke-width="4" stroke-linecap="round"/>
            <path className="mizu2" d="M20 66 C 55 21, 105 21, 140 66" fill="none" stroke="#a9863f" stroke-width="4" stroke-linecap="round"/>
            <circle cx="80" cy="45" r="6" fill="#b23a2e"/>
          </svg>
          <div className="celebrate-text">お返し、完了しました</div>
        </div>
      )}
      {screen === "login" && (
        <>
          <div className="brand">のし</div>
          <div className="brand-en">N O S H I</div>
          <p className="muted" style={{ textAlign: "center" }}>贈答を、ちゃんと続けられる。</p>
          <button className="btn primary" aria-label="noshi をはじめる" onClick={() => go("home")}>noshi をはじめる</button>
        </>
      )}

      {screen === "home" && home && (
        <>
          <Bar title="noshi" />
          {nudge && <div className="nudge">🎁 {nudge}</div>}
          {home.pending.length === 0 && home.recent.length === 0 ? (
            <div className="onboard">
              <div className="onboard-emoji" aria-hidden="true">🧧</div>
              <div className="h" style={{ textAlign: "center" }}>まず1枚、撮ってみましょう</div>
              <p className="muted" style={{ textAlign: "center" }}>頂いた贈答を撮るだけで、お返しまでご案内します。</p>
            </div>
          ) : (
            <>
              <div className="h">お返しの予定</div>
              <p className="muted">期限の近い順。タップしてお返しへ。</p>
              {home.pending.length === 0 && <p className="muted" style={{ marginTop: 16 }}>いま必要なお返しはありません。</p>}
            </>
          )}
          {home.pending.map((e: any) => {
            const overdue = e.days_left !== null && e.days_left < 0;
            const soon = e.days_left !== null && e.days_left <= 3;
            return (
              <div className="card tap" key={e.id} onClick={() => openEvent(e.id)}>
                <div className="between">
                  <b>{e.party_name} 様</b>
                  <span className="duebadge" style={{
                    color: overdue ? "var(--shu)" : soon ? "var(--kin)" : "var(--ink-soft)",
                    fontWeight: overdue || soon ? 700 : 400,
                  }}>{daysLeftLabel(e.days_left)}</span>
                </div>
                <div className="muted">{e.purpose} ・ {yen(e.amount)} ・ {statusLabel(e.status)}</div>
              </div>
            );
          })}
        </>
      )}

      {screen === "capture" && (
        <>
          <Bar title="撮影" back="home" />
          <p className="muted" style={{ marginTop: 6 }}>ご祝儀袋・のし・送り状を撮影、または画像を選んでください。</p>

          <label className="dropzone" htmlFor="noshi-camera" aria-label="写真を撮る・画像を選ぶ">
            {capturedImage ? (
              <img className="capture-preview" src={capturedImage} alt="撮影した画像" />
            ) : (
              <><div className="dz-emoji" aria-hidden="true">📷</div><div className="muted">タップして撮影 / 画像を選ぶ</div></>
            )}
          </label>
          <input id="noshi-camera" className="visually-hidden" type="file" accept="image/*" capture="environment"
            onChange={(e) => onPickImage(e.target.files?.[0] ?? null)} />

          {capturedImage && (
            <label className="btn ghost" htmlFor="noshi-camera" style={{ marginTop: 8 }}>撮り直す / 別の画像</label>
          )}
          <button className="btn primary" disabled={!capturedImage || extracting} onClick={doCapture}>
            {extracting ? "読み取り中…" : "この画像で読み取る"}
          </button>
          <TrustNote />
        </>
      )}

      {screen === "review" && draft && (() => {
        const fields = ["amount", "party_name", "relationship", "purpose", "occurred_at"] as const;
        const labels: any = { amount: "金額", party_name: "お相手", relationship: "続柄", purpose: "用途", occurred_at: "日付" };
        const fr = draft.field_review || {};
        const reviewCount = fields.filter((k) => fr[k]).length;
        return (
          <>
            <Bar title="内容を確認" back="capture" />
            {draft.image && <img className="review-image" src={draft.image} alt="撮影した画像" />}
            <p className="muted" style={{ marginTop: 6 }}>
              {reviewCount > 0
                ? `ほぼ読み取れました。${reviewCount}か所だけ確認してください。`
                : "読み取れました。問題なければ保存できます。"}
            </p>
            <div className="field">
              <label>種類</label>
              <div className="chips">
                {([["received", "もらった"], ["given", "あげた"]] as const).map(([d, lbl]) => (
                  <span key={d} className={"chip " + (draft.direction === d ? "on" : "")}
                    role="button" aria-label={lbl} aria-pressed={draft.direction === d}
                    onClick={() => setDraft({ ...draft, direction: d })}>{lbl}</span>
                ))}
              </div>
            </div>
            {fields.map((k) => {
              const warn = !!fr[k];
              return (
                <div className="field" key={k}>
                  <label>{labels[k]}{warn ? <span className="reviewbadge">要確認</span> : <span className="okbadge">✓ 確定</span>}</label>
                  <input className={"input" + (warn ? " warn" : "")} value={draft[k] ?? ""}
                    onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} />
                </div>
              );
            })}
            <TrustNote />
            <button className="btn primary" onClick={saveRecord}>確認して保存</button>
          </>
        );
      })()}

      {screen === "ledger" && ledger && (
        <>
          <Bar title="贈答の台帳" />
          {ledger.records.length === 0 && <p className="muted">記録がありません</p>}
          {ledger.records.map((r: any) => (
            <div className="listitem" key={r.id} onClick={() => openEventForRecord(r.id)}>
              <span className={`dirpill dir-${r.direction}`}>{r.direction === "received" ? "受領" : "贈与"}</span>
              <div style={{ flex: 1 }}><b>{r.party_name}</b><div className="muted">{r.purpose}</div></div>
              <div className="amount">{yen(r.amount)}</div>
            </div>
          ))}
        </>
      )}

      {screen === "half" && range && (
        <>
          <Bar title="半返し" back="home" />
          <div className="card"><span className="muted">もらった額</span><div className="amount">{yen(range.amount)}</div></div>
          <div className="card"><span className="muted">推奨お返し額</span><div className="range">{yen(range.low)}〜{yen(range.high)}</div></div>
          <div className="card"><span className="muted">根拠</span><div>{range.rationale}</div></div>
          <button className="btn primary" onClick={loadSuggestions}>次へ（お返し品）</button>
        </>
      )}

      {screen === "suggest" && (
        <>
          <Bar title="お返し品の提案" back="half" />
          {suggestions.map((s, i) => (
            <div className="card" key={i}>
              <b>{s.title}</b><div className="muted">{s.summary} ・ {s.price_band} ・ 外部サイト↗</div>
              <button className="btn" style={{ height: 40 }} onClick={() => chooseSuggestion(s)}>これにする</button>
            </div>
          ))}
        </>
      )}

      {screen === "letter" && (
        <>
          <Bar title="礼状の文面" back="suggest" />
          <button className="btn ghost" onClick={makeLetter}>文面を生成する</button>
          {letterText && <div className="letterpaper">{letterText}</div>}
          {letterText && (
            <button className="btn" onClick={async () => {
              notify(await copyText(letterText) ? "文面をコピーしました" : "コピーできませんでした。長押しで選択してください。");
            }}>📋 文面をコピー</button>
          )}
          <button className="btn primary" onClick={complete}>このお礼で完了にする</button>
        </>
      )}

      {screen === "event" && event && (() => {
        const mourning = toneOf(event.purpose) === "mourning";
        return (
          <div className={mourning ? "mourning" : ""}>
            <Bar title={mourning ? "弔事のお返し" : "贈答の詳細"} back="home" />
            {mourning && <div className="mournnote">お悔やみの贈答です。落ち着いてお返しを進めましょう。</div>}
            {!editDraft ? (
              <div className="card">
                <b style={{ fontFamily: "var(--serif)", fontSize: 17 }}>{event.party_name} 様</b>
                <div className="muted">{event.purpose} ・ {yen(event.amount)} ・ {event.direction === "received" ? "受領" : "贈与"}</div>
                <button className="btn ghost" style={{ height: 38, marginTop: 8 }} onClick={startEdit}>✎ 内容を修正</button>
              </div>
            ) : (
              <div className="card">
                <div className="h" style={{ fontSize: 14 }}>内容を修正</div>
                <label className="field">相手のお名前
                  <input value={editDraft.party_name} onChange={(e) => setEditDraft({ ...editDraft, party_name: e.target.value })} />
                </label>
                <label className="field">用途
                  <input value={editDraft.purpose} onChange={(e) => setEditDraft({ ...editDraft, purpose: e.target.value })} />
                </label>
                <label className="field">金額（円）
                  <input type="number" inputMode="numeric" value={editDraft.amount} onChange={(e) => setEditDraft({ ...editDraft, amount: e.target.value })} />
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn primary" style={{ flex: 1 }} onClick={saveEdit}>保存する</button>
                  <button className="btn ghost" style={{ flex: 1 }} onClick={() => setEditDraft(null)}>やめる</button>
                </div>
              </div>
            )}
            <div className="h" style={{ fontSize: 14 }}>ステータス</div>
            <div className="chips">
              {["received", "considering", "done"].map((st) => (
                <span key={st} className={`chip ${event.status === st ? "on" : ""}`}
                  onClick={async () => { const r = await api.setStatus(event.id, st); setEvent(r.event); notify("更新しました"); }}>
                  {statusLabel(st)}
                </span>
              ))}
            </div>
            {event.direction === "received" && (
              <button className={mourning ? "btn" : "btn shu"} onClick={() => startReturn(event)}>
                {mourning ? "お返し（香典返し）を進める" : "お返しの続き（半返し→提案→礼状）"}
              </button>
            )}
          </div>
        );
      })()}

      {screen === "mypage" && (
        <>
          <Bar title="マイページ" />
          {annual && (
            <>
              <div className="h" style={{ fontSize: 15 }}>{annual.year}年の振り返り</div>
              <div className="card">
                {annual.received_count === 0 && annual.given_count === 0 ? (
                  <div className="muted">今年の記録はまだありません。撮影して残しましょう。</div>
                ) : (
                  <>
                    <div style={{ display: "flex", gap: 12 }}>
                      <div style={{ flex: 1 }}>
                        <div className="muted">いただいた</div>
                        <div className="amount" style={{ fontSize: 20 }}>{yen(annual.received_total)}</div>
                        <div className="muted">{annual.received_count}件</div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className="muted">贈った</div>
                        <div className="amount" style={{ fontSize: 20 }}>{yen(annual.given_total)}</div>
                        <div className="muted">{annual.given_count}件</div>
                      </div>
                    </div>
                    <div className="muted" style={{ marginTop: 10 }}>
                      今年は <b>{annual.party_count}</b> 人の方とご縁がありました。
                    </div>
                  </>
                )}
              </div>
            </>
          )}
          <div className="h" style={{ fontSize: 15 }}>贈与税の目安</div>
          {giftTax && (
            <div className="card">
              <div className="muted">今年もらった（対象）合計</div>
              <div className="amount" style={{ fontSize: 20 }}>{yen(giftTax.total)}</div>
              <div style={{ marginTop: 8 }}>
                {giftTax.over
                  ? <span style={{ color: "var(--shu)", fontWeight: 700 }}>110万円の枠を超えています。確認しましょう。</span>
                  : <span className="muted">110万円まで <b>あと {yen(giftTax.remaining)}</b></span>}
              </div>
              <div className="disclaimer">※ 香典・お中元・お歳暮などは除外した概算です。これは税アドバイスではなく気づきのための目安です。正確な要否は専門家にご確認ください。</div>
            </div>
          )}
          <div className="h" style={{ fontSize: 15 }}>お年玉の目安</div>
          <div className="card">
            <div className="field" style={{ marginTop: 0 }}>
              <label htmlFor="otoshi-age">お子さんの年齢</label>
              <input id="otoshi-age" className="input" type="number" inputMode="numeric" min={0} max={25}
                placeholder="例）8" value={otoshiAge} aria-label="お子さんの年齢"
                onChange={(e) => setOtoshiAge(e.target.value)} />
            </div>
            {otoshiAge !== "" && !Number.isNaN(Number(otoshiAge)) && (() => {
              const r = otoshidamaRange(Number(otoshiAge));
              return (
                <div style={{ marginTop: 12 }}>
                  <div className="muted">{r.bracket}</div>
                  <div className="range" style={{ fontSize: 22 }}>
                    {r.low === r.high ? yen(r.low) : `${yen(r.low)}〜${yen(r.high)}`}
                  </div>
                  <div className="muted" style={{ marginTop: 4 }}>{r.note}</div>
                </div>
              );
            })()}
            <div className="disclaimer">※ 家庭・地域で異なる一般的な目安です。</div>
          </div>

          <div className="h" style={{ fontSize: 15, marginTop: 20 }}>おつきあい</div>
          <p className="muted">関係のメンテナンス。気になる関係をそっとお知らせします。</p>
          {relationships && relationships.length === 0 && <p className="muted" style={{ marginTop: 8 }}>まだ記録がありません。</p>}
          {relationships && relationships.map((r: any) => {
            const label = r.status === "owe" ? "もらい多め" : r.status === "ahead" ? "お贈り多め" : "均衡";
            return (
              <div className="card" key={r.party_name}>
                <div className="between">
                  <b className="val">{r.party_name} 様</b>
                  <span className={"balbadge " + r.status}>{r.attention ? "気になる関係" : label}</span>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  もらった {yen(r.received)} ／ あげた {yen(r.given)} ・ 最終 {r.last_at || "—"}
                </div>
                {r.attention && <div className="muted" style={{ marginTop: 4, color: "var(--kin)" }}>しばらくお贈りしていません。折を見て一言いかがでしょう。</div>}
              </div>
            );
          })}

          <div className="h" style={{ fontSize: 15, marginTop: 20 }}>表示</div>
          <div className="card">
            <div className="between">
              <span>文字を大きくする</span>
              <button className={"toggle" + (fontLarge ? " on" : "")} role="switch" aria-checked={fontLarge}
                aria-label="文字を大きくする" onClick={toggleFont}><span className="knob" /></button>
            </div>
          </div>

          <div className="h" style={{ fontSize: 15, marginTop: 20 }}>プライバシー</div>
          <div className="card"><TrustNote />
            <div className="muted" style={{ marginTop: 8 }}>贈り先の情報も含め、あなたのデータはいつでも書き出し・削除できます。</div>
          </div>
        </>
      )}

      {screen !== "login" && (
        <div className="tabbar">
          <button className={screen === "home" ? "on" : ""} aria-label="ホーム" onClick={() => go("home")}>ホーム</button>
          <button className={screen === "ledger" ? "on" : ""} aria-label="台帳" onClick={() => go("ledger")}>台帳</button>
          <button className="fab" aria-label="贈答を撮影して記録" onClick={startCapture}>＋</button>
          <button className={screen === "mypage" ? "on" : ""} aria-label="マイページ" onClick={() => go("mypage")}>マイページ</button>
          <button className="spacer" aria-hidden="true" tabIndex={-1}></button>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
