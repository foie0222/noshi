import { useEffect, useRef, useState } from "react";
import { api, RecordInput, currentUserId, setCurrentUserId, UnauthorizedError } from "./api";
import { authEnabled, isLoggedIn, currentEmail, signIn, signUp, confirmSignUp, signOut, forgotPassword, confirmForgotPassword } from "./lib/cognito";
import { yen, statusLabel, daysLeftLabel } from "./lib/format";
import { toneOf } from "./lib/tone";
import { seasonOf, seasonNudge } from "./lib/season";
import { otoshidamaRange } from "./lib/otoshidama";
import { validateImageFile, fileToDataUrl } from "./lib/image";
import { copyText } from "./lib/clipboard";
import { reviewMessage } from "./lib/review";

type Screen =
  | "login" | "home" | "capture" | "review" | "ledger"
  | "half" | "suggest" | "letter" | "event" | "mypage";

const TrustNote = () => (
  <div className="trustnote">🔒 ここに入れた情報は<b>ご家族だけ</b>が見られます。暗号化して保存します。</div>
);

export function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [toast, setToast] = useState<string>("");
  const [home, setHome] = useState<any>(null);
  const [ledger, setLedger] = useState<any>(null);
  const [giftTax, setGiftTax] = useState<any>(null);
  const [annual, setAnnual] = useState<any>(null);
  const [household, setHousehold] = useState<any>(null);
  const [joinCode, setJoinCode] = useState<string>("");
  const devUserRef = useRef<string>(currentUserId());
  // ログイン（Cognito）
  const [authMode, setAuthMode] = useState<"signin" | "signup" | "confirm" | "forgot" | "reset">("signin");
  const [authEmail, setAuthEmail] = useState<string>("");
  const [authPassword, setAuthPassword] = useState<string>("");
  const [authCode, setAuthCode] = useState<string>("");
  const [authBusy, setAuthBusy] = useState<boolean>(false);
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
  // 401（トークン切れ等）はログイン画面へ戻す。それ以外はトースト表示。
  const handleErr = (e: any) => {
    if (e instanceof UnauthorizedError) { signOut(); go("login"); notify("もう一度ログインしてください"); }
    else notify(e?.message || "エラーが発生しました");
  };

  // ---- ログイン（Cognito）----
  async function doSignIn() {
    setAuthBusy(true);
    try { await signIn(authEmail.trim(), authPassword); setAuthPassword(""); go("home"); }
    catch (e: any) { notify(e.message); } finally { setAuthBusy(false); }
  }
  async function doSignUp() {
    setAuthBusy(true);
    try { await signUp(authEmail.trim(), authPassword); setAuthMode("confirm"); notify("確認コードをメールに送りました"); }
    catch (e: any) { notify(e.message); } finally { setAuthBusy(false); }
  }
  async function doConfirm() {
    setAuthBusy(true);
    try {
      await confirmSignUp(authEmail.trim(), authCode.trim());
      await signIn(authEmail.trim(), authPassword);  // 確認後そのままログイン
      setAuthPassword(""); setAuthCode(""); go("home");
    } catch (e: any) { notify(e.message); } finally { setAuthBusy(false); }
  }
  function doSignOut() { signOut(); go("login"); notify("ログアウトしました"); }
  async function doForgot() {
    if (!authEmail.trim()) { notify("メールアドレスを入力してください。"); return; }
    setAuthBusy(true);
    try { await forgotPassword(authEmail.trim()); setAuthPassword(""); setAuthCode(""); setAuthMode("reset"); notify("確認コードをメールに送りました"); }
    catch (e: any) { notify(e.message); } finally { setAuthBusy(false); }
  }
  async function doReset() {
    setAuthBusy(true);
    try {
      await confirmForgotPassword(authEmail.trim(), authCode.trim(), authPassword);
      await signIn(authEmail.trim(), authPassword);  // 再設定後そのままログイン
      setAuthPassword(""); setAuthCode(""); go("home"); notify("パスワードを再設定しました");
    } catch (e: any) { notify(e.message); } finally { setAuthBusy(false); }
  }
  const nudge = seasonNudge(seasonOf(new Date().getMonth() + 1));

  function toggleFont() {
    const next = !fontLarge;
    setFontLarge(next);
    localStorage.setItem("noshi-font", next ? "large" : "normal");
  }

  async function loadHome() { setHome(await api.home()); }
  async function loadLedger() { setLedger(await api.ledger()); }

  // 起動時: ログイン必須環境で未ログインなら login 画面に固定。
  useEffect(() => {
    if (authEnabled() && !isLoggedIn() && screen !== "login") go("login");
  }, [screen]);

  useEffect(() => {
    if (screen === "home") loadHome().catch(handleErr);
    if (screen === "ledger") loadLedger().catch(handleErr);
    if (screen === "mypage") {
      api.giftTax().then(setGiftTax).catch(handleErr);
      api.annual().then(setAnnual).catch(handleErr);
      api.relationships().then((r) => setRelationships(r.relationships)).catch(handleErr);
      api.household().then((r) => setHousehold(r.household)).catch(handleErr);
    }
  }, [screen]);

  // ---- 撮影 → 抽出 ----
  async function doCapture() {
    if (!capturedImage) { notify("先に写真を撮るか、画像を選んでください。"); return; }
    setExtracting(true);
    try {
      // 撮影画像を送って AI 抽出（モック or Bedrock/Claude を環境変数で切替）。
      const job = await api.capture(capturedImage);
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

  // ---- 家族共有 ----
  async function doJoinHousehold() {
    const code = joinCode.trim().toUpperCase();
    if (!code) { notify("招待コードを入力してください。"); return; }
    try {
      const r = await api.joinHousehold(code);
      setHousehold(r.household);
      setJoinCode("");
      notify("ご家族に参加しました");
    } catch (e: any) { notify(e.message); }
  }
  async function doRemoveMember(userId: string, label: string) {
    if (!confirm(`${label} さんをこの家族から外しますか？\nこの方には台帳が見えなくなります。`)) return;
    try {
      const r = await api.removeMember(userId);
      setHousehold(r.household);
      notify("メンバーを外しました");
    } catch (e: any) { notify(e.message); }
  }
  async function doLeaveHousehold() {
    if (!confirm("この家族から脱退しますか？\n台帳はご家族側に残り、あなたは新しい空の状態になります。")) return;
    try {
      await api.leaveHousehold();
      notify("脱退しました");
      location.reload();   // 世帯（データの見え方）が変わるため全体を読み直す
    } catch (e: any) { notify(e.message); }
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

          {!authEnabled() ? (
            <button className="btn primary" aria-label="noshi をはじめる" onClick={() => go("home")}>noshi をはじめる</button>
          ) : (
            <div className="card" style={{ marginTop: 16 }}>
              {/* メール: signin/signup/forgot で表示 */}
              {(authMode === "signin" || authMode === "signup" || authMode === "forgot") && (
                <div className="field" style={{ marginTop: 0 }}>
                  <label htmlFor="auth-email">メールアドレス</label>
                  <input id="auth-email" className="input" type="email" autoComplete="email"
                    value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} placeholder="you@example.com" />
                </div>
              )}
              {/* パスワード: signin/signup で表示（reset は下で新パスワードを表示） */}
              {(authMode === "signin" || authMode === "signup") && (
                <div className="field">
                  <label htmlFor="auth-pw">パスワード</label>
                  <input id="auth-pw" className="input" type="password"
                    autoComplete={authMode === "signup" ? "new-password" : "current-password"}
                    value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} placeholder="8文字以上・英小文字と数字" />
                </div>
              )}

              {authMode === "signin" && (
                <>
                  <button className="btn primary" disabled={authBusy} onClick={doSignIn}>
                    {authBusy ? "ログイン中…" : "ログイン"}
                  </button>
                  <button className="btn ghost" style={{ marginTop: 8 }} disabled={authBusy}
                    onClick={() => setAuthMode("signup")}>アカウントを作成</button>
                  <button className="linklike" disabled={authBusy}
                    onClick={() => setAuthMode("forgot")}>パスワードをお忘れの方</button>
                </>
              )}

              {authMode === "forgot" && (
                <>
                  <p className="muted">登録メールに確認コードを送ります。</p>
                  <button className="btn primary" disabled={authBusy} onClick={doForgot}>
                    {authBusy ? "送信中…" : "確認コードを送る"}
                  </button>
                  <button className="btn ghost" style={{ marginTop: 8 }} disabled={authBusy}
                    onClick={() => setAuthMode("signin")}>ログインに戻る</button>
                </>
              )}

              {authMode === "reset" && (
                <>
                  <p className="muted">{authEmail} に届いた確認コードと、新しいパスワードを入力してください。</p>
                  <div className="field" style={{ marginTop: 0 }}>
                    <label htmlFor="reset-code">確認コード</label>
                    <input id="reset-code" className="input" inputMode="numeric"
                      value={authCode} onChange={(e) => setAuthCode(e.target.value)} placeholder="メールの6桁コード" />
                  </div>
                  <div className="field">
                    <label htmlFor="reset-pw">新しいパスワード</label>
                    <input id="reset-pw" className="input" type="password" autoComplete="new-password"
                      value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} placeholder="8文字以上・英小文字と数字" />
                  </div>
                  <button className="btn primary" disabled={authBusy} onClick={doReset}>
                    {authBusy ? "再設定中…" : "パスワードを再設定"}
                  </button>
                  <button className="btn ghost" style={{ marginTop: 8 }} disabled={authBusy}
                    onClick={() => setAuthMode("signin")}>ログインに戻る</button>
                </>
              )}

              {authMode === "signup" && (
                <>
                  <button className="btn primary" disabled={authBusy} onClick={doSignUp}>
                    {authBusy ? "送信中…" : "登録（確認コードを送る）"}
                  </button>
                  <button className="btn ghost" style={{ marginTop: 8 }} disabled={authBusy}
                    onClick={() => setAuthMode("signin")}>ログインに戻る</button>
                </>
              )}

              {authMode === "confirm" && (
                <>
                  <p className="muted">{authEmail} に届いた確認コードを入力してください。</p>
                  <div className="field" style={{ marginTop: 0 }}>
                    <label htmlFor="auth-code">確認コード</label>
                    <input id="auth-code" className="input" inputMode="numeric"
                      value={authCode} onChange={(e) => setAuthCode(e.target.value)} placeholder="メールの6桁コード" />
                  </div>
                  <button className="btn primary" disabled={authBusy} onClick={doConfirm}>
                    {authBusy ? "確認中…" : "確認して はじめる"}
                  </button>
                  <button className="btn ghost" style={{ marginTop: 8 }} disabled={authBusy}
                    onClick={() => setAuthMode("signin")}>ログインに戻る</button>
                </>
              )}
              <div className="trustnote" style={{ marginTop: 12 }}>🔒 メール認証で、ご家族の台帳を安全に守ります。</div>
            </div>
          )}
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
              {reviewMessage(reviewCount, fields.length)}
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
          {household && (
            <>
              <div className="h" style={{ fontSize: 15 }}>ご家族（共有）</div>
              <div className="card">
                {(() => {
                  const me = currentUserId();
                  const iAmOwner = household.members.some((m: any) => m.user_id === me && m.role === "owner");
                  return (
                    <>
                      <div className="muted">この台帳を共有しているメンバー</div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, margin: "6px 0 10px" }}>
                        {household.members.map((m: any) => {
                          const label = m.email || m.user_id;
                          const isMe = m.user_id === me;
                          return (
                            <span key={m.user_id} className="chip on">
                              {label}{m.role === "owner" ? "（管理者）" : ""}{isMe ? "・あなた" : ""}
                              {iAmOwner && !isMe && (
                                <button className="memberx" aria-label={`${label} を外す`}
                                  onClick={() => doRemoveMember(m.user_id, label)}>✕</button>
                              )}
                            </span>
                          );
                        })}
                      </div>
                    </>
                  );
                })()}
                <div className="muted">家族を招待するコード（伝えると同じ台帳を共有できます）</div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "4px 0 6px" }}>
                  <code className="invitecode">{household.invite_code}</code>
                  <button className="btn" style={{ height: 38, width: "auto", padding: "0 12px" }}
                    onClick={async () => notify(await copyText(household.invite_code) ? "コードをコピーしました" : "コピーできませんでした")}>
                    コピー
                  </button>
                </div>
                <div className="muted" style={{ marginTop: 10 }}>家族から受け取ったコードで参加する</div>
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <input className="input" style={{ flex: 1 }} placeholder="招待コード"
                    value={joinCode} onChange={(e) => setJoinCode(e.target.value)} aria-label="招待コード" />
                  <button className="btn primary" style={{ width: "auto", padding: "0 16px" }}
                    onClick={doJoinHousehold}>参加</button>
                </div>
                <div className="trustnote" style={{ marginTop: 10 }}>🔒 台帳は<b>このご家族だけ</b>が見られます。</div>
                {household.members.length > 1 && (
                  <button className="btn ghost danger" style={{ marginTop: 10 }}
                    onClick={doLeaveHousehold}>この家族から脱退する</button>
                )}
              </div>
            </>
          )}
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
            <div className="muted" style={{ marginTop: 8 }}>贈り先の情報も含め、ご家族のデータはいつでも書き出し・削除できます。</div>
          </div>

          <div className="h" style={{ fontSize: 15, marginTop: 20 }}>アカウント</div>
          {authEnabled() ? (
            <div className="card">
              <div className="muted">ログイン中</div>
              <div style={{ fontFamily: "var(--serif)", margin: "2px 0 10px" }}>{currentEmail() || "—"}</div>
              <button className="btn ghost danger" onClick={doSignOut}>ログアウト</button>
            </div>
          ) : (
            <div className="card" style={{ borderStyle: "dashed" }}>
              <div className="muted">🛠 開発用: ログイン中のユーザー（本番は Cognito ログイン）</div>
              <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                <input className="input" style={{ flex: 1 }} defaultValue={currentUserId()} aria-label="ユーザー識別子"
                  onChange={(e) => (devUserRef.current = e.target.value)} />
                <button className="btn" style={{ width: "auto", padding: "0 14px" }}
                  onClick={() => { setCurrentUserId(devUserRef.current ?? currentUserId()); location.reload(); }}>
                  切替
                </button>
              </div>
              <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                別の人に切替→相手の招待コードで「参加」すると、同じ台帳が共有されます。
              </div>
            </div>
          )}
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
