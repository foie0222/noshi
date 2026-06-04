#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""noshi MVP wireframe generator — emits neutral mobile (375x812) SVG wireframes.
Layout-reference only (brand deferred). One file per screen under screens/."""
import os, html

W, H = 375, 812
OUT = os.path.join(os.path.dirname(__file__), "screens")
os.makedirs(OUT, exist_ok=True)

C_FRAME = "#222"; C_LINE = "#bbb"; C_FILL = "#f4f4f5"; C_PRIMARY = "#3b3b3b"
C_TXT = "#333"; C_MUTE = "#888"; C_WARN = "#b8860b"; C_DANGER = "#a33"

def esc(s): return html.escape(str(s))

def svg_header(title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="sans-serif">
<rect x="0" y="0" width="{W}" height="{H}" fill="#fff" stroke="{C_FRAME}" stroke-width="2"/>
<rect x="0" y="0" width="{W}" height="24" fill="#fafafa"/>
<text x="12" y="16" font-size="10" fill="{C_MUTE}">9:41</text>
<text x="{W-12}" y="16" font-size="10" fill="{C_MUTE}" text-anchor="end">100%</text>
<!-- screen title chip -->
<text x="{W-10}" y="{H-8}" font-size="9" fill="#ccc" text-anchor="end">{esc(title)}</text>'''

def appbar(title, back=True, action=None):
    y0=24; out=f'<rect x="0" y="{y0}" width="{W}" height="48" fill="#fafafa" stroke="{C_LINE}"/>'
    if back: out+=f'<text x="14" y="{y0+30}" font-size="18" fill="{C_TXT}">‹</text>'
    out+=f'<text x="{W/2}" y="{y0+30}" font-size="15" fill="{C_TXT}" text-anchor="middle" font-weight="bold">{esc(title)}</text>'
    if action: out+=f'<text x="{W-14}" y="{y0+30}" font-size="12" fill="{C_PRIMARY}" text-anchor="end">{esc(action)}</text>'
    return out

def block(x,y,w,h,label,fill=C_FILL,sub=None,dashed=False):
    dash=' stroke-dasharray="5 4"' if dashed else ''
    out=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{C_LINE}"{dash}/>'
    out+=f'<text x="{x+12}" y="{y+22}" font-size="12" fill="{C_TXT}">{esc(label)}</text>'
    if sub: out+=f'<text x="{x+12}" y="{y+40}" font-size="10" fill="{C_MUTE}">{esc(sub)}</text>'
    return out

def button(x,y,w,label,primary=True,danger=False):
    fill=C_PRIMARY if primary else "#fff"
    if danger: fill="#fff"
    txt="#fff" if primary and not danger else (C_DANGER if danger else C_TXT)
    stroke=C_DANGER if danger else C_PRIMARY
    return (f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="22" fill="{fill}" stroke="{stroke}"/>'
            f'<text x="{x+w/2}" y="{y+28}" font-size="13" fill="{txt}" text-anchor="middle">{esc(label)}</text>')

def field(x,y,w,label,val="",warn=False):
    out=f'<text x="{x}" y="{y-4}" font-size="10" fill="{C_MUTE}">{esc(label)}</text>'
    out+=f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="6" fill="#fff" stroke="{C_WARN if warn else C_LINE}"/>'
    if val: out+=f'<text x="{x+10}" y="{y+23}" font-size="12" fill="{C_TXT}">{esc(val)}</text>'
    if warn: out+=f'<text x="{x+w-8}" y="{y+22}" font-size="9" fill="{C_WARN}" text-anchor="end">要確認</text>'
    return out

def stepper(step,total=4):
    y=H-44; out=f'<rect x="0" y="{y}" width="{W}" height="44" fill="#fafafa" stroke="{C_LINE}"/>'
    seg=W/total
    for i in range(total):
        on = i < step
        out+=f'<rect x="{i*seg+10}" y="{y+20}" width="{seg-20}" height="4" rx="2" fill="{C_PRIMARY if on else C_LINE}"/>'
    out+=f'<text x="{W/2}" y="{y+15}" font-size="9" fill="{C_MUTE}" text-anchor="middle">撮影ウィザード {step}/{total}</text>'
    return out

def note(x,y,text,color=C_MUTE):
    return f'<text x="{x}" y="{y}" font-size="9" fill="{color}">{esc(text)}</text>'

def write(name, body):
    open(os.path.join(OUT,f"{name}.svg"),"w",encoding="utf-8").write(svg_header(name)+body+"\n</svg>\n")

# ---- screens ----
def login():
    b=appbar("noshi へようこそ",back=False)
    b+=f'<circle cx="{W/2}" cy="150" r="34" fill="{C_FILL}" stroke="{C_LINE}"/><text x="{W/2}" y="156" font-size="13" fill="{C_MUTE}" text-anchor="middle">logo</text>'
    b+=button(28,210,W-56,"Google で続ける",primary=False)
    b+=button(28,262,W-56,"Apple で続ける",primary=False)
    b+=note(W/2-20,330,"または")
    b+=field(28,360,W-56,"メールアドレス","")
    b+=field(28,422,W-56,"パスワード","")
    b+=button(28,480,W-56,"ログイン")
    b+=note(28,540,"※連続失敗でレート制限 / エラーは汎用文言 (OWASP)")
    write("login",b)

def consent():
    b=appbar("ご利用にあたって",back=False)
    b+=block(16,90,W-32,150,"利用目的の説明",sub="贈答記録の管理・お返し支援に利用します")
    b+=block(16,256,W-32,120,"データの扱い",sub="氏名/関係/金額は機微情報として暗号化保存")
    b+=block(16,392,W-32,110,"第三者(贈り先)の情報",sub="取り扱い方針・削除の手段を明記")
    b+=f'<rect x="16" y="520" width="20" height="20" rx="4" fill="#fff" stroke="{C_LINE}"/><text x="44" y="535" font-size="11" fill="{C_TXT}">上記に同意します</text>'
    b+=button(16,560,W-32,"同意して始める")
    b+=note(16,624,"S-14 / 初回ログイン後に一度だけ表示")
    write("consent",b)

def home():
    b=appbar("noshi",back=False,action="⚙")
    for i,(t,v) in enumerate([("もらった","¥84,000"),("あげた","¥39,000"),("差分","+¥45,000")]):
        x=16+i*((W-32)/3)
        b+=block(x+4,84,(W-32)/3-8,64,t,sub=v)
    b+=f'<text x="16" y="180" font-size="12" fill="{C_TXT}" font-weight="bold">未完了のお返し</text>'
    b+=block(16,192,W-32,60,"佐藤様 出産祝い ¥30,000",sub="検討中 — タップで詳細")
    b+=block(16,260,W-32,60,"田中様 結婚祝い ¥50,000",sub="検討中")
    b+=f'<text x="16" y="356" font-size="12" fill="{C_TXT}" font-weight="bold">直近の記録</text>'
    b+=block(16,368,W-32,56,"山田様 お中元 ¥5,000",sub="受領 8/3")
    b+=button(16,H-120,W-32,"＋ 贈答を撮影")
    b+=note(16,H-60,"主導線=撮影。台帳/設定はヘッダ・メニューから (S-4,S-8)")
    write("home",b)

def home_empty():
    b=appbar("noshi",back=False,action="⚙")
    b+=f'<circle cx="{W/2}" cy="280" r="46" fill="{C_FILL}" stroke="{C_LINE}" stroke-dasharray="5 4"/><text x="{W/2}" y="286" font-size="12" fill="{C_MUTE}" text-anchor="middle">empty</text>'
    b+=f'<text x="{W/2}" y="370" font-size="15" fill="{C_TXT}" text-anchor="middle">最初の贈答を記録しよう</text>'
    b+=f'<text x="{W/2}" y="394" font-size="11" fill="{C_MUTE}" text-anchor="middle">撮影するだけで自動で記録できます</text>'
    b+=button(16,440,W-32,"＋ 贈答を撮影")
    b+=note(16,H-40,"empty 状態の代表画面")
    write("home-empty",b)

def capture():
    b=appbar("撮影")
    b+=block(28,96,W-56,W-56,"カメラプレビュー / ドロップゾーン",fill="#eee",sub="ご祝儀袋・のし・送り状を撮影",dashed=True)
    b+=note(28,W+70,"複数枚アップロード可 (S-3)")
    b+=button(28,W+90,W-56,"この画像で読み取る")
    b+=stepper(1)
    write("capture",b)

def capture_loading():
    b=appbar("読み取り中")
    b+=f'<circle cx="{W/2}" cy="300" r="40" fill="none" stroke="{C_LINE}" stroke-width="6"/><path d="M{W/2} 260 a40 40 0 0 1 40 40" fill="none" stroke="{C_PRIMARY}" stroke-width="6"/>'
    b+=f'<text x="{W/2}" y="380" font-size="14" fill="{C_TXT}" text-anchor="middle">読み取り中…</text>'
    b+=f'<text x="{W/2}" y="404" font-size="11" fill="{C_MUTE}" text-anchor="middle">通常 10 秒以内 (NFR-1.2)</text>'
    b+=f'<text x="{W/2}" y="470" font-size="12" fill="{C_PRIMARY}" text-anchor="middle">キャンセル</text>'
    b+=stepper(2); b+=note(16,H-60,"loading 状態の代表画面 (S-9)")
    write("capture-loading",b)

def extract_review():
    b=appbar("内容を確認")
    b+=block(W-92,84,72,72,"画像",fill="#eee",dashed=True)
    b+=field(16,118,W-120,"金額","¥30,000")
    b+=field(16,182,W-32,"お相手の氏名","佐藤 花子",warn=True)
    b+=field(16,246,(W-40)/2,"続柄","友人")
    b+=field(16+(W-40)/2+8,246,(W-40)/2,"用途","出産祝い")
    b+=field(16,310,W-32,"日付","2026-05-20")
    b+=f'<text x="16" y="372" font-size="11" fill="{C_TXT}">方向:</text><rect x="60" y="358" width="70" height="26" rx="13" fill="{C_PRIMARY}"/><text x="95" y="375" font-size="11" fill="#fff" text-anchor="middle">受領</text><rect x="138" y="358" width="70" height="26" rx="13" fill="#fff" stroke="{C_LINE}"/><text x="173" y="375" font-size="11" fill="{C_TXT}" text-anchor="middle">贈与</text>'
    b+=button(16,H-110,W-32,"確認して保存")
    b+=stepper(2); b+=note(16,H-54,"低信頼項目に要確認バッジ (S-3,S-9)")
    write("extract-review",b)

def extract_error():
    b=appbar("読み取れませんでした")
    b+=f'<rect x="16" y="84" width="{W-32}" height="56" rx="8" fill="#fbf3e6" stroke="{C_WARN}"/><text x="28" y="108" font-size="12" fill="{C_WARN}">うまく読み取れませんでした</text><text x="28" y="126" font-size="10" fill="{C_MUTE}">手入力で続けられます（汎用文言 / OWASP）</text>'
    b+=field(16,176,W-32,"金額","")
    b+=field(16,240,W-32,"お相手の氏名","")
    b+=field(16,304,(W-40)/2,"用途","")
    b+=field(16+(W-40)/2+8,304,(W-40)/2,"日付","")
    b+=button(16,400,W-32,"手入力で続ける")
    b+=button(16,452,W-32,"撮影し直す",primary=False)
    b+=stepper(2); b+=note(16,H-54,"error 状態の代表 / 内部情報を出さない")
    write("extract-error",b)

def record_saved():
    b=appbar("完了",back=False)
    b+=f'<circle cx="{W/2}" cy="200" r="40" fill="#eef7ee" stroke="#6a6"/><text x="{W/2}" y="212" font-size="30" fill="#5a5" text-anchor="middle">✓</text>'
    b+=f'<text x="{W/2}" y="290" font-size="16" fill="{C_TXT}" text-anchor="middle">記録しました</text>'
    b+=block(16,320,W-32,72,"佐藤 花子 / 出産祝い",sub="¥30,000 受領 — 2026-05-20")
    b+=button(16,430,W-32,"お返しを検討する")
    b+=button(16,482,W-32,"ホームに戻る",primary=False)
    write("record-saved",b)

def half_return():
    b=appbar("半返し計算")
    b+=block(16,84,W-32,64,"もらった額",sub="¥30,000 / 出産祝い")
    b+=f'<rect x="16" y="164" width="{W-32}" height="96" rx="8" fill="{C_FILL}" stroke="{C_LINE}"/><text x="{W/2}" y="200" font-size="12" fill="{C_MUTE}" text-anchor="middle">推奨お返し額</text><text x="{W/2}" y="236" font-size="22" fill="{C_TXT}" text-anchor="middle" font-weight="bold">¥10,000 〜 ¥15,000</text>'
    b+=block(16,276,W-32,110,"根拠",sub="出産祝いは 1/3〜半返しが目安 / 地域慣習を初期値")
    b+=field(16,420,W-32,"上書き額（任意）","")
    b+=button(16,H-90,W-32,"次へ（お返し品）")
    b+=note(16,H-36,"S-5 / 上書きは以後の提案に反映")
    write("half-return",b)

def gift_suggest():
    b=appbar("お返し品の提案")
    b+=f'<rect x="16" y="84" width="120" height="26" rx="13" fill="{C_FILL}" stroke="{C_LINE}"/><text x="76" y="101" font-size="11" fill="{C_TXT}" text-anchor="middle">予算 ¥10–15k</text>'
    for i in range(3):
        y=126+i*150
        b+=f'<rect x="16" y="{y}" width="{W-32}" height="136" rx="8" fill="#fff" stroke="{C_LINE}"/>'
        b+=f'<rect x="28" y="{y+12}" width="80" height="80" rx="6" fill="#eee" stroke="{C_LINE}" stroke-dasharray="4 3"/><text x="68" y="{y+56}" font-size="9" fill="{C_MUTE}" text-anchor="middle">商品画像</text>'
        b+=f'<text x="120" y="{y+30}" font-size="12" fill="{C_TXT}">カタログギフト {chr(65+i)}</text><text x="120" y="{y+50}" font-size="10" fill="{C_MUTE}">¥{12000+i*1000:,} ・ 外部サイト↗</text>'
        b+=f'<rect x="120" y="{y+70}" width="100" height="30" rx="15" fill="{C_PRIMARY}"/><text x="170" y="{y+90}" font-size="11" fill="#fff" text-anchor="middle">これにする</text>'
    b+=note(16,H-24,"MVP は提案のみ・noshi 内決済なし (S-6)")
    write("gift-suggest",b)

def letter():
    b=appbar("礼状の文面")
    b+=f'<text x="16" y="100" font-size="11" fill="{C_MUTE}">トーン:</text>'
    for i,t in enumerate(["丁寧","標準","カジュアル"]):
        x=64+i*86; on=i==0
        b+=f'<rect x="{x}" y="86" width="78" height="26" rx="13" fill="{C_PRIMARY if on else "#fff"}" stroke="{C_PRIMARY if on else C_LINE}"/><text x="{x+39}" y="103" font-size="11" fill="{"#fff" if on else C_TXT}" text-anchor="middle">{t}</text>'
    b+=f'<rect x="16" y="128" width="{W-32}" height="300" rx="8" fill="#fff" stroke="{C_LINE}"/><text x="28" y="156" font-size="11" fill="{C_TXT}">この度はご出産のお祝いを賜り…</text><text x="28" y="178" font-size="11" fill="{C_TXT}">（生成された文面・編集可）</text>'
    b+=button(16,450,(W-40)/2,"コピー",primary=False)
    b+=button(16+(W-40)/2+8,450,(W-40)/2,"書き出し",primary=False)
    b+=button(16,H-90,W-32,"このお礼で完了")
    b+=note(16,H-36,"LLM 送信は最小化 (S-7 AC3)")
    write("letter",b)

def ledger():
    b=appbar("贈答の台帳")
    b+=f'<rect x="16" y="84" width="{W-32}" height="36" rx="18" fill="{C_FILL}" stroke="{C_LINE}"/><text x="34" y="107" font-size="12" fill="{C_MUTE}">🔍 検索（相手・用途）</text>'
    for i,t in enumerate(["相手","用途","期間"]):
        x=16+i*72
        b+=f'<rect x="{x}" y="130" width="64" height="26" rx="13" fill="#fff" stroke="{C_LINE}"/><text x="{x+32}" y="147" font-size="10" fill="{C_TXT}" text-anchor="middle">{t} ▾</text>'
    rows=[("↙ 受領","佐藤 花子","¥30,000","出産祝 5/20"),("↗ 贈与","田中 太郎","¥50,000","結婚祝 4/2"),("↙ 受領","山田 一郎","¥5,000","お中元 8/3"),("↙ 受領","鈴木 桜","¥10,000","入学祝 3/30")]
    for i,(d,n,a,u) in enumerate(rows):
        y=172+i*64
        b+=f'<rect x="16" y="{y}" width="{W-32}" height="56" rx="8" fill="#fff" stroke="{C_LINE}"/><text x="28" y="{y+24}" font-size="11" fill="{C_MUTE}">{d}</text><text x="92" y="{y+24}" font-size="12" fill="{C_TXT}">{n}</text><text x="{W-28}" y="{y+24}" font-size="12" fill="{C_TXT}" text-anchor="end">{a}</text><text x="92" y="{y+42}" font-size="10" fill="{C_MUTE}">{u}</text>'
    b+=block(16,440,W-32,56,"相手別サマリ",sub="佐藤様: もらった ¥30,000 / 差分 +¥30,000")
    b+=note(16,H-24,"行タップ→event-detail / 空は EmptyState (S-4)")
    write("ledger",b)

def event_detail():
    b=appbar("贈答の詳細",action="編集")
    b+=block(16,84,W-32,84,"佐藤 花子 / 出産祝い",sub="¥30,000 受領 — 2026-05-20")
    b+=f'<text x="16" y="200" font-size="11" fill="{C_TXT}" font-weight="bold">ステータス</text>'
    labels=["受領","検討中","完了"]
    for i,l in enumerate(labels):
        cx=60+i*120; on=i<=1
        b+=f'<circle cx="{cx}" cy="232" r="12" fill="{C_PRIMARY if on else "#fff"}" stroke="{C_PRIMARY if on else C_LINE}"/><text x="{cx}" y="262" font-size="10" fill="{C_TXT}" text-anchor="middle">{l}</text>'
        if i<2: b+=f'<line x1="{cx+12}" y1="232" x2="{cx+108}" y2="232" stroke="{C_LINE}"/>'
    b+=block(16,290,W-32,80,"紐付くお返し",sub="カタログギフト B ¥12,000（提案）＋礼状あり")
    b+=button(16,396,W-32,"お返しの続き（半返し→提案→礼状）")
    b+=button(16,460,W-32,"このイベントを削除",primary=False,danger=True)
    b+=note(16,H-30,"削除は確認ダイアログ＋監査記録 (S-8)")
    write("event-detail",b)

def settings():
    b=appbar("設定")
    b+=f'<text x="16" y="100" font-size="11" fill="{C_MUTE}">アカウント</text>'
    b+=block(16,110,W-32,50,"プロフィール")
    b+=block(16,168,W-32,50,"ログアウト")
    b+=f'<text x="16" y="252" font-size="11" fill="{C_MUTE}">プライバシー</text>'
    b+=block(16,262,W-32,50,"同意状況の確認")
    b+=block(16,320,W-32,50,"データをエクスポート")
    b+=f'<text x="16" y="412" font-size="11" fill="{C_DANGER}">Danger Zone</text>'
    b+=f'<rect x="16" y="422" width="{W-32}" height="50" rx="8" fill="#fff" stroke="{C_DANGER}"/><text x="28" y="452" font-size="12" fill="{C_DANGER}">アカウントと全データを削除</text>'
    b+=note(16,500,"削除=確認ダイアログ必須・監査ログ記録 (S-2,S-13)")
    write("settings",b)

for fn in [login,consent,home,home_empty,capture,capture_loading,extract_review,
           extract_error,record_saved,half_return,gift_suggest,letter,ledger,
           event_detail,settings]:
    fn()
print("generated:", len(os.listdir(OUT)), "svg files")
