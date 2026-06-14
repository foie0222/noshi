#!/usr/bin/env bash
# CI 生成の Info.plist に noshi 固有設定を注入する（ios/ を都度生成する運用のため）。
#  - 輸出コンプライアンス自動化（#213）: ITSAppUsesNonExemptEncryption=false で毎回の質問をスキップ。
#  - カスタム URL スキーム（#204）: ソーシャルログインの戻り先 me.noshi.app://callback を受けるため。
set -euo pipefail

PLIST="${1:?usage: ios-configure-plist.sh <path-to-Info.plist>}"
PB=/usr/libexec/PlistBuddy
SCHEME="me.noshi.app"

echo "configuring $PLIST"

# 輸出コンプライアンス（HTTPS のみ＝非対象）。
"$PB" -c "Add :ITSAppUsesNonExemptEncryption bool false" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :ITSAppUsesNonExemptEncryption false" "$PLIST"

# カスタム URL スキーム（CFBundleURLTypes に未登録なら追加）。
if ! "$PB" -c "Print :CFBundleURLTypes" "$PLIST" >/dev/null 2>&1; then
  "$PB" -c "Add :CFBundleURLTypes array" "$PLIST"
fi
"$PB" -c "Add :CFBundleURLTypes:0 dict" "$PLIST" 2>/dev/null || true
"$PB" -c "Add :CFBundleURLTypes:0:CFBundleURLName string ${SCHEME}" "$PLIST" 2>/dev/null || true
"$PB" -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes array" "$PLIST" 2>/dev/null || true
"$PB" -c "Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string ${SCHEME}" "$PLIST" 2>/dev/null || true

# ステータスバーは暗色文字（生成り背景で読めるように）。ViewController ベースの制御は無効化（#206）。
"$PB" -c "Add :UIStatusBarStyle string UIStatusBarStyleDarkContent" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :UIStatusBarStyle UIStatusBarStyleDarkContent" "$PLIST"
"$PB" -c "Add :UIViewControllerBasedStatusBarAppearance bool false" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :UIViewControllerBasedStatusBarAppearance false" "$PLIST"

echo "--- result ---"
"$PB" -c "Print :ITSAppUsesNonExemptEncryption" "$PLIST"
"$PB" -c "Print :CFBundleURLTypes" "$PLIST"
"$PB" -c "Print :UIStatusBarStyle" "$PLIST"
"$PB" -c "Print :UIViewControllerBasedStatusBarAppearance" "$PLIST"
