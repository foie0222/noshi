import { useEffect, useRef, useState } from "react";
import {
  api,
  currentUserId,
  type RecordInput,
  setCurrentUserId,
  UnauthorizedError,
  uploadToS3,
} from "./api";
import { Icon } from "./components/Icon";
import { LegalView } from "./components/LegalView";
import { Logo } from "./components/Logo";
import { MasterSelect } from "./components/MasterSelect";
import { PartySelect } from "./components/PartySelect";
import { PasswordInput } from "./components/PasswordInput";
import { Select } from "./components/Select";
import { LEGAL_DOCS, type LegalDocKey, legalDocFromPath } from "./legal";
import { copyText } from "./lib/clipboard";
import {
  authEnabled,
  confirmForgotPassword,
  confirmSignUp,
  currentEmail,
  forgotPassword,
  handleAuthCallback,
  isLoggedIn,
  pickInitialScreen,
  registerNativeAuthCallback,
  signIn,
  signOut,
  signUp,
  socialEnabled,
  socialSignIn,
} from "./lib/cognito";
import { openExternalUrl } from "./lib/external";
import { daysLeftLabel, statusLabel, withHonor, yen } from "./lib/format";
import { isSharing, memberDisplay } from "./lib/household";
import { downscaleImage, fileToDataUrl, validateImageFile } from "./lib/image";
import { filterSortRecords, LEDGER_DEFAULT, type LedgerSort, type LedgerView } from "./lib/ledger";
import { isValidChildAge, otoshidamaRange } from "./lib/otoshidama";
import { reviewMessage } from "./lib/review";
import { seasonNudge, seasonOf } from "./lib/season";
import { priceLine } from "./lib/suggestion";
import { toneOf } from "./lib/tone";
import { hasErrors, recordErrors } from "./lib/validate";
import {
  type AnnualSummary,
  type Direction,
  type Draft,
  type EditDraft,
  type EventView,
  errMsg,
  type GiftTax,
  type HomeResponse,
  type Household,
  type LedgerResponse,
  type Party,
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
  | "mypage"
  | "legal";

// 品物欄の定番サジェスト（自由入力可。datalist で候補表示）。
const ITEM_SUGGESTIONS = [
  "現金",
  "商品券",
  "ギフトカード",
  "カタログギフト",
  "お酒",
  "お菓子",
  "花",
];

// 台帳の並べ替え選択肢（デザインシステム準拠の自前 Select で表示）。
const LEDGER_SORT_OPTIONS: { value: LedgerSort; label: string }[] = [
  { value: "date_desc", label: "新しい順" },
  { value: "date_asc", label: "古い順" },
  { value: "amount_desc", label: "金額が高い順" },
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
  // 直URL（/privacy 等）は未ログインでも法的文書を直接開く（#155）。
  const initialLegal = legalDocFromPath(window.location.pathname);
  // リロード時はトークンの有無からホーム/ログインを復元する（毎回ログインに戻る問題の対策）。
  const [screen, setScreen] = useState<Screen>(() =>
    initialLegal ? "legal" : pickInitialScreen(authEnabled(), isLoggedIn()),
  );
  const [legalDoc, setLegalDoc] = useState<LegalDocKey | null>(initialLegal);
  const [legalBack, setLegalBack] = useState<Screen>(() =>
    pickInitialScreen(authEnabled(), isLoggedIn()),
  ); // 法的文書からの戻り先（ログイン前は login）
  const [agreedTerms, setAgreedTerms] = useState<boolean>(false); // 規約・ポリシーへの同意（#152）
  const [toast, setToast] = useState<string>("");
  const [home, setHome] = useState<HomeResponse | null>(null);
  const [ledger, setLedger] = useState<LedgerResponse | null>(null);
  const [giftTax, setGiftTax] = useState<GiftTax | null>(null);
  const [annual, setAnnual] = useState<AnnualSummary | null>(null);
  const [household, setHousehold] = useState<Household | null>(null);
  const [joinCode, setJoinCode] = useState<string>("");
  const [showJoin, setShowJoin] = useState<boolean>(false); // 共有中は「参加」を控えめに折りたたむ(#80)
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
  const [notifyEmail, setNotifyEmail] = useState<boolean>(true); // お返し期限のメール通知(#178)
  const [celebrate, setCelebrate] = useState<boolean>(false); // 水引の完了演出
  const [capturedImage, setCapturedImage] = useState<string>(""); // 撮影/選択した画像(dataURL)
  const [captureDirection, setCaptureDirection] = useState<Direction>("received"); // 撮影時の種類（もらった/あげた）
  const [extracting, setExtracting] = useState<boolean>(false);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null); // 記録の修正中(AI抽出の訂正)
  const [dueEditing, setDueEditing] = useState<boolean>(false); // お返し期限の編集中
  const [dueInput, setDueInput] = useState<string>(""); // 期限編集の入力値(YYYY-MM-DD)
  const [relOptions, setRelOptions] = useState<string[]>([]); // 続柄マスタの選択肢(#1)
  const [relDefaults, setRelDefaults] = useState<string[]>([]); // 既定（削除不可の判定用）
  const [purOptions, setPurOptions] = useState<string[]>([]); // 用途マスタの選択肢(#37)
  const [purDefaults, setPurDefaults] = useState<string[]>([]); // 既定（削除不可の判定用）
  const [parties, setParties] = useState<Party[]>([]); // 相手マスタ(#47)
  const [reviewTried, setReviewTried] = useState<boolean>(false); // 保存を試みたか(#50: 検証表示)
  const [editTried, setEditTried] = useState<boolean>(false);
  const [ledgerView, setLedgerView] = useState<LedgerView>(LEDGER_DEFAULT); // 台帳の検索/絞込/並替(#51)
  const [ledgerBack, setLedgerBack] = useState<Screen | null>(null); // おつきあいから台帳へ来たときの戻り先(#180)
  const [uploading, setUploading] = useState<boolean>(false); // 画像アップロード中(#54)

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
  // 画面遷移をブラウザ履歴に積み、戻る/進むで一つ前の「画面」に戻れるようにする（#168）。
  // 履歴には screen 名だけを積み、URL は変えない（詳細などのコンテキストはメモリ上の
  // state が持つ。URL 直リンクは法的文書のみ＝#155 の仕様を維持）。
  const go = (s: Screen) => {
    if (s !== screen) window.history.pushState({ screen: s }, "", window.location.pathname);
    setScreen(s);
  };
  function openLegal(k: LegalDocKey) {
    setLegalDoc(k);
    setLegalBack(screen); // ログイン画面（サインアップの同意リンク）からも開けるように戻り先を記録
    go("legal");
  }
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
  async function doDeleteAccount() {
    if (
      !confirm(
        "アカウントを削除しますか？\nあなたの記録・画像がすべて消え、この操作は取り消せません。\n（家族で共有中の台帳は、残る家族に引き継がれます）",
      )
    )
      return;
    try {
      await api.deleteAccount();
      signOut();
      go("login");
      notify("アカウントを削除しました");
    } catch (e) {
      handleErr(e);
    }
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

  // お返し期限のメール通知 オン/オフ（#178）。楽観更新し、失敗時は元に戻す。
  async function toggleNotify() {
    const next = !notifyEmail;
    setNotifyEmail(next);
    try {
      await api.setNotifications(next);
      notify(next ? "お返し時期にメールでお知らせします" : "メール通知をオフにしました");
    } catch (e) {
      setNotifyEmail(!next);
      handleErr(e);
    }
  }

  async function loadHome() {
    setHome(await api.home());
  }
  async function loadLedger() {
    setLedger(await api.ledger());
  }

  // ソーシャルログインのコールバック処理（URL に ?code= / ?error= があるときだけ動く）
  // biome-ignore lint/correctness/useExhaustiveDependencies: 起動時1回だけ実行する意図
  useEffect(() => {
    if (!socialEnabled()) return;
    const onResult = (r: "ok" | "retry" | "error" | "none") => {
      if (r === "ok") {
        go("home");
      } else if (r === "retry") {
        notify("アカウントを連携しました。続けてログインします…");
      } else if (r === "error") {
        setScreen("login");
        notify("ログインに失敗しました。もう一度お試しください。");
      }
    };
    // Web: 起動時に URL の code/error を処理。iOS ネイティブ: カスタムスキーム復帰を購読（#204）。
    void handleAuthCallback().then(onResult);
    const unsubscribe = registerNativeAuthCallback(onResult);
    return unsubscribe;
  }, []);

  // 起動時: ログイン必須環境で未ログインなら login 画面に固定。
  // biome-ignore lint/correctness/useExhaustiveDependencies: 画面遷移時のみ判定する意図
  useEffect(() => {
    // 法的文書（規約・ポリシー）は未ログインでも閲覧可（#155）。
    if (authEnabled() && !isLoggedIn() && screen !== "login" && screen !== "legal") go("login");
  }, [screen]);

  // ブラウザの戻る/進むで画面を復元する（#168）。go() が積んだ {screen} を読む。
  // state が無い履歴（起動エントリや OAuth コールバック後）は初期画面の判定にフォールバック。
  // biome-ignore lint/correctness/useExhaustiveDependencies: リスナー登録は起動時1回だけ
  useEffect(() => {
    // 起動時の履歴エントリにも screen を持たせ、戻ってきたときに復元できるようにする。
    window.history.replaceState({ screen }, "", window.location.pathname);
    const onPop = (e: PopStateEvent) => {
      const s = (e.state as { screen?: Screen } | null)?.screen;
      setScreen(s ?? pickInitialScreen(authEnabled(), isLoggedIn()));
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // 法的文書を開いている間は URL を同期し、閉じたら / に戻す（直リンク共有用、#155）。
  // replaceState で {screen} を保持し、戻る/進むの復元（#168）を壊さない。
  useEffect(() => {
    const path = screen === "legal" && legalDoc ? `/${legalDoc}` : "/";
    if (window.location.pathname !== path) window.history.replaceState({ screen }, "", path);
  }, [screen, legalDoc]);

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
      // メール通知の設定（ログイン環境のみ。メールアドレスが前提、#178）
      if (authEnabled()) {
        api
          .notifications()
          .then((r) => setNotifyEmail(r.email))
          .catch(handleErr);
      }
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
      // 相手マスタ（#47）は都度最新化（追加が反映されるように）。
      api
        .parties()
        .then((r) => setParties(r.parties))
        .catch(handleErr);
    }
  }, [screen]);

  // 相手を世帯マスタへ追加し、一覧を更新したうえでその相手を選ぶ（#47）。
  async function addParty(name: string, relationship: string, select: (id: string) => void) {
    try {
      const { party } = await api.addParty(name, relationship);
      const r = await api.parties();
      setParties(r.parties);
      select(party.id);
    } catch (e) {
      notify(errMsg(e));
    }
  }

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
        direction: captureDirection, // 撮影画面で選んだ種類を引き継ぐ（確認画面で変更可）
        field_review: job.field_review || {},
        image: capturedImage,
        party_id: "", // 確認画面で相手を選ぶ/作る（#47）
        // item は job.candidates に含まれる（読めたら自動入力、ダメなら空で手入力）
      });
      setReviewTried(false);
      go("review");
    } catch (e) {
      notify(errMsg(e));
    } finally {
      setExtracting(false);
    }
  }

  function startCapture() {
    setCapturedImage("");
    setCaptureDirection("received");
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
      party_id: "",
      item: "",
    });
    setReviewTried(false);
    go("review");
  }

  // data URL の画像を縮小し、署名付きURLでS3へ上げてキーを返す（#35/#54）。
  // 進捗は uploading で可視化。失敗は failed で呼び出し側に伝える（記録自体は続行可）。
  async function uploadImage(dataUrl: string): Promise<{ key: string; failed: boolean }> {
    if (!dataUrl) return { key: "", failed: false };
    setUploading(true);
    try {
      const blob = await downscaleImage(dataUrl);
      const { url, fields, key } = await api.imageUploadUrl("image/jpeg");
      await uploadToS3(url, fields, blob);
      return { key, failed: false };
    } catch {
      return { key: "", failed: true };
    } finally {
      setUploading(false);
    }
  }

  async function saveRecord() {
    if (!draft) return;
    const errs = recordErrors({
      amount: String(draft.amount ?? ""),
      purpose: draft.purpose ?? "",
      partyId: draft.party_id,
    });
    if (hasErrors(errs)) {
      setReviewTried(true); // 各項目の下にインライン表示（#50）
      return;
    }
    try {
      const { key: image_key, failed: imgFailed } = await uploadImage(draft.image);
      const input: RecordInput = {
        amount: Number(draft.amount),
        purpose: draft.purpose,
        party_id: draft.party_id,
        direction: draft.direction,
        occurred_at: draft.occurred_at || "",
        item: draft.item?.trim() || "",
        image_key,
      };
      const res = await api.createRecord(input);
      setEvent(res.event);
      notify(imgFailed ? "記録しました（写真は保存できませんでした）" : "記録しました");
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

  // ---- ホームから「お返し済み」をワンタップで完了に（#179）----
  // 詳細を開かず status=done に。カードは予定一覧からそっと外れる。急かさず労う一言を返す。
  async function doMarkDone(eventId: string) {
    try {
      await api.setStatus(eventId, "done");
      notify("お返し、おつかれさまでした");
      await loadHome();
    } catch (e) {
      handleErr(e);
    }
  }

  // ---- おつきあい → 相手の贈答履歴へドリルダウン（#180）----
  // 新しい画面は作らず、既存の台帳ビューをその相手で絞り込んだ状態で開く。
  function openPartyHistory(name: string) {
    setLedgerView({ ...LEDGER_DEFAULT, query: name });
    setLedgerBack("relations"); // 台帳のヘッダに戻る導線を出す
    go("ledger");
  }

  // ---- 記録の修正（AI抽出の誤りを本人が訂正）----
  function startEdit() {
    if (!event) return;
    setEditTried(false);
    setEditDraft({
      amount: String(event.amount),
      purpose: event.purpose,
      occurred_at: event.occurred_at || "",
      party_id: event.party_id || "",
      item: event.item || "",
    });
  }
  async function saveEdit() {
    if (!editDraft || !event) return;
    const errs = recordErrors({
      amount: editDraft.amount,
      purpose: editDraft.purpose,
      partyId: editDraft.party_id,
    });
    if (hasErrors(errs)) {
      setEditTried(true); // インライン表示（#50）
      return;
    }
    try {
      const amount = Number(editDraft.amount);
      await api.updateRecord(event.record_id, {
        amount,
        purpose: editDraft.purpose.trim(),
        party_id: editDraft.party_id, // 相手の付け替え（#47）
        occurred_at: editDraft.occurred_at.trim(), // もらった日。期限の自動計算に反映される
        item: editDraft.item.trim(), // 品物（例: 現金/メガネ）
      });
      // 記録ベースで取り直す（given=イベントなしでも動く、#48）。期限も再計算。
      const r = await api.eventForRecord(event.record_id);
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

  // ---- 詳細の写真を追加/差し替え/削除（#35）。file=null で削除。----
  async function changeImage(file: File | null) {
    if (!event) return;
    let image_key = "";
    if (file) {
      const err = validateImageFile(file);
      if (err) {
        notify(err);
        return;
      }
      const up = await uploadImage(await fileToDataUrl(file));
      if (up.failed) {
        notify("写真を保存できませんでした。通信環境をご確認ください。");
        return;
      }
      image_key = up.key;
    }
    try {
      await api.updateRecord(event.record_id, {
        amount: event.amount,
        purpose: event.purpose,
        image_key, // 相手は変更しない（party_id 未指定）
      });
      const r = await api.eventForRecord(event.record_id);
      setEvent(r.event);
      notify(file ? "写真を変更しました" : "写真を削除しました");
    } catch (e) {
      handleErr(e);
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
    const r = await api.suggestions(
      event.id,
      range.recommended,
      event.relationship || "",
      range.purpose,
    );
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
        <button type="button" className="back" onClick={() => go(back)} aria-label="戻る">
          <Icon name="arrowLeft" size={22} />
        </button>
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
          <svg width="160" height="90" viewBox="0 0 160 90" role="img" aria-label="水引">
            <title>水引</title>
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
          <div className="login-hero">
            <div className="brand">
              <Logo variant="full" size={40} />
            </div>
            <div className="brand-en">N O S H I</div>
            {/* コンセプト（OGP/meta と一致）を主役に。3層を一貫させる（#login-redesign 設計） */}
            <p className="login-concept">
              大切な人との縁を、
              <br />
              長く美しく。
            </p>
            <p className="login-desc">贈りものの記録と、お返し選び</p>
          </div>

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
            <div className="card" style={{ marginTop: 24 }}>
              {/* 主導線: Google を最上部に置く（federation は初回=サインアップ／
                  以降=ログインでモード非依存）。メール導線は「または」の下に続ける。 */}
              {socialEnabled() && (authMode === "signin" || authMode === "signup") && (
                <>
                  <button
                    type="button"
                    className="btn social-google"
                    onClick={() => void socialSignIn("Google")}
                  >
                    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                      <path
                        fill="#4285F4"
                        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
                      />
                      <path
                        fill="#34A853"
                        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"
                      />
                      <path
                        fill="#EA4335"
                        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"
                      />
                    </svg>
                    Google で続ける
                  </button>
                  {/* LINE はメール取得権限の審査中。死んだボタンも予告も見せず、一旦
                      非表示にする（#login-redesign / #177）。承認後は socialSignIn("LINE")
                      のボタンをここに復活させる。 */}
                  <div className="login-or">または</div>
                </>
              )}
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
                  <PasswordInput
                    id="auth-pw"
                    autoComplete={authMode === "signup" ? "new-password" : "current-password"}
                    value={authPassword}
                    onChange={setAuthPassword}
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
                    <PasswordInput
                      id="reset-pw"
                      autoComplete="new-password"
                      value={authPassword}
                      onChange={setAuthPassword}
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
                  <div className="agree-row">
                    <input
                      id="agree-terms"
                      type="checkbox"
                      aria-label="利用規約とプライバシーポリシーに同意する"
                      checked={agreedTerms}
                      onChange={(e) => setAgreedTerms(e.target.checked)}
                    />
                    <span className="agree-text">
                      <button
                        type="button"
                        className="text-link"
                        onClick={() => openLegal("terms")}
                      >
                        利用規約
                      </button>
                      ・
                      <button
                        type="button"
                        className="text-link"
                        onClick={() => openLegal("privacy")}
                      >
                        プライバシーポリシー
                      </button>
                      に同意します
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn primary"
                    disabled={authBusy || !agreedTerms}
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
                {/* 認証方式ではなく守られる価値を語る（#164）。17文字以内に抑えると
                    最小幅端末（375px・13px）でも折り返さず1行に収まる。 */}
                <div>見られるのは、あなたとご家族だけ。</div>
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
              // biome-ignore lint/a11y/useSemanticElements: 削除ボタンを内包する開閉カードのため button にできない。role+キーボードで代替。
              <div
                className="card tap"
                key={e.id}
                role="button"
                tabIndex={0}
                onClick={() => openEvent(e.id)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    openEvent(e.id);
                  }
                }}
              >
                <div className="between">
                  <b>{withHonor(e.party_name)}</b>
                  <span
                    className="duebadge"
                    style={{
                      // 朱(accent)は CTA 専用に。期限まわりは責めない山吹(warning)で穏やかに（#181）。
                      color: overdue || soon ? "var(--color-warning)" : "var(--text-sub)",
                      fontWeight: overdue ? 700 : soon ? 600 : 400,
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
                {/* お返し済みワンタップ（#179）。削除と離し、静かなチェック1つに留める。 */}
                <button
                  type="button"
                  className="card-done"
                  aria-label={`${e.party_name} へのお返しを済みにする`}
                  onClick={(ev) => {
                    ev.stopPropagation();
                    doMarkDone(e.id);
                  }}
                >
                  <Icon name="check" size={16} strokeWidth={2.4} />
                  お返し済みにする
                </button>
              </div>
            );
          })}
        </>
      )}

      {screen === "capture" && (
        <>
          <Bar title="撮影" back="home" />
          <p className="muted" style={{ marginTop: 6 }}>
            ご祝儀袋・のし・送り状や、贈った品物を撮影、または画像を選んでください。
          </p>

          <fieldset className="field fieldset-reset">
            <legend className="field-label">種類</legend>
            <div className="chips">
              {(
                [
                  ["received", "もらった"],
                  ["given", "あげた"],
                ] as const
              ).map(([d, lbl]) => (
                <button
                  type="button"
                  key={d}
                  className={`chip ${captureDirection === d ? "on" : ""}`}
                  aria-label={lbl}
                  aria-pressed={captureDirection === d}
                  onClick={() => setCaptureDirection(d)}
                >
                  {lbl}
                </button>
              ))}
            </div>
          </fieldset>

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
          {/* capture 属性は付けない: 付けるとスマホでカメラ直起動になり、
              ギャラリー/ファイルからの選択ができなくなる。無しなら OS の
              選択シート（カメラ/ライブラリ/ファイル）が出て撮影も可能。 */}
          <input
            id="noshi-camera"
            className="visually-hidden"
            type="file"
            accept="image/*"
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
            <p className="muted">写真がないときは、手入力でも記録できます。</p>
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
          const fields = ["amount", "purpose", "occurred_at"] as const;
          const labels: Record<string, string> = {
            amount: "金額",
            purpose: "用途",
            occurred_at: "日付",
          };
          const fr = draft.field_review || {};
          const reviewCount = fields.filter((k) => fr[k]).length;
          const errs = reviewTried
            ? recordErrors({
                amount: String(draft.amount ?? ""),
                purpose: draft.purpose ?? "",
                partyId: draft.party_id,
              })
            : {};
          return (
            <>
              <Bar title={draft.image ? "内容を確認" : "あげた物を記録"} back="capture" />
              {draft.image && <img className="review-image" src={draft.image} alt="撮影した画像" />}
              <p className="muted" style={{ marginTop: 6 }}>
                {draft.image
                  ? reviewMessage(reviewCount, fields.length)
                  : "贈った内容を入力して保存してください。"}
              </p>
              <fieldset className="field fieldset-reset">
                <legend className="field-label">種類</legend>
                <div className="chips">
                  {(
                    [
                      ["received", "もらった"],
                      ["given", "あげた"],
                    ] as const
                  ).map(([d, lbl]) => (
                    <button
                      type="button"
                      key={d}
                      className={`chip ${draft.direction === d ? "on" : ""}`}
                      aria-label={lbl}
                      aria-pressed={draft.direction === d}
                      onClick={() => setDraft({ ...draft, direction: d })}
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              </fieldset>
              <div className="field">
                <label htmlFor="rev-party">お相手</label>
                <PartySelect
                  id="rev-party"
                  value={draft.party_id}
                  parties={parties}
                  suggestedName={draft.party_name ?? ""}
                  onChange={(pid) => setDraft({ ...draft, party_id: pid })}
                  onAdd={(name, relationship) =>
                    addParty(name, relationship, (pid) => setDraft({ ...draft, party_id: pid }))
                  }
                  relOptions={relOptions}
                  relDefaults={relDefaults}
                  onAddRelationship={addRelationship}
                  onDeleteRelationship={deleteRelationship}
                />
                {errs.party && <span className="field-error">{errs.party}</span>}
              </div>
              {fields.map((k) => {
                const warn = !!fr[k];
                const err =
                  k === "amount" ? errs.amount : k === "purpose" ? errs.purpose : undefined;
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
                    {k === "purpose" ? (
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
                        className={`input${warn || err ? " warn" : ""}`}
                        type={k === "occurred_at" ? "date" : k === "amount" ? "number" : "text"}
                        inputMode={k === "amount" ? "numeric" : undefined}
                        value={draft[k] ?? ""}
                        onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
                      />
                    )}
                    {err && <span className="field-error">{err}</span>}
                  </div>
                );
              })}
              <div className="field">
                <label htmlFor="rev-item">品物（任意）</label>
                <input
                  id="rev-item"
                  className="input"
                  list="item-suggestions"
                  placeholder="現金・メガネ など"
                  value={draft.item}
                  onChange={(e) => setDraft({ ...draft, item: e.target.value })}
                />
              </div>
              <datalist id="item-suggestions">
                {ITEM_SUGGESTIONS.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
              <TrustNote />
              <button
                type="button"
                className="btn primary"
                disabled={uploading}
                onClick={saveRecord}
              >
                {uploading ? "写真を保存中…" : "確認して保存"}
              </button>
            </>
          );
        })()}

      {screen === "ledger" &&
        ledger &&
        (() => {
          const shown = filterSortRecords(ledger.records, ledgerView);
          return (
            <>
              {/* おつきあいからのドリルダウン時のみ、戻る導線を出す（#180） */}
              <Bar title="贈答の台帳" back={ledgerBack ?? undefined} />
              <div className="ledger-controls">
                <div className="select-wrap" style={{ position: "relative" }}>
                  <input
                    className="input"
                    type="search"
                    placeholder="相手名・用途で検索"
                    aria-label="台帳を検索"
                    value={ledgerView.query}
                    onChange={(e) => setLedgerView({ ...ledgerView, query: e.target.value })}
                  />
                </div>
                <div className="ledger-controls-row">
                  <div className="chips">
                    {(
                      [
                        ["all", "すべて"],
                        ["received", "もらった"],
                        ["given", "あげた"],
                      ] as const
                    ).map(([d, lbl]) => (
                      <button
                        type="button"
                        key={d}
                        className={`chip ${ledgerView.direction === d ? "on" : ""}`}
                        aria-pressed={ledgerView.direction === d}
                        onClick={() => setLedgerView({ ...ledgerView, direction: d })}
                      >
                        {lbl}
                      </button>
                    ))}
                  </div>
                  <Select
                    compact
                    ariaLabel="並べ替え"
                    value={ledgerView.sort}
                    options={LEDGER_SORT_OPTIONS}
                    onChange={(v) => setLedgerView({ ...ledgerView, sort: v as LedgerSort })}
                  />
                </div>
              </div>
              {shown.length === 0 && (
                <p className="muted">
                  {ledger.records.length === 0 ? "記録がありません" : "該当する記録がありません"}
                </p>
              )}
              {shown.map((r) => (
                /* biome-ignore lint/a11y/useSemanticElements: 削除ボタンを内包する行のため button にできない。role+キーボードで代替。 */
                <div
                  className="listitem"
                  key={r.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => openEventForRecord(r.id)}
                  onKeyDown={(ev) => {
                    if (ev.key === "Enter" || ev.key === " ") {
                      ev.preventDefault();
                      openEventForRecord(r.id);
                    }
                  }}
                >
                  <span className={`dirpill dir-${r.direction}`}>
                    {r.direction === "received" ? "もらった" : "あげた"}
                  </span>
                  <div style={{ flex: 1 }}>
                    <b>{r.party_name}</b>
                    <div className="muted">
                      {r.purpose}
                      {r.item && ` ・ ${r.item}`}
                    </div>
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
          );
        })()}

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
            気に入った品は「この品に決める」で、このお返しを完了にできます。
          </p>
          <div className="ad-disclosure">
            <Icon name="info" size={15} />
            以下の商品リンクはアフィリエイト広告です。
          </div>
          {suggestions.map((s) => (
            <div className="card" key={s.item_code ?? s.title}>
              <div className="sug-head">
                {s.image_url && <img src={s.image_url} alt="" width={72} height={72} />}
                <div className="sug-headtext">
                  <div className="sug-title">{s.title}</div>
                  <div className="sug-meta">
                    {s.rating
                      ? `★${s.rating}（${(s.review_count ?? 0).toLocaleString()}件）・`
                      : ""}
                    {priceLine(s)}
                    {s.sale_note ? `・${s.sale_note}` : ""}
                  </div>
                </div>
              </div>
              {s.summary && <p className="sug-reason">{s.summary}</p>}
              {s.external_ref && (
                <a
                  className="btn primary"
                  href={s.external_ref}
                  target="_blank"
                  rel="noopener sponsored"
                  onClick={(e) => {
                    api.clickSuggestion(s);
                    // ネイティブは実ブラウザで開く（埋め込みWebViewの遷移失敗・計測取りこぼし回避, #230）。
                    if (openExternalUrl(s.external_ref)) e.preventDefault();
                  }}
                >
                  商品を見る ↗
                </a>
              )}
              <button type="button" className="btn ghost" onClick={() => chooseSuggestion(s)}>
                この品に決める
              </button>
            </div>
          ))}
          <p className="muted" style={{ fontSize: 12 }}>
            価格は変動します。購入時はストア側の表示が優先されます。
            <br />
            Supported by Rakuten Developers
          </p>
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
                  <div className="between">
                    <b className="detail-name">{withHonor(event.party_name)}</b>
                    <button
                      type="button"
                      className="card-edit"
                      aria-label="内容を修正"
                      onClick={startEdit}
                    >
                      <Icon name="edit" size={18} />
                    </button>
                  </div>
                  <div className="detail-amount">{yen(event.amount)}</div>
                  <div className="detailrows">
                    <div className="between">
                      <span className="muted">用途</span>
                      <span>{event.purpose}</span>
                    </div>
                    {event.item && (
                      <div className="between">
                        <span className="muted">品物</span>
                        <span>{event.item}</span>
                      </div>
                    )}
                    {event.relationship && (
                      <div className="between">
                        <span className="muted">続柄</span>
                        <span>{event.relationship}</span>
                      </div>
                    )}
                    <div className="between">
                      <span className="muted">種類</span>
                      <span>{event.direction === "received" ? "もらった" : "あげた"}</span>
                    </div>
                    <div className="between">
                      <span className="muted">
                        {event.direction === "received" ? "もらった日" : "あげた日"}
                      </span>
                      <span>{event.occurred_at || "—"}</span>
                    </div>
                  </div>
                  <div className="detail-photo">
                    {event.image_url && (
                      <img className="detail-image" src={event.image_url} alt="贈答の写真" />
                    )}
                    <div className="detail-photo-actions">
                      {uploading ? (
                        <span className="photo-btn" aria-busy="true">
                          <Icon name="camera" size={16} />
                          アップロード中…
                        </span>
                      ) : (
                        <label className="photo-btn" htmlFor="detail-photo-input">
                          <Icon name="camera" size={16} />
                          {event.image_url ? "写真を差し替え" : "写真を追加"}
                        </label>
                      )}
                      {event.image_url && !uploading && (
                        <button
                          type="button"
                          className="photo-btn danger"
                          onClick={() => changeImage(null)}
                        >
                          <Icon name="trash" size={16} />
                          削除
                        </button>
                      )}
                    </div>
                    <input
                      id="detail-photo-input"
                      className="visually-hidden"
                      type="file"
                      accept="image/*"
                      onChange={(e) => changeImage(e.target.files?.[0] ?? null)}
                    />
                  </div>
                </div>
              ) : (
                <div className="card">
                  <div className="h" style={{ fontSize: 14 }}>
                    内容を修正
                  </div>
                  <div className="field">
                    <label htmlFor="edit-party">お相手</label>
                    <PartySelect
                      id="edit-party"
                      value={editDraft.party_id}
                      parties={parties}
                      onChange={(pid) => setEditDraft((d) => (d ? { ...d, party_id: pid } : d))}
                      onAdd={(name, relationship) =>
                        addParty(name, relationship, (pid) =>
                          setEditDraft((d) => (d ? { ...d, party_id: pid } : d)),
                        )
                      }
                      relOptions={relOptions}
                      relDefaults={relDefaults}
                      onAddRelationship={addRelationship}
                      onDeleteRelationship={deleteRelationship}
                    />
                    {editTried && !editDraft.party_id && (
                      <span className="field-error">お相手を選んでください。</span>
                    )}
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
                    {editTried && !editDraft.purpose.trim() && (
                      <span className="field-error">用途を選んでください。</span>
                    )}
                  </div>
                  <div className="field">
                    <label htmlFor="edit-amount">金額（円）</label>
                    <input
                      id="edit-amount"
                      className={`input${editTried && (!editDraft.amount.trim() || Number(editDraft.amount) <= 0) ? " warn" : ""}`}
                      type="number"
                      inputMode="numeric"
                      value={editDraft.amount}
                      onChange={(e) => setEditDraft({ ...editDraft, amount: e.target.value })}
                    />
                    {editTried && (!editDraft.amount.trim() || Number(editDraft.amount) <= 0) && (
                      <span className="field-error">金額は1円以上で入力してください。</span>
                    )}
                  </div>
                  <div className="field">
                    <label htmlFor="edit-occurred">
                      {event.direction === "received" ? "もらった日" : "あげた日"}
                    </label>
                    <input
                      id="edit-occurred"
                      className="input"
                      type="date"
                      value={editDraft.occurred_at}
                      onChange={(e) => setEditDraft({ ...editDraft, occurred_at: e.target.value })}
                    />
                    {event.direction === "received" && (
                      <span className="muted">
                        変更すると、お返し期限が自動で計算し直されます。
                      </span>
                    )}
                  </div>
                  <div className="field">
                    <label htmlFor="edit-item">品物（任意）</label>
                    <input
                      id="edit-item"
                      className="input"
                      list="item-suggestions"
                      placeholder="現金・メガネ など"
                      value={editDraft.item}
                      onChange={(e) => setEditDraft({ ...editDraft, item: e.target.value })}
                    />
                    <datalist id="item-suggestions">
                      {ITEM_SUGGESTIONS.map((s) => (
                        <option key={s} value={s} />
                      ))}
                    </datalist>
                  </div>
                  <p className="muted" style={{ marginTop: 4 }}>
                    続柄は相手（人）の情報です。お相手の選択肢から変更できます。
                  </p>
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
              {event.id && (
                <>
                  <div className="section-label">ステータス</div>
                  <div className="chips">
                    {["received", "considering", "done"].map((st) => (
                      <button
                        type="button"
                        key={st}
                        className={`chip ${event.status === st ? "on" : ""}`}
                        aria-pressed={event.status === st}
                        onClick={async () => {
                          const r = await api.setStatus(event.id, st);
                          setEvent(r.event);
                          notify("更新しました");
                        }}
                      >
                        {statusLabel(st)}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {event.direction === "received" && (
                <>
                  <div className="section-label">お返し期限</div>
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
                    {mourning ? "香典返しを進める" : "お返しを進める"}
                  </button>
                </>
              )}
              <div className="detail-danger">
                <button
                  type="button"
                  className="danger-link"
                  onClick={() => doDeleteRecord(event.record_id, event.party_name)}
                >
                  <Icon name="trash" size={14} />
                  この記録を削除
                </button>
              </div>
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
              // タップでその相手の履歴（台帳の絞り込み）へ（#180）。
              // biome-ignore lint/a11y/useSemanticElements: バッジ等を内包するカードのため button にできない。role+キーボードで代替。
              <div
                className="card tap"
                key={r.party_name}
                role="button"
                tabIndex={0}
                onClick={() => openPartyHistory(r.party_name)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    openPartyHistory(r.party_name);
                  }
                }}
              >
                <div className="between">
                  <b className="val">{withHonor(r.party_name)}</b>
                  {/* 気になる関係だけ穏やかに強調。それ以外は静かなバッジに（#181） */}
                  <span className={`balbadge ${r.attention ? "attention" : r.status}`}>
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
          <Bar title="マイページ" />

          {/* アカウント — 自分を最初に */}
          <div className="settings-label">アカウント</div>
          {authEnabled() ? (
            <div className="card">
              <div className="muted">ログイン中</div>
              <div className="account-id">{currentEmail() || "—"}</div>
              <button type="button" className="btn ghost danger" onClick={doSignOut}>
                ログアウト
              </button>
              <div className="account-danger">
                <button type="button" className="danger-link" onClick={doDeleteAccount}>
                  <Icon name="trash" size={14} />
                  アカウントを削除
                </button>
              </div>
            </div>
          ) : (
            <div className="card dashed">
              <div className="muted">開発用: ログイン中のユーザー（本番は Cognito ログイン）</div>
              <div className="row-inline">
                <input
                  className="input grow"
                  defaultValue={currentUserId()}
                  aria-label="ユーザー識別子"
                  onChange={(e) => (devUserRef.current = e.target.value)}
                />
                <button
                  type="button"
                  className="btn compact"
                  onClick={() => {
                    setCurrentUserId(devUserRef.current ?? currentUserId());
                    location.reload();
                  }}
                >
                  切替
                </button>
              </div>
              <div className="muted note-top">
                別の人に切替→相手の招待コードで「参加」すると、同じ台帳が共有されます。
              </div>
            </div>
          )}

          {/* ご家族で共有（台帳の共有・招待・参加） */}
          <div className="settings-label">ご家族で共有</div>
          {household &&
            (() => {
              const me = currentUserId();
              const sharing = isSharing(household);
              const iAmOwner = household.members.some(
                (m) => m.user_id === me && m.role === "owner",
              );
              return (
                <div className="card">
                  <div className="muted">
                    {sharing ? "この台帳を共有しているメンバー" : "まだ家族と共有していません"}
                  </div>
                  <div className="chips">
                    {household.members.map((m) => {
                      const d = memberDisplay(m, me);
                      return (
                        <span key={m.user_id} className="chip on">
                          {d.name}
                          {d.isOwner ? "（管理者）" : ""}
                          {iAmOwner && !d.isMe && (
                            <button
                              type="button"
                              className="memberx"
                              aria-label={`${d.name} を外す`}
                              onClick={() => doRemoveMember(m.user_id, d.name)}
                            >
                              <Icon name="close" size={12} strokeWidth={2.4} />
                            </button>
                          )}
                        </span>
                      );
                    })}
                  </div>
                  <div className="trustnote">
                    <span className="ic">
                      <Icon name="lock" size={18} />
                    </span>
                    <div>
                      台帳は<b>このご家族だけ</b>が見られます。
                    </div>
                  </div>

                  <hr className="divider" />

                  <div className="subhead">家族を招待する</div>
                  <div className="muted">このコードを伝えると、同じ台帳を一緒に使えます。</div>
                  <div className="row-inline">
                    <code className="invitecode grow">{household.invite_code}</code>
                    <button
                      type="button"
                      className="btn compact"
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

                  {/* 共有中は「参加」を控えめに折りたたみ、未共有時のみ前面に出す(#80) */}
                  {sharing && !showJoin ? (
                    <button type="button" className="linklike" onClick={() => setShowJoin(true)}>
                      別の家族の台帳に参加する
                    </button>
                  ) : (
                    <>
                      <div className="subhead">家族の台帳に参加する</div>
                      <div className="muted">家族から受け取った招待コードを入力します。</div>
                      <div className="row-inline">
                        <input
                          className="input grow"
                          placeholder="招待コード"
                          value={joinCode}
                          onChange={(e) => setJoinCode(e.target.value)}
                          aria-label="招待コード"
                        />
                        <button
                          type="button"
                          className="btn primary compact"
                          onClick={doJoinHousehold}
                        >
                          参加
                        </button>
                      </div>
                    </>
                  )}

                  {sharing && (
                    <button type="button" className="btn ghost danger" onClick={doLeaveHousehold}>
                      この家族から脱退する
                    </button>
                  )}
                </div>
              );
            })()}

          {/* お知らせ（メール通知）— ログイン環境のみ。メールアドレスが前提（#178） */}
          {authEnabled() && (
            <>
              <div className="settings-label">お知らせ</div>
              <div className="card">
                <div className="between">
                  <span>お返し時期をメールで知らせる</span>
                  <button
                    type="button"
                    className={`toggle${notifyEmail ? " on" : ""}`}
                    role="switch"
                    aria-checked={notifyEmail}
                    aria-label="お返し時期をメールで知らせる"
                    onClick={toggleNotify}
                  >
                    <span className="knob" />
                  </button>
                </div>
                <div className="muted note-top">
                  お返しの目安が近づいたら、登録のメールにそっとお知らせします。
                </div>
              </div>
            </>
          )}

          {/* 表示 */}
          <div className="settings-label">表示</div>
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

          {/* プライバシー */}
          <div className="settings-label">プライバシー</div>
          <div className="card">
            <TrustNote />
            <div className="muted note-top">
              贈り先の情報も含め、ご家族のデータはいつでも書き出し・削除できます。
            </div>
          </div>

          <div className="settings-label">規約・ポリシー</div>
          <div className="card legal-links">
            {(
              [
                ["privacy", "プライバシーポリシー"],
                ["terms", "利用規約"],
                ["operator", "運営者情報・お問い合わせ"],
              ] as const
            ).map(([k, label]) => (
              <button key={k} type="button" className="legal-link-row" onClick={() => openLegal(k)}>
                <span>{label}</span>
                <Icon name="chevronRight" size={18} />
              </button>
            ))}
          </div>

          {/* めやす・ふりかえり（旧マイページのツール群を集約） */}
          <div className="settings-label">めやす・ふりかえり</div>
          {annual && (
            <div className="card">
              <div className="subhead">{annual.year}年の振り返り</div>
              {annual.received_count === 0 && annual.given_count === 0 ? (
                <div className="muted">今年の記録はまだありません。撮影して残しましょう。</div>
              ) : (
                <>
                  <div className="split">
                    <div className="col">
                      <div className="muted">いただいた</div>
                      <div className="amount lg">{yen(annual.received_total)}</div>
                      <div className="muted">{annual.received_count}件</div>
                    </div>
                    <div className="col">
                      <div className="muted">贈った</div>
                      <div className="amount lg">{yen(annual.given_total)}</div>
                      <div className="muted">{annual.given_count}件</div>
                    </div>
                  </div>
                  <div className="muted note-top">
                    今年は <b>{annual.party_count}</b> 人の方とご縁がありました。
                  </div>
                </>
              )}
            </div>
          )}
          {giftTax && (
            <div className="card">
              <div className="subhead">贈与税の目安</div>
              <div className="muted">今年もらった（対象）合計</div>
              <div className="amount lg">{yen(giftTax.total)}</div>
              <div className="note-top">
                {giftTax.over ? (
                  <span className="text-accent">110万円の枠を超えています。確認しましょう。</span>
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
          <div className="card">
            <div className="subhead">お年玉の目安</div>
            <div className="field flush">
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
            {otoshiAge !== "" && !isValidChildAge(otoshiAge) && (
              <div className="muted note-top text-warn">0〜25歳の数字で入力してください。</div>
            )}
            {isValidChildAge(otoshiAge) &&
              (() => {
                const r = otoshidamaRange(Number(otoshiAge));
                return (
                  <div className="note-top">
                    <div className="muted">{r.bracket}</div>
                    <div className="range">
                      {r.low === r.high ? yen(r.low) : `${yen(r.low)}〜${yen(r.high)}`}
                    </div>
                    <div className="muted note-top">{r.note}</div>
                  </div>
                );
              })()}
            <div className="disclaimer">※ 家庭・地域で異なる一般的な目安です。</div>
          </div>
        </>
      )}

      {screen === "legal" && legalDoc && (
        <>
          <Bar title={LEGAL_DOCS[legalDoc].title} back={legalBack} />
          <LegalView docKey={legalDoc} />
        </>
      )}

      {screen !== "login" && screen !== "legal" && (
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
            onClick={() => {
              // タブからは常に絞り込みなしの全件・戻る導線なしで開く（#180）
              setLedgerView(LEDGER_DEFAULT);
              setLedgerBack(null);
              go("ledger");
            }}
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
