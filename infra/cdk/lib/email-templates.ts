/**
 * noshi 認証メールのデザインテンプレート（#182）。
 *
 * Cognito の verificationMessageTemplate（emailStyle=CODE）で使う HTML。
 * サインアップの確認コードと**パスワード再設定**の両方がこのテンプレートを使う。
 *
 * デザインシステム（frontend/src/tokens）をメールに写経する。ただしメールでは
 * CSS 変数・webフォント・外部CSS・<style> が使えない/不安定なため:
 *   - 配色はトークンの hex を直書き（生成り #F3EEE2 / 和紙 #FFFDF8 / 朱 #B23A2E など）
 *   - 見出しは明朝フォールバック（Hiragino Mincho / Yu Mincho / Noto Serif JP）
 *   - レイアウトは table、装飾は inline style のみ（Gmail / Apple Mail で崩れない）
 *   - ロゴ「の」印は朱の円＋白文字で再現（webフォント不要）
 *
 * Cognito は本文に確認コードのプレースホルダ {####} を必須とする。
 */

// --- デザイントークン（tokens/colors.css の値を直書き） -----------------------
const KINARI = "#F3EEE2"; // 生成り（ページ背景）
const WASHI_RAISED = "#FFFDF8"; // 和紙（カード）
const SUMI = "#23211C"; // 墨（本文）
const SUMI_SUB = "#5E574A"; // サブテキスト
const SUMI_MUTED = "#8A8270"; // 控えめ
const SHU = "#B23A2E"; // 朱（アクセント・ロゴ印）
const KON = "#1F3A5A"; // 紺（確認コード）
const BORDER_FAINT = "#E7DFCC"; // 淡い罫

const SERIF =
  "'Shippori Mincho B1','Hiragino Mincho ProN','Yu Mincho','Noto Serif JP',serif";
const SANS =
  "'Zen Kaku Gothic New','Hiragino Kaku Gothic ProN','Yu Gothic','Noto Sans JP',sans-serif";

const CONTACT = "contact@noshi.me";

/** 確認コード（サインアップ／パスワード再設定）メールの件名。 */
export const VERIFICATION_EMAIL_SUBJECT = "noshi｜確認コードのお知らせ";

/**
 * 確認コードメールの HTML 本文。`{####}` は Cognito が実際のコードに差し替える。
 * 急かさない落ち着いたトーン・大きめの確認コード・1アクションのみ。
 */
export function verificationEmailBody(): string {
  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<title>noshi 確認コード</title>
</head>
<body style="margin:0;padding:0;background:${KINARI};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:${KINARI};">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" border="0" style="width:480px;max-width:100%;background:${WASHI_RAISED};border:1px solid ${BORDER_FAINT};border-radius:16px;">
          <tr>
            <td style="padding:36px 32px 28px 32px;">

              <!-- ブランド: 朱の「の」印＋明朝の「し」で「のし」 -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
                <tr>
                  <td width="44" height="44" align="center" valign="middle" style="background:${SHU};border-radius:50%;color:#ffffff;font-family:${SERIF};font-size:23px;font-weight:700;line-height:44px;">の</td>
                  <td style="padding-left:10px;font-family:${SERIF};font-size:26px;font-weight:700;color:${SHU};letter-spacing:0.04em;">し</td>
                </tr>
              </table>

              <!-- 見出し -->
              <h1 style="margin:24px 0 0 0;text-align:center;font-family:${SERIF};font-size:21px;font-weight:700;color:${SUMI};letter-spacing:0.02em;">確認コードをお送りします</h1>
              <p style="margin:12px 0 0 0;text-align:center;font-family:${SANS};font-size:15px;line-height:1.9;color:${SUMI_SUB};">下の数字を、noshi の画面にご入力ください。</p>

              <!-- 確認コード -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding:24px 0 8px 0;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td align="center" style="background:${KINARI};border:1px solid ${BORDER_FAINT};border-radius:12px;padding:18px 32px;font-family:${SERIF};font-size:34px;font-weight:700;letter-spacing:8px;color:${KON};">{####}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="margin:16px 0 0 0;text-align:center;font-family:${SANS};font-size:13px;line-height:1.8;color:${SUMI_MUTED};">このコードは一定時間で無効になります。<br>お心当たりがない場合は、このメールはそのまま破棄してください。</p>

              <!-- 区切り -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="padding:24px 0 0 0;border-top:1px solid ${BORDER_FAINT};"></td></tr>
              </table>

              <!-- フッタ -->
              <p style="margin:20px 0 0 0;text-align:center;font-family:${SANS};font-size:12px;line-height:1.8;color:${SUMI_MUTED};">
                贈りものの記録と、お返し選び — noshi<br>
                お問い合わせ：<a href="mailto:${CONTACT}" style="color:${SUMI_SUB};text-decoration:underline;">${CONTACT}</a>
              </p>

            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}
