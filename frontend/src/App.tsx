import { useEffect, useRef, useState } from "react";
import { api, currentUserId, type RecordInput, setCurrentUserId, UnauthorizedError } from "./api";
import { Drawer } from "./components/Drawer";
import { Icon, type IconName } from "./components/Icon";
import { Logo } from "./components/Logo";
import { MasterSelect } from "./components/MasterSelect";
import { copyText } from "./lib/clipboard";
import {
  authEnabled,
  confirmForgotPassword,
  confirmSignUp,
  currentEmail,
  forgotPassword,
  isLoggedIn,
  signIn,
  signOut,
  signUp,
} from "./lib/cognito";
import { daysLeftLabel, statusLabel, yen } from "./lib/format";
import { fileToDataUrl, validateImageFile } from "./lib/image";
import { otoshidamaRange } from "./lib/otoshidama";
import { reviewMessage } from "./lib/review";
import { seasonNudge, seasonOf } from "./lib/season";
import { toneOf } from "./lib/tone";
import {
  type AnnualSummary,
  type Draft,
  type EditDraft,
  type EventView,
  errMsg,
  type GiftTax,
  type HomeResponse,
  type Household,
  type LedgerResponse,
  type Range,
  type Relationship,
  type Suggestion,
} from "./types";

type Screen =
  | "login"
  | "home"
  | "capture"
  | "review"
  | "ledger"
  | "half"
  | "suggest"
  | "event"
  | "relations"
  | "mypage";

// マイページのサブページ（#3: ハンバーガー→ドロワーで切替）。
type MySection =
  | "household"
  | "annual"
  | "gifttax"
  | "otoshidama"
  | "display"
  | "privacy"
  | "account";

const MY_SECTIONS: { key: MySection; label: string; icon: IconName }[] = [
  { key: "household", label: "ご家族", icon: "users" },
  { key: "annual", label: "年間振り返り", icon: "calendar" },
  { key: "gifttax", label: "贈与税の目安", icon: "scale" },
  { key: "otoshidama", label: "お年玉の目安", icon: "gift" },
  { key: "display", label: "表示設定", icon: "settings" },
  { key: "privacy", label: "プライバシー", icon: "lock" },
  { key: "account", label: "アカウント", icon: "user" },
];

const TrustNote = () => (
  <div className="trustnote">
    <span className="ic">
      <Icon name="lock" size={18} />
    </span>
    <div>
      ここに入れた情報は<b>ご家族だけ</b>が見られます。暗号化して保存します。
    </div>
  </div>
);

export function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [toast, setToast] = useState<string>("");
  const [home, setHome] = useState<HomeResponse | null>(null);
  const [ledger, setLedger] = useState<LedgerResponse | null>(null);
  const [giftTax, setGiftTax] = useState<GiftTax | null>(null);
  const [annual, setAnnual] = useState<AnnualSummary | null>(null);
  const [household, setHousehold] = useState<Household | null>(null);
  const [joinCode, setJoinCode] = useState<string>("");
  const devUserRef = useRef<string>(currentUserId());
  // ログイン（Cognito）
  const [authMode, setAuthMode] = useState<"signin" | "signup" | "confirm" | "forgot" | "reset">(
    "signin",
  );
  const [authEmail, setAuthEmail] = useState<string>("");
  const [authPassword, setAuthPassword] = useState<string>("");
  const [authCode, setAuthCode] = useState<string>("");
  const [authBusy, setAuthBusy] = useState<boolean>(false);
  const [relationships, setRelationships] = useState<Relationship[] | null>(null);
  const [otoshiAge, setOtoshiAge] = useState<string>("");
  const [draft, setDraft] = useState<Draft | null>(null); // 抽出/手入力中のレコード
  const [event, setEvent] = useState<EventView | null>(null); // 進行中のお返し対象
  const [range, setRange] = useState<Range | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [fontLarge, setFontLarge] = useState<boolean>(
    () => localStorage.getItem("noshi-font") === "large",
  );
  const [celebrate, setCelebrate] = useState<boolean>(false); // 水引の完了演出
  const [capturedImage, setCapturedImage] = useState<string>(""); // 撮影/選択した画像(dataURL)
  const [extracting, setExtracting] = useState<boolean>(false);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null); // 記録の修正中(AI抽出の訂正)
  const [dueEditing, setDueEditing] = useState<boolean>(false); // お返し期限の編集中
  const [dueInput, setDueInput] = useState<string>(""); // 期限編集の入力値(YYYY-MM-DD)
  const [relOptions, setRelOptions] = useState<string[]>([]); // 続柄マスタの選択肢(#1)
  const [relDefaults, setRelDefaults] = useState<string[]>([]); // 既定（削除不可の判定用）
  const [purOptions, setPurOptions] = useState<string[]>([]); // 用途マスタの選択肢(#37)
  const [purDefaults, setPurDefaults] = useState<string[]>([]); // 既定（削除不可の判定用）
  const [mySection, setMySection] = useState<MySection>("household"); // マイページのサブページ(#3)
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false); // マイページのドロワー

  async function onPickImage(file: File | null) {
    const err = validateImageFile(file);
    if (err) {
      notify(err);
      return;
    }
    try {
      const dataUrl = await fileToDataUrl(file as File);
      setCapturedImage(dataUrl);
    } catch {
      notify("画像を読み込めませんでした。");
    }
  }

  const notify = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(""), 1500);
  };
  const go = (s: Screen) => setScreen(s);
  // 401（トークン切れ等）はログイン画面へ戻す。それ以外はトースト表示。
  const handleErr = (e: unknown) => {
    if (e instanceof UnauthorizedError) {
      signOut();
      go("login");
      notify("もう一度ログインしてください");
    } else notify(errMsg(e));
  };

  // ---- ログイン（Cognito）----
  async function doSignIn() {
    setAuthBusy(true);
    try {
      await signIn(authEmail.trim(), authPassword);
      setAuthPassword("");
      go("home");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setAuthBusy(false);
    }
  }
  async function doSignUp() {
    setAuthBusy(true);
    try {
      await signUp(authEmail.trim(), authPassword);
      setAuthMode("confirm");
      notify("確認コードをメールに送りました");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setAuthBusy(false);
    }
  }
  async function doConfirm() {
    setAuthBusy(true);
    try {
      await confirmSignUp(authEmail.trim(), authCode.trim());
      await signIn(authEmail.trim(), authPassword); // 確認後そのままログイン
      setAuthPassword("");
      setAuthCode("");
      go("home");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setAuthBusy(false);
    }
  }
  function doSignOut() {
    signOut();
    go("login");
    notify("ログアウトしました");
  }
  async function doForgot() {
    if (!authEmail.trim()) {
      notify("メールアドレスを入力してください。");
      return;
    }
    setAuthBusy(true);
    try {
      await forgotPassword(authEmail.trim());
      setAuthPassword("");
      setAuthCode("");
      setAuthMode("reset");
      notify("確認コードをメールに送りました");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setAuthBusy(false);
    }
  }
  async function doReset() {
    setAuthBusy(true);
    try {
      await confirmForgotPassword(authEmail.trim(), authCode.trim(), authPassword);
      await signIn(authEmail.trim(), authPassword); // 再設定後そのままログイン
      setAuthPassword("");
      setAuthCode("");
      go("home");
      notify("パスワードを再設定しました");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setAuthBusy(false);
    }
  }
  const nudge = seasonNudge(seasonOf(new Date().getMonth() + 1));

  function toggleFont() {
    const next = !fontLarge;
    setFontLarge(next);
    localStorage.setItem("noshi-font", next ? "large" : "normal");
  }

  async function loadHome() {
    setHome(await api.home());
  }
  async function loadLedger() {
    setLedger(await api.ledger());
  }

  // 起動時: ログイン必須環境で未ログインなら login 画面に固定。
  // biome-ignore lint/correctness/useExhaustiveDependencies: 画面遷移時のみ判定する意図
  useEffect(() => {
    if (authEnabled() && !isLoggedIn() && screen !== "login") go("login");
  }, [screen]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: 画面遷移時のみ再取得する意図
  useEffect(() => {
    if (screen === "home") loadHome().catch(handleErr);
    if (screen === "ledger") loadLedger().catch(handleErr);
    if (screen === "relations") {
      api
        .relationships()
        .then((r) => setRelationships(r.relationships))
        .catch(handleErr);
    }
    if (screen === "mypage") {
      api.giftTax().then(setGiftTax).catch(handleErr);
      api.annual().then(setAnnual).catch(handleErr);
      api
        .household()
        .then((r) => setHousehold(r.household))
        .catch(handleErr);
    }
    // 続柄・用途マスタは記録の確認/詳細で使う。未取得なら一度だけ読み込む（#1, #37）。
    if (screen === "review" || screen === "event") {
      if (relOptions.length === 0) {
        api
          .relationshipMaster()
          .then((m) => {
            setRelOptions(m.options);
            setRelDefaults(m.defaults);
          })
          .catch(handleErr);
      }
      if (purOptions.length === 0) {
        api
          .purposeMaster()
          .then((m) => {
            setPurOptions(m.options);
            setPurDefaults(m.defaults);
          })
          .catch(handleErr);
      }
    }
  }, [screen]);

  // 続柄を世帯マスタへ追加し、選択肢を更新したうえでその値を選ぶ（#1）。
  async function addRelationship(name: string, select: (v: string) => void) {
    try {
      const m = await api.addRelationship(name);
      setRelOptions(m.options);
      select(name);
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // 世帯独自の続柄をマスタから削除（過去レコードの値はそのまま残る）（#1）。
  async function deleteRelationship(name: string) {
    try {
      const m = await api.removeRelationship(name);
      setRelOptions(m.options);
      notify(`「${name}」を続柄から削除しました`);
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // 用途を世帯マスタへ追加/削除（#37、続柄と同じ）。
  async function addPurpose(name: string, select: (v: string) => void) {
    try {
      const m = await api.addPurpose(name);
      setPurOptions(m.options);
      select(name);
    } catch (e) {
      notify(errMsg(e));
    }
  }
  async function deletePurpose(name: string) {
    try {
      const m = await api.removePurpose(name);
      setPurOptions(m.options);
      notify(`「${name}」を用途から削除しました`);
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // ---- 撮影 → 抽出 ----
  async function doCapture() {
    if (!capturedImage) {
      notify("先に写真を撮るか、画像を選んでください。");
      return;
    }
    setExtracting(true);
    try {
      // 撮影画像を送って AI 抽出（モック or Bedrock/Claude を環境変数で切替）。
      const job = await api.capture(capturedImage);
      setDraft({
        ...job.candidates,
        direction: "received",
        field_review: job.field_review || {},
        image: capturedImage,
      });
      go("review");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setExtracting(false);
    }
  }

  function startCapture() {
    setCapturedImage("");
    go("capture");
  }

  // 「あげた」を起点にした手入力（副導線、#39）。撮影なしで空の下書きを開く。
  function startManualGiven() {
    setDraft({
      amount: "",
      party_name: "",
      relationship: "",
      purpose: "",
      occurred_at: "",
      direction: "given",
      field_review: {},
      image: "",
    });
    go("review");
  }

  async function saveRecord() {
    if (!draft) return;
    try {
      const input: RecordInput = {
        amount: Number(draft.amount),
        purpose: draft.purpose,
        party_name: draft.party_name,
        direction: draft.direction,
        occurred_at: draft.occurred_at || "",
        relationship: draft.relationship || "",
      };
      const res = await api.createRecord(input);
      setEvent(res.event);
      notify("記録しました");
      go("home");
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // ---- イベントを開く（相手・用途・金額つき） ----
  async function openEvent(eventId: string) {
    try {
      const r = await api.getEvent(eventId);
      setEvent(r.event);
      setEditDraft(null);
      setDueEditing(false);
      go("event");
    } catch (e) {
      notify(errMsg(e));
    }
  }
  async function openEventForRecord(recordId: string) {
    try {
      const r = await api.eventForRecord(recordId);
      setEvent(r.event);
      setEditDraft(null);
      setDueEditing(false);
      go("event");
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // ---- 家族共有 ----
  async function doJoinHousehold() {
    const code = joinCode.trim().toUpperCase();
    if (!code) {
      notify("招待コードを入力してください。");
      return;
    }
    try {
      const r = await api.joinHousehold(code);
      setHousehold(r.household);
      setJoinCode("");
      notify("ご家族に参加しました");
    } catch (e) {
      notify(errMsg(e));
    }
  }
  async function doRemoveMember(userId: string, label: string) {
    if (!confirm(`${label} さんをこの家族から外しますか？\nこの方には台帳が見えなくなります。`))
      return;
    try {
      const r = await api.removeMember(userId);
      setHousehold(r.household);
      notify("メンバーを外しました");
    } catch (e) {
      notify(errMsg(e));
    }
  }
  async function doLeaveHousehold() {
    if (
      !confirm(
        "この家族から脱退しますか？\n台帳はご家族側に残り、あなたは新しい空の状態になります。",
      )
    )
      return;
    try {
      await api.leaveHousehold();
      notify("脱退しました");
      location.reload(); // 世帯（データの見え方）が変わるため全体を読み直す
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // ---- 記録の削除（詳細・ホーム・台帳から）（#36）----
  async function doDeleteRecord(recordId: string, label: string) {
    if (!confirm(`「${label}」の記録を削除しますか？\nこの操作は取り消せません。`)) return;
    try {
      await api.deleteRecord(recordId);
      notify("削除しました");
      if (screen === "event") go("home");
      else if (screen === "home") await loadHome();
      else if (screen === "ledger") await loadLedger();
    } catch (e) {
      handleErr(e);
    }
  }

  // ---- 記録の修正（AI抽出の誤りを本人が訂正）----
  function startEdit() {
    if (!event) return;
    setEditDraft({
      amount: String(event.amount),
      purpose: event.purpose,
      party_name: event.party_name,
      occurred_at: event.occurred_at || "",
      relationship: event.relationship || "",
    });
  }
  async function saveEdit() {
    if (!editDraft || !event) return;
    try {
      const amount = Number(editDraft.amount);
      if (!amount || amount <= 0) {
        notify("金額は1円以上で入力してください。");
        return;
      }
      if (!editDraft.purpose.trim() || !editDraft.party_name.trim()) {
        notify("用途と相手は必須です。");
        return;
      }
      await api.updateRecord(event.record_id, {
        amount,
        purpose: editDraft.purpose.trim(),
        party_name: editDraft.party_name.trim(),
        occurred_at: editDraft.occurred_at.trim(), // もらった日。期限の自動計算に反映される
        relationship: editDraft.relationship.trim(), // 続柄（#1）
      });
      const r = await api.getEvent(event.id); // 修正後の表示を取り直す（期限も再計算）
      setEvent(r.event);
      setEditDraft(null);
      notify("修正しました");
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // ---- お返し期限の手動上書き / 既定に戻す ----
  async function changeDue(dueAt: string | null) {
    if (!event) return;
    try {
      const r = await api.setEventDue(event.id, dueAt);
      setEvent(r.event);
      notify(dueAt ? "期限を変更しました" : "期限を既定に戻しました");
    } catch (e) {
      notify(errMsg(e));
    }
  }

  // ---- お返し ----
  async function startReturn(ev: EventView) {
    setEvent(ev);
    const r = await api.halfReturn(ev.amount, ev.purpose);
    setRange({ ...r, amount: ev.amount, purpose: ev.purpose });
    go("half");
  }
  async function loadSuggestions() {
    if (!event || !range) return;
    const r = await api.suggestions(event.id, range.recommended, "友人", range.purpose);
    setSuggestions(r.suggestions);
    go("suggest");
  }
  async function chooseSuggestion(s: Suggestion) {
    if (!event) return;
    // お返し品を選んだら、そのまま完了に（礼状ステップは廃止、#40）。
    await api.selectSuggestion(event.id, s);
    await complete();
  }
  async function complete() {
    if (!event) return;
    await api.setStatus(event.id, "done");
    setCelebrate(true); // 水引が結ばれる演出（reduced-motion 尊重）
    setTimeout(() => {
      setCelebrate(false);
      go("home");
    }, 1600);
  }

  const Bar = ({ title, back, logo }: { title: string; back?: Screen; logo?: boolean }) => (
    <div className="appbar">
      {back ? (
        <div className="back" onClick={() => go(back)} role="button" aria-label="戻る">
          <Icon name="arrowLeft" size={22} />
        </div>
      ) : (
        <div style={{ width: 28 }} />
      )}
      <div className="title">
        {logo ? <Logo variant="full" size={20} style={{ verticalAlign: "middle" }} /> : title}
      </div>
      <div style={{ width: 28 }} />
    </div>
  );

  return (
    <div className={`phone${fontLarge ? " font-large" : ""}`}>
      {celebrate && (
        <div className="celebrate" role="status" aria-label="お返しを完了しました">
          <svg width="160" height="90" viewBox="0 0 160 90">
            <path
              className="mizu1"
              d="M20 60 C 55 15, 105 15, 140 60"
              fill="none"
              stroke="#b23a2e"
              stroke-width="4"
              stroke-linecap="round"
            />
            <path
              className="mizu2"
              d="M20 66 C 55 21, 105 21, 140 66"
              fill="none"
              stroke="#a9863f"
              stroke-width="4"
              stroke-linecap="round"
            />
            <circle cx="80" cy="45" r="6" fill="#b23a2e" />
          </svg>
          <div className="celebrate-text">お返し、完了しました</div>
        </div>
      )}
      {screen === "login" && (
        <>
          <div className="brand">
            <Logo variant="full" size={40} />
          </div>
          <div className="brand-en">N O S H I</div>
          <p className="muted" style={{ textAlign: "center" }}>
            贈答を、ちゃんと続けられる。
          </p>

          {!authEnabled() ? (
            <button
              type="button"
              className="btn primary"
              aria-label="noshi をはじめる"
              onClick={() => go("home")}
            >
              noshi をはじめる
            </button>
          ) : (
            <div className="card" style={{ marginTop: 16 }}>
              {/* メール: signin/signup/forgot で表示 */}
              {(authMode === "signin" || authMode === "signup" || authMode === "forgot") && (
                <div className="field" style={{ marginTop: 0 }}>
                  <label htmlFor="auth-email">メールアドレス</label>
                  <input
                    id="auth-email"
                    className="input"
                    type="email"
                    autoComplete="email"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    placeholder="you@example.com"
                  />
                </div>
              )}
              {/* パスワード: signin/signup で表示（reset は下で新パスワードを表示） */}
              {(authMode === "signin" || authMode === "signup") && (
                <div className="field">
                  <label htmlFor="auth-pw">パスワード</label>
                  <input
                    id="auth-pw"
                    className="input"
                    type="password"
                    autoComplete={authMode === "signup" ? "new-password" : "current-password"}
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    placeholder="8文字以上・英小文字と数字"
                  />
                </div>
              )}

              {authMode === "signin" && (
                <>
                  <button
                    type="button"
                    className="btn primary"
                    disabled={authBusy}
                    onClick={doSignIn}
                  >
                    {authBusy ? "ログイン中…" : "ログイン"}
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ marginTop: 8 }}
                    disabled={authBusy}
                    onClick={() => setAuthMode("signup")}
                  >
                    アカウントを作成
                  </button>
                  <button
                    type="button"
                    className="linklike"
                    disabled={authBusy}
                    onClick={() => setAuthMode("forgot")}
                  >
                    パスワードをお忘れの方
                  </button>
                </>
              )}

              {authMode === "forgot" && (
                <>
                  <p className="muted">登録メールに確認コードを送ります。</p>
                  <button
                    type="button"
                    className="btn primary"
                    disabled={authBusy}
                    onClick={doForgot}
                  >
                    {authBusy ? "送信中…" : "確認コードを送る"}
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ marginTop: 8 }}
                    disabled={authBusy}
                    onClick={() => setAuthMode("signin")}
                  >
                    ログインに戻る
                  </button>
                </>
              )}

              {authMode === "reset" && (
                <>
                  <p className="muted">
                    {authEmail} に届いた確認コードと、新しいパスワードを入力してください。
                  </p>
                  <div className="field" style={{ marginTop: 0 }}>
                    <label htmlFor="reset-code">確認コード</label>
                    <input
                      id="reset-code"
                      className="input"
                      inputMode="numeric"
                      value={authCode}
                      onChange={(e) => setAuthCode(e.target.value)}
                      placeholder="メールの6桁コード"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="reset-pw">新しいパスワード</label>
                    <input
                      id="reset-pw"
                      className="input"
                      type="password"
                      autoComplete="new-password"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                      placeholder="8文字以上・英小文字と数字"
                    />
                  </div>
                  <button
                    type="button"
                    className="btn primary"
                    disabled={authBusy}
                    onClick={doReset}
                  >
                    {authBusy ? "再設定中…" : "パスワードを再設定"}
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ marginTop: 8 }}
                    disabled={authBusy}
                    onClick={() => setAuthMode("signin")}
                  >
                    ログインに戻る
                  </button>
                </>
              )}

              {authMode === "signup" && (
                <>
                  <button
                    type="button"
                    className="btn primary"
                    disabled={authBusy}
                    onClick={doSignUp}
                  >
                    {authBusy ? "送信中…" : "登録（確認コードを送る）"}
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ marginTop: 8 }}
                    disabled={authBusy}
                    onClick={() => setAuthMode("signin")}
                  >
                    ログインに戻る
                  </button>
                </>
              )}

              {authMode === "confirm" && (
                <>
                  <p className="muted">{authEmail} に届いた確認コードを入力してください。</p>
                  <div className="field" style={{ marginTop: 0 }}>
                    <label htmlFor="auth-code">確認コード</label>
                    <input
                      id="auth-code"
                      className="input"
                      inputMode="numeric"
                      value={authCode}
                      onChange={(e) => setAuthCode(e.target.value)}
                      placeholder="メールの6桁コード"
                    />
                  </div>
                  <button
                    type="button"
                    className="btn primary"
                    disabled={authBusy}
                    onClick={doConfirm}
                  >
                    {authBusy ? "確認中…" : "確認して はじめる"}
                  </button>
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ marginTop: 8 }}
                    disabled={authBusy}
                    onClick={() => setAuthMode("signin")}
                  >
                    ログインに戻る
                  </button>
                </>
              )}
              <div className="trustnote" style={{ marginTop: 12 }}>
                <span className="ic">
                  <Icon name="lock" size={18} />
                </span>
                <div>メール認証で、ご家族の台帳を安全に守ります。</div>
              </div>
            </div>
          )}
        </>
      )}

      {screen === "home" && home && (
        <>
          <Bar title="noshi" logo />
          {nudge && (
            <div className="nudge">
              <Icon name="gift" size={18} />
              {nudge}
            </div>
          )}
          {home.pending.length === 0 && home.recent.length === 0 ? (
            <div className="onboard">
              <div className="onboard-emoji" aria-hidden="true">
                <Icon name="gift" size={40} strokeWidth={1.6} />
              </div>
              <div className="h" style={{ textAlign: "center" }}>
                まず1枚、撮ってみましょう
              </div>
              <p className="muted" style={{ textAlign: "center" }}>
                頂いた贈答を撮るだけで、お返しまでご案内します。
              </p>
            </div>
          ) : (
            <>
              <div className="h">お返しの予定</div>
              <p className="muted">期限の近い順。タップしてお返しへ。</p>
              {home.pending.length === 0 && (
                <p className="muted" style={{ marginTop: 16 }}>
                  いま必要なお返しはありません。
                </p>
              )}
            </>
          )}
          {home.pending.map((e) => {
            const overdue = e.days_left !== null && e.days_left < 0;
            const soon = e.days_left !== null && e.days_left <= 3;
            return (
              <div className="card tap" key={e.id} onClick={() => openEvent(e.id)}>
                <div className="between">
                  <b>{e.party_name} 様</b>
                  <span
                    className="duebadge"
                    style={{
                      color: overdue
                        ? "var(--color-accent)"
                        : soon
                          ? "var(--color-warning)"
                          : "var(--text-sub)",
                      fontWeight: overdue || soon ? 700 : 400,
                    }}
                  >
                    {daysLeftLabel(e.days_left)}
                  </span>
                </div>
                <div className="between">
                  <div className="muted">
                    {e.purpose} ・ {yen(e.amount)} ・ {statusLabel(e.status)}
                  </div>
                  <button
                    type="button"
                    className="card-del"
                    aria-label={`${e.party_name} の記録を削除`}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      doDeleteRecord(e.record_id, e.party_name);
                    }}
                  >
                    <Icon name="trash" size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </>
      )}

      {screen === "capture" && (
        <>
          <Bar title="撮影" back="home" />
          <p className="muted" style={{ marginTop: 6 }}>
            ご祝儀袋・のし・送り状を撮影、または画像を選んでください。
          </p>

          <label className="dropzone" htmlFor="noshi-camera" aria-label="写真を撮る・画像を選ぶ">
            {capturedImage ? (
              <img className="capture-preview" src={capturedImage} alt="撮影した画像" />
            ) : (
              <>
                <div className="dz-emoji" aria-hidden="true">
                  <Icon name="camera" size={34} strokeWidth={1.8} />
                </div>
                <div className="muted">タップして撮影 / 画像を選ぶ</div>
              </>
            )}
          </label>
          <input
            id="noshi-camera"
            className="visually-hidden"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => onPickImage(e.target.files?.[0] ?? null)}
          />

          {capturedImage && (
            <label className="btn ghost" htmlFor="noshi-camera" style={{ marginTop: 8 }}>
              撮り直す / 別の画像
            </label>
          )}
          <button
            type="button"
            className="btn primary"
            disabled={!capturedImage || extracting}
            onClick={doCapture}
          >
            {extracting ? "読み取り中…" : "この画像で読み取る"}
          </button>
          <TrustNote />
          <div
            style={{
              marginTop: 20,
              paddingTop: 16,
              borderTop: "1px dashed var(--border-default)",
            }}
          >
            <p className="muted">贈った（あげた）ものは、撮影せず手入力で記録できます。</p>
            <button type="button" className="btn ghost" onClick={startManualGiven}>
              <Icon name="gift" size={18} />
              あげた物を手入力で記録
            </button>
          </div>
        </>
      )}

      {screen === "review" &&
        draft &&
        (() => {
          const fields = [
            "amount",
            "party_name",
            "relationship",
            "purpose",
            "occurred_at",
          ] as const;
          const labels: Record<string, string> = {
            amount: "金額",
            party_name: "お相手",
            relationship: "続柄",
            purpose: "用途",
            occurred_at: "日付",
          };
          const fr = draft.field_review || {};
          const reviewCount = fields.filter((k) => fr[k]).length;
          return (
            <>
              <Bar title={draft.image ? "内容を確認" : "あげた物を記録"} back="capture" />
              {draft.image && <img className="review-image" src={draft.image} alt="撮影した画像" />}
              <p className="muted" style={{ marginTop: 6 }}>
                {draft.image
                  ? reviewMessage(reviewCount, fields.length)
                  : "贈った内容を入力して保存してください。"}
              </p>
              <div className="field">
                <label>種類</label>
                <div className="chips">
                  {(
                    [
                      ["received", "もらった"],
                      ["given", "あげた"],
                    ] as const
                  ).map(([d, lbl]) => (
                    <span
                      key={d}
                      className={`chip ${draft.direction === d ? "on" : ""}`}
                      role="button"
                      aria-label={lbl}
                      aria-pressed={draft.direction === d}
                      onClick={() => setDraft({ ...draft, direction: d })}
                    >
                      {lbl}
                    </span>
                  ))}
                </div>
              </div>
              {fields.map((k) => {
                const warn = !!fr[k];
                return (
                  <div className="field" key={k}>
                    <label htmlFor={`rev-${k}`}>
                      {labels[k]}
                      {warn ? (
                        <span className="reviewbadge">要確認</span>
                      ) : (
                        <span className="okbadge">
                          <Icon name="check" size={13} strokeWidth={2.6} />
                          確定
                        </span>
                      )}
                    </label>
                    {k === "relationship" ? (
                      <MasterSelect
                        id={`rev-${k}`}
                        noun="続柄"
                        value={draft.relationship ?? ""}
                        options={relOptions}
                        defaults={relDefaults}
                        onChange={(v) => setDraft({ ...draft, relationship: v })}
                        onAdd={(name) =>
                          addRelationship(name, (v) => setDraft({ ...draft, relationship: v }))
                        }
                        onDelete={deleteRelationship}
                      />
                    ) : k === "purpose" ? (
                      <MasterSelect
                        id={`rev-${k}`}
                        noun="用途"
                        value={draft.purpose ?? ""}
                        options={purOptions}
                        defaults={purDefaults}
                        onChange={(v) => setDraft({ ...draft, purpose: v })}
                        onAdd={(name) =>
                          addPurpose(name, (v) => setDraft({ ...draft, purpose: v }))
                        }
                        onDelete={deletePurpose}
                      />
                    ) : (
                      <input
                        id={`rev-${k}`}
                        className={`input${warn ? " warn" : ""}`}
                        value={draft[k] ?? ""}
                        onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
                      />
                    )}
                  </div>
                );
              })}
              <TrustNote />
              <button type="button" className="btn primary" onClick={saveRecord}>
                確認して保存
              </button>
            </>
          );
        })()}

      {screen === "ledger" && ledger && (
        <>
          <Bar title="贈答の台帳" />
          {ledger.records.length === 0 && <p className="muted">記録がありません</p>}
          {ledger.records.map((r) => (
            <div className="listitem" key={r.id} onClick={() => openEventForRecord(r.id)}>
              <span className={`dirpill dir-${r.direction}`}>
                {r.direction === "received" ? "受領" : "贈与"}
              </span>
              <div style={{ flex: 1 }}>
                <b>{r.party_name}</b>
                <div className="muted">{r.purpose}</div>
              </div>
              <div className="amount">{yen(r.amount)}</div>
              <button
                type="button"
                className="card-del"
                aria-label={`${r.party_name} の記録を削除`}
                onClick={(ev) => {
                  ev.stopPropagation();
                  doDeleteRecord(r.id, r.party_name);
                }}
              >
                <Icon name="trash" size={16} />
              </button>
            </div>
          ))}
        </>
      )}

      {screen === "half" && range && (
        <>
          <Bar title="半返し" back="home" />
          <div className="card">
            <span className="muted">もらった額</span>
            <div className="amount">{yen(range.amount)}</div>
          </div>
          <div className="card">
            <span className="muted">推奨お返し額</span>
            <div className="range">
              {yen(range.low)}〜{yen(range.high)}
            </div>
          </div>
          <div className="card">
            <span className="muted">根拠</span>
            <div>{range.rationale}</div>
          </div>
          <button type="button" className="btn primary" onClick={loadSuggestions}>
            次へ（お返し品）
          </button>
        </>
      )}

      {screen === "suggest" && (
        <>
          <Bar title="お返し品の提案" back="half" />
          <p className="muted" style={{ marginTop: 6 }}>
            お返し品を選ぶと、このお返しは「完了」になります。
          </p>
          {suggestions.map((s, i) => (
            <div className="card" key={i}>
              <b>{s.title}</b>
              <div className="muted">
                {s.summary} ・ {s.price_band} ・ 外部サイト↗
              </div>
              <button
                type="button"
                className="btn primary"
                style={{ minHeight: 40 }}
                onClick={() => chooseSuggestion(s)}
              >
                これにして完了
              </button>
            </div>
          ))}
        </>
      )}

      {screen === "event" &&
        event &&
        (() => {
          const mourning = toneOf(event.purpose) === "mourning";
          return (
            <div className={mourning ? "mourning" : ""}>
              <Bar title={mourning ? "弔事のお返し" : "贈答の詳細"} back="home" />
              {mourning && (
                <div className="mournnote">
                  お悔やみの贈答です。落ち着いてお返しを進めましょう。
                </div>
              )}
              {!editDraft ? (
                <div className="card">
                  <b style={{ fontFamily: "var(--font-display)", fontSize: 17 }}>
                    {event.party_name} 様
                  </b>
                  <div className="muted">
                    {event.purpose} ・ {yen(event.amount)} ・{" "}
                    {event.direction === "received" ? "受領" : "贈与"}
                  </div>
                  <div className="detailrows">
                    <div className="between">
                      <span className="muted">もらった日</span>
                      <span>{event.occurred_at || "—"}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn ghost"
                    style={{ minHeight: 38, marginTop: 8 }}
                    onClick={startEdit}
                  >
                    <Icon name="edit" size={16} />
                    内容を修正
                  </button>
                </div>
              ) : (
                <div className="card">
                  <div className="h" style={{ fontSize: 14 }}>
                    内容を修正
                  </div>
                  <div className="field">
                    <label htmlFor="edit-party">相手のお名前</label>
                    <input
                      id="edit-party"
                      className="input"
                      value={editDraft.party_name}
                      onChange={(e) => setEditDraft({ ...editDraft, party_name: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="edit-purpose">用途</label>
                    <MasterSelect
                      id="edit-purpose"
                      noun="用途"
                      value={editDraft.purpose}
                      options={purOptions}
                      defaults={purDefaults}
                      onChange={(v) => setEditDraft({ ...editDraft, purpose: v })}
                      onAdd={(name) =>
                        addPurpose(name, (v) => setEditDraft((d) => (d ? { ...d, purpose: v } : d)))
                      }
                      onDelete={deletePurpose}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="edit-amount">金額（円）</label>
                    <input
                      id="edit-amount"
                      className="input"
                      type="number"
                      inputMode="numeric"
                      value={editDraft.amount}
                      onChange={(e) => setEditDraft({ ...editDraft, amount: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="edit-occurred">もらった日</label>
                    <input
                      id="edit-occurred"
                      className="input"
                      type="date"
                      value={editDraft.occurred_at}
                      onChange={(e) => setEditDraft({ ...editDraft, occurred_at: e.target.value })}
                    />
                    <span className="muted">変更すると、お返し期限が自動で計算し直されます。</span>
                  </div>
                  <div className="field">
                    <label htmlFor="edit-relationship">続柄</label>
                    <MasterSelect
                      id="edit-relationship"
                      noun="続柄"
                      value={editDraft.relationship}
                      options={relOptions}
                      defaults={relDefaults}
                      onChange={(v) => setEditDraft({ ...editDraft, relationship: v })}
                      onAdd={(name) =>
                        addRelationship(name, (v) =>
                          setEditDraft((d) => (d ? { ...d, relationship: v } : d)),
                        )
                      }
                      onDelete={deleteRelationship}
                    />
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      type="button"
                      className="btn primary"
                      style={{ flex: 1 }}
                      onClick={saveEdit}
                    >
                      保存する
                    </button>
                    <button
                      type="button"
                      className="btn ghost"
                      style={{ flex: 1 }}
                      onClick={() => setEditDraft(null)}
                    >
                      やめる
                    </button>
                  </div>
                </div>
              )}
              <div className="h" style={{ fontSize: 14 }}>
                ステータス
              </div>
              <div className="chips">
                {["received", "considering", "done"].map((st) => (
                  <span
                    key={st}
                    className={`chip ${event.status === st ? "on" : ""}`}
                    onClick={async () => {
                      const r = await api.setStatus(event.id, st);
                      setEvent(r.event);
                      notify("更新しました");
                    }}
                  >
                    {statusLabel(st)}
                  </span>
                ))}
              </div>
              {event.direction === "received" && (
                <>
                  <div className="h" style={{ fontSize: 14 }}>
                    お返し期限
                  </div>
                  <div className="card">
                    {!dueEditing ? (
                      <div className="between">
                        <span>
                          {event.due_at ? event.due_at : "期限なし（お返し不要）"}
                          {event.due_overridden && (
                            <span className="reviewbadge" style={{ marginLeft: 6 }}>
                              変更済
                            </span>
                          )}
                          {event.due_at && (
                            <span className="muted" style={{ marginLeft: 8 }}>
                              {daysLeftLabel(event.days_left)}
                            </span>
                          )}
                        </span>
                        <button
                          type="button"
                          className="btn ghost"
                          style={{ width: "auto", minHeight: 36, marginTop: 0, padding: "0 14px" }}
                          onClick={() => {
                            setDueInput(event.due_at ?? "");
                            setDueEditing(true);
                          }}
                        >
                          変更
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="field" style={{ marginTop: 0 }}>
                          <label htmlFor="due-input">お返し期限</label>
                          <input
                            id="due-input"
                            className="input"
                            type="date"
                            value={dueInput}
                            onChange={(e) => setDueInput(e.target.value)}
                          />
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            type="button"
                            className="btn primary"
                            style={{ flex: 1 }}
                            onClick={async () => {
                              await changeDue(dueInput || null);
                              setDueEditing(false);
                            }}
                          >
                            この日に変更
                          </button>
                          <button
                            type="button"
                            className="btn ghost"
                            style={{ flex: 1 }}
                            onClick={() => setDueEditing(false)}
                          >
                            やめる
                          </button>
                        </div>
                        {event.due_overridden && (
                          <button
                            type="button"
                            className="linklike"
                            onClick={async () => {
                              await changeDue(null);
                              setDueEditing(false);
                            }}
                          >
                            既定（自動計算）に戻す
                          </button>
                        )}
                      </>
                    )}
                  </div>
                  <button
                    type="button"
                    className={mourning ? "btn" : "btn shu"}
                    onClick={() => startReturn(event)}
                  >
                    {mourning ? "お返し（香典返し）を進める" : "お返しの続き（半返し→お返し品）"}
                  </button>
                </>
              )}
              <button
                type="button"
                className="btn ghost danger"
                style={{ marginTop: 20 }}
                onClick={() => doDeleteRecord(event.record_id, event.party_name)}
              >
                <Icon name="trash" size={16} />
                この記録を削除
              </button>
            </div>
          );
        })()}

      {screen === "relations" && (
        <>
          <Bar title="おつきあい" />
          <p className="muted" style={{ marginTop: 6 }}>
            相手別の収支バランス。気になる関係をそっとお知らせします。
          </p>
          {relationships && relationships.length === 0 && (
            <p className="muted" style={{ marginTop: 16 }}>
              まだ記録がありません。贈答を記録すると、ここにおつきあいが表示されます。
            </p>
          )}
          {relationships?.map((r) => {
            const label =
              r.status === "owe" ? "もらい多め" : r.status === "ahead" ? "お贈り多め" : "均衡";
            return (
              <div className="card" key={r.party_name}>
                <div className="between">
                  <b className="val">{r.party_name} 様</b>
                  <span className={`balbadge ${r.status}`}>
                    {r.attention ? "気になる関係" : label}
                  </span>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  もらった {yen(r.received)} ／ あげた {yen(r.given)} ・ 最終 {r.last_at || "—"}
                </div>
                {r.attention && (
                  <div className="muted" style={{ marginTop: 4, color: "var(--color-warning)" }}>
                    しばらくお贈りしていません。折を見て一言いかがでしょう。
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}

      {screen === "mypage" && (
        <>
          <div className="mypage-head">
            <button
              type="button"
              className="hamburger"
              aria-label="メニュー"
              onClick={() => setDrawerOpen(true)}
            >
              <Icon name="menu" size={24} />
            </button>
            <span className="title">
              {MY_SECTIONS.find((s) => s.key === mySection)?.label ?? "マイページ"}
            </span>
          </div>
          {mySection === "household" && household && (
            <>
              <div className="card">
                {(() => {
                  const me = currentUserId();
                  const iAmOwner = household.members.some(
                    (m) => m.user_id === me && m.role === "owner",
                  );
                  return (
                    <>
                      <div className="muted">この台帳を共有しているメンバー</div>
                      <div
                        style={{ display: "flex", flexWrap: "wrap", gap: 6, margin: "6px 0 10px" }}
                      >
                        {household.members.map((m) => {
                          const label = m.email || m.user_id;
                          const isMe = m.user_id === me;
                          return (
                            <span key={m.user_id} className="chip on">
                              {label}
                              {m.role === "owner" ? "（管理者）" : ""}
                              {isMe ? "・あなた" : ""}
                              {iAmOwner && !isMe && (
                                <button
                                  type="button"
                                  className="memberx"
                                  aria-label={`${label} を外す`}
                                  onClick={() => doRemoveMember(m.user_id, label)}
                                >
                                  <Icon name="close" size={12} strokeWidth={2.4} />
                                </button>
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
                  <button
                    type="button"
                    className="btn"
                    style={{ height: 38, width: "auto", padding: "0 12px" }}
                    onClick={async () =>
                      notify(
                        (await copyText(household.invite_code))
                          ? "コードをコピーしました"
                          : "コピーできませんでした",
                      )
                    }
                  >
                    コピー
                  </button>
                </div>
                <div className="muted" style={{ marginTop: 10 }}>
                  家族から受け取ったコードで参加する
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                  <input
                    className="input"
                    style={{ flex: 1 }}
                    placeholder="招待コード"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value)}
                    aria-label="招待コード"
                  />
                  <button
                    type="button"
                    className="btn primary"
                    style={{ width: "auto", padding: "0 16px" }}
                    onClick={doJoinHousehold}
                  >
                    参加
                  </button>
                </div>
                <div className="trustnote" style={{ marginTop: 10 }}>
                  <span className="ic">
                    <Icon name="lock" size={18} />
                  </span>
                  <div>
                    台帳は<b>このご家族だけ</b>が見られます。
                  </div>
                </div>
                {household.members.length > 1 && (
                  <button
                    type="button"
                    className="btn ghost danger"
                    style={{ marginTop: 10 }}
                    onClick={doLeaveHousehold}
                  >
                    この家族から脱退する
                  </button>
                )}
              </div>
            </>
          )}
          {mySection === "annual" && annual && (
            <>
              <div className="h" style={{ fontSize: 15 }}>
                {annual.year}年の振り返り
              </div>
              <div className="card">
                {annual.received_count === 0 && annual.given_count === 0 ? (
                  <div className="muted">今年の記録はまだありません。撮影して残しましょう。</div>
                ) : (
                  <>
                    <div style={{ display: "flex", gap: 12 }}>
                      <div style={{ flex: 1 }}>
                        <div className="muted">いただいた</div>
                        <div className="amount" style={{ fontSize: 20 }}>
                          {yen(annual.received_total)}
                        </div>
                        <div className="muted">{annual.received_count}件</div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className="muted">贈った</div>
                        <div className="amount" style={{ fontSize: 20 }}>
                          {yen(annual.given_total)}
                        </div>
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
          {mySection === "gifttax" && giftTax && (
            <div className="card">
              <div className="muted">今年もらった（対象）合計</div>
              <div className="amount" style={{ fontSize: 20 }}>
                {yen(giftTax.total)}
              </div>
              <div style={{ marginTop: 8 }}>
                {giftTax.over ? (
                  <span style={{ color: "var(--color-accent)", fontWeight: 700 }}>
                    110万円の枠を超えています。確認しましょう。
                  </span>
                ) : (
                  <span className="muted">
                    110万円まで <b>あと {yen(giftTax.remaining)}</b>
                  </span>
                )}
              </div>
              <div className="disclaimer">
                ※
                香典・お中元・お歳暮などは除外した概算です。これは税アドバイスではなく気づきのための目安です。正確な要否は専門家にご確認ください。
              </div>
            </div>
          )}
          {mySection === "otoshidama" && (
            <div className="card">
              <div className="field" style={{ marginTop: 0 }}>
                <label htmlFor="otoshi-age">お子さんの年齢</label>
                <input
                  id="otoshi-age"
                  className="input"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={25}
                  placeholder="例）8"
                  value={otoshiAge}
                  aria-label="お子さんの年齢"
                  onChange={(e) => setOtoshiAge(e.target.value)}
                />
              </div>
              {otoshiAge !== "" &&
                !Number.isNaN(Number(otoshiAge)) &&
                (() => {
                  const r = otoshidamaRange(Number(otoshiAge));
                  return (
                    <div style={{ marginTop: 12 }}>
                      <div className="muted">{r.bracket}</div>
                      <div className="range" style={{ fontSize: 22 }}>
                        {r.low === r.high ? yen(r.low) : `${yen(r.low)}〜${yen(r.high)}`}
                      </div>
                      <div className="muted" style={{ marginTop: 4 }}>
                        {r.note}
                      </div>
                    </div>
                  );
                })()}
              <div className="disclaimer">※ 家庭・地域で異なる一般的な目安です。</div>
            </div>
          )}

          {mySection === "display" && (
            <div className="card">
              <div className="between">
                <span>文字を大きくする</span>
                <button
                  type="button"
                  className={`toggle${fontLarge ? " on" : ""}`}
                  role="switch"
                  aria-checked={fontLarge}
                  aria-label="文字を大きくする"
                  onClick={toggleFont}
                >
                  <span className="knob" />
                </button>
              </div>
            </div>
          )}

          {mySection === "privacy" && (
            <div className="card">
              <TrustNote />
              <div className="muted" style={{ marginTop: 8 }}>
                贈り先の情報も含め、ご家族のデータはいつでも書き出し・削除できます。
              </div>
            </div>
          )}

          {mySection === "account" &&
            (authEnabled() ? (
              <div className="card">
                <div className="muted">ログイン中</div>
                <div style={{ fontFamily: "var(--font-display)", margin: "2px 0 10px" }}>
                  {currentEmail() || "—"}
                </div>
                <button type="button" className="btn ghost danger" onClick={doSignOut}>
                  ログアウト
                </button>
              </div>
            ) : (
              <div className="card" style={{ borderStyle: "dashed" }}>
                <div className="muted">開発用: ログイン中のユーザー（本番は Cognito ログイン）</div>
                <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                  <input
                    className="input"
                    style={{ flex: 1 }}
                    defaultValue={currentUserId()}
                    aria-label="ユーザー識別子"
                    onChange={(e) => (devUserRef.current = e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn"
                    style={{ width: "auto", padding: "0 14px" }}
                    onClick={() => {
                      setCurrentUserId(devUserRef.current ?? currentUserId());
                      location.reload();
                    }}
                  >
                    切替
                  </button>
                </div>
                <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                  別の人に切替→相手の招待コードで「参加」すると、同じ台帳が共有されます。
                </div>
              </div>
            ))}

          <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="マイページ">
            {MY_SECTIONS.map((s) => (
              <button
                key={s.key}
                type="button"
                className={`drawer-item${mySection === s.key ? " on" : ""}`}
                onClick={() => {
                  setMySection(s.key);
                  setDrawerOpen(false);
                }}
              >
                <span className="ic">
                  <Icon name={s.icon} size={20} />
                </span>
                {s.label}
              </button>
            ))}
          </Drawer>
        </>
      )}

      {screen !== "login" && (
        <div className="tabbar">
          <button
            type="button"
            className={screen === "home" ? "on" : ""}
            aria-label="ホーム"
            onClick={() => go("home")}
          >
            <Icon name="home" size={23} strokeWidth={screen === "home" ? 2.4 : 2} />
            ホーム
          </button>
          <button
            type="button"
            className={screen === "ledger" ? "on" : ""}
            aria-label="台帳"
            onClick={() => go("ledger")}
          >
            <Icon name="ledger" size={23} strokeWidth={screen === "ledger" ? 2.4 : 2} />
            台帳
          </button>
          <button
            type="button"
            className="fab"
            aria-label="贈答を撮影して記録"
            onClick={startCapture}
          >
            <Icon name="plus" size={26} strokeWidth={2.4} color="#fff" />
          </button>
          <button
            type="button"
            className={screen === "relations" ? "on" : ""}
            aria-label="おつきあい"
            onClick={() => go("relations")}
          >
            <Icon name="handshake" size={23} strokeWidth={screen === "relations" ? 2.4 : 2} />
            おつきあい
          </button>
          <button
            type="button"
            className={screen === "mypage" ? "on" : ""}
            aria-label="マイページ"
            onClick={() => go("mypage")}
          >
            <Icon name="user" size={23} strokeWidth={screen === "mypage" ? 2.4 : 2} />
            マイページ
          </button>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
