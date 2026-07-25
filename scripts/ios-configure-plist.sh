#!/usr/bin/env bash
# CI 生成の Info.plist に noshi 固有設定を注入する（ios/ を都度生成する運用のため）。
#  - 輸出コンプライアンス自動化（#213）: ITSAppUsesNonExemptEncryption=false で毎回の質問をスキップ。
#  - カスタム URL スキーム（#204）: ソーシャルログインの戻り先 me.noshi.app://callback を受けるため。
#  - カメラ/写真の用途文言（#203）: ネイティブ撮影・ライブラリ選択の権限ダイアログに表示。
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

# カメラ/写真の用途文言（#203）。慶弔トーンで簡潔に。
# 注意: NSPhotoLibraryAddUsageDescription は「保存機能を使わないから不要」ではない。
# @capacitor/camera の getPhoto は冒頭で必須キー3つ（Camera/PhotoLibrary/PhotoLibraryAdd）を
# ソースに関係なく全件チェックし、1つでも欠けると権限要求前に即 reject する
# （CameraPlugin.swift checkUsageDescriptions / CameraPropertyListKeys.allCases）。
# これが欠けていたことが全端末でのカメラ・ライブラリ即失敗＝審査却下 2.1(a) の根本原因（#414）。
"$PB" -c "Add :NSCameraUsageDescription string ご祝儀袋やお品物を撮影して内容を読み取るために使用します。" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :NSCameraUsageDescription ご祝儀袋やお品物を撮影して内容を読み取るために使用します。" "$PLIST"
"$PB" -c "Add :NSPhotoLibraryUsageDescription string 撮影済みの写真から、ご祝儀袋やお品物を選んで内容を読み取るために使用します。" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :NSPhotoLibraryUsageDescription 撮影済みの写真から、ご祝儀袋やお品物を選んで内容を読み取るために使用します。" "$PLIST"
"$PB" -c "Add :NSPhotoLibraryAddUsageDescription string 撮影した写真を端末の写真ライブラリに保存する場合に使用します。" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :NSPhotoLibraryAddUsageDescription 撮影した写真を端末の写真ライブラリに保存する場合に使用します。" "$PLIST"

# ステータスバーは暗色文字（生成り背景で読めるように）。ViewController ベースの制御は無効化（#206）。
"$PB" -c "Add :UIStatusBarStyle string UIStatusBarStyleDarkContent" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :UIStatusBarStyle UIStatusBarStyleDarkContent" "$PLIST"
"$PB" -c "Add :UIViewControllerBasedStatusBarAppearance bool false" "$PLIST" 2>/dev/null \
  || "$PB" -c "Set :UIViewControllerBasedStatusBarAppearance false" "$PLIST"

echo "--- result ---"
"$PB" -c "Print :ITSAppUsesNonExemptEncryption" "$PLIST"
"$PB" -c "Print :NSCameraUsageDescription" "$PLIST"
"$PB" -c "Print :NSPhotoLibraryUsageDescription" "$PLIST"
"$PB" -c "Print :NSPhotoLibraryAddUsageDescription" "$PLIST"
"$PB" -c "Print :CFBundleURLTypes" "$PLIST"
"$PB" -c "Print :UIStatusBarStyle" "$PLIST"
"$PB" -c "Print :UIViewControllerBasedStatusBarAppearance" "$PLIST"
