// iOS プッシュ通知（#205）。ネイティブ（Capacitor 内包）時のみ有効で、Web では何もしない。
// 許可の取得はユーザーがマイページのトグルを押した文脈でのみ行う（起動直後に迫らない）。
import { Capacitor } from "@capacitor/core";

/** この実行環境でプッシュ通知を扱えるか（iOS アプリ内のみ true）。 */
export function pushSupported(): boolean {
  return Capacitor.isNativePlatform() && Capacitor.isPluginAvailable("PushNotifications");
}

type RegisterFn = (token: string) => Promise<unknown>;

/** register() を発行し、取得した APNs トークンをバックエンドへ登録する。 */
async function registerAndUpload(registerToken: RegisterFn): Promise<boolean> {
  const { PushNotifications } = await import("@capacitor/push-notifications");
  const token = await new Promise<string | null>((resolve) => {
    // 端末側の応答が返らないケースに備えたタイムアウト（登録は次回起動時にも再試行される）
    const timer = setTimeout(() => resolve(null), 10_000);
    PushNotifications.addListener("registration", (t) => {
      clearTimeout(timer);
      resolve(t.value);
    });
    PushNotifications.addListener("registrationError", () => {
      clearTimeout(timer);
      resolve(null);
    });
    PushNotifications.register();
  });
  if (!token) return false;
  await registerToken(token);
  return true;
}

/**
 * プッシュ通知を有効化する（マイページのトグル ON から呼ぶ）。
 * OS の許可ダイアログ → APNs トークン取得 → バックエンド登録。拒否なら false。
 */
export async function enablePush(registerToken: RegisterFn): Promise<boolean> {
  if (!pushSupported()) return false;
  const { PushNotifications } = await import("@capacitor/push-notifications");
  const perm = await PushNotifications.requestPermissions();
  if (perm.receive !== "granted") return false;
  return registerAndUpload(registerToken);
}

/**
 * 起動時の呼び出し用。すでに許可済みの場合のみ再登録し、OS によるトークン
 * ローテーションへ追従する（未許可なら何もしない＝ダイアログを出さない）。
 */
export async function refreshPushToken(registerToken: RegisterFn): Promise<void> {
  if (!pushSupported()) return;
  const { PushNotifications } = await import("@capacitor/push-notifications");
  const st = await PushNotifications.checkPermissions();
  if (st.receive !== "granted") return;
  await registerAndUpload(registerToken);
}

/** 通知タップでアプリが開かれたときのハンドラを登録する（ホームのお返し予定へ誘導）。 */
export async function onPushTap(handler: () => void): Promise<void> {
  if (!pushSupported()) return;
  const { PushNotifications } = await import("@capacitor/push-notifications");
  PushNotifications.addListener("pushNotificationActionPerformed", () => handler());
}
