#!/usr/bin/env bash
# CI 生成の iOS プロジェクトに Sign in with Apple（#198）と Push（#205）の entitlement を注入する。
set -euo pipefail
ENT="${1:?usage: ios-configure-entitlements.sh <path-to-App.entitlements>}"
PB=/usr/libexec/PlistBuddy
if [ ! -f "$ENT" ]; then
  cat > "$ENT" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict/></plist>
XML
fi
"$PB" -c "Delete :com.apple.developer.applesignin" "$ENT" 2>/dev/null || true
"$PB" -c "Add :com.apple.developer.applesignin array" "$ENT"
"$PB" -c "Add :com.apple.developer.applesignin:0 string Default" "$ENT"
# プッシュ通知（#205）。TestFlight/App Store は本番 APNs のため production 固定。
"$PB" -c "Delete :aps-environment" "$ENT" 2>/dev/null || true
"$PB" -c "Add :aps-environment string production" "$ENT"
echo "--- entitlements ---"
"$PB" -c "Print" "$ENT"

