"""お返し品ガイド（オフライン）。外部カタログ API・アフィリエイトに依存しない。

用途のトーン（慶事／弔事）・お返し予算・品目カテゴリ・続柄グループから、
定番の贈り物と「のし／時期」のマナーを返す。ネットワークも LLM も使わないため
決定論的で、運用コストは発生しない（楽天アフィリエイトは廃止）。

データは日本の贈答マナーの一般的な通説に基づく編集コンテンツ。
特定の店舗・商品を指すものではないので、価格や在庫の鮮度管理も不要。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.catalog.buckets import (
    ITEM_CATEGORIES,
    ITEM_CATEGORY_LABELS,
    band_label,
    band_of,
    item_category_key,
    slug_of,
    tone_slug,
)
from app.catalog.relationships import group_of

_MAX_ITEMS = 8


@dataclass(frozen=True)
class GiftIdea:
    """お返し品の定番アイデア1件。

    low/high はこの品が収まりやすい予算帯（円。high=None は上限なし）。
    groups は特に相性の良い続柄グループ（空タプルは万人向け）。
    """

    title: str
    summary: str
    tone: str  # cele / mourn
    category: str  # ITEM_CATEGORIES[tone] の slug
    low: int
    high: int | None
    tip: str = ""
    groups: tuple[str, ...] = ()


# --- 慶事（内祝い）---------------------------------------------------------
_CELE: tuple[GiftIdea, ...] = (
    # スイーツ・お菓子
    GiftIdea(
        "焼き菓子の詰合せ",
        "個包装で配りやすく日持ちもする、内祝いの王道。",
        "cele",
        "sweets",
        1000,
        4999,
        tip="職場へのお返しなら、人数より少し多めの個数を選ぶと安心です。",
        groups=("work", "other"),
    ),
    GiftIdea(
        "バウムクーヘン",
        "年輪が「幸せを重ねる」に通じる縁起物。結婚・出産の内祝いの定番です。",
        "cele",
        "sweets",
        2000,
        7999,
        tip="切り分けやすい大きさか、個包装かを相手の家族構成で選び分けを。",
    ),
    GiftIdea(
        "和菓子の詰合せ",
        "最中や羊羹など。年配の方や目上の方に失礼がありません。",
        "cele",
        "sweets",
        2000,
        9999,
        tip="日持ちは生菓子より干菓子・半生菓子が安心です。",
        groups=("family", "work"),
    ),
    GiftIdea(
        "名店のチョコレート・ショコラ",
        "見た目にも華やかで、友人へのお返しに喜ばれます。",
        "cele",
        "sweets",
        3000,
        14999,
        tip="夏場は溶けやすいので、クール便の有無を確認しましょう。",
        groups=("friend",),
    ),
    GiftIdea(
        "老舗の高級菓子詰合せ",
        "格の要る相手にも通る、包装まで整った贈答向けの一品。",
        "cele",
        "sweets",
        10000,
        None,
        tip="高額のお菓子は量より「どこの品か」が伝わるものを。",
        groups=("family", "work"),
    ),
    # グルメ・食品
    GiftIdea(
        "だし・調味料の詰合せ",
        "毎日使えて好みが分かれにくい、堅実なお返しです。",
        "cele",
        "gourmet",
        1500,
        5999,
        tip="家族構成がわからないときも外しにくい品です。",
    ),
    GiftIdea(
        "そうめん・乾麺の詰合せ",
        "日持ちがして常温保存でき、夏のお返しに向きます。",
        "cele",
        "gourmet",
        2000,
        5999,
    ),
    GiftIdea(
        "ハム・ソーセージの詰合せ",
        "家族で囲めるボリューム感。人数の多いお宅に喜ばれます。",
        "cele",
        "gourmet",
        3000,
        9999,
        tip="要冷蔵のことが多いので、受け取れる日を確認できると確実です。",
        groups=("family",),
    ),
    GiftIdea(
        "銘柄米の食べ比べセット",
        "必ず使う品で、重さのわりに負担になりません。",
        "cele",
        "gourmet",
        3000,
        9999,
    ),
    GiftIdea(
        "国産和牛のすき焼き・ステーキ",
        "特別感のある「ごちそう」。高額のお返しの定番です。",
        "cele",
        "gourmet",
        10000,
        None,
        tip="冷凍便が届く日を相手に一報しておくと親切です。",
        groups=("family", "friend"),
    ),
    GiftIdea(
        "海鮮の詰合せ（うなぎ・いくら等）",
        "食卓が華やぐ贈り物。目上の方へのお返しにも向きます。",
        "cele",
        "gourmet",
        8000,
        29999,
        groups=("family", "work"),
    ),
    # 飲料
    GiftIdea(
        "ドリップコーヒーの詰合せ",
        "一杯ずつ淹れられて場所を取らない、軽やかなお返し。",
        "cele",
        "drink",
        1000,
        4999,
        tip="職場に配るなら個包装のドリップバッグが扱いやすいです。",
        groups=("work", "other"),
    ),
    GiftIdea(
        "紅茶・ハーブティーの詰合せ",
        "香りの贈り物。友人や同僚へのお返しに気負いがありません。",
        "cele",
        "drink",
        2000,
        5999,
        groups=("friend", "work"),
    ),
    GiftIdea(
        "煎茶・玉露の詰合せ",
        "年配の方に間違いのない品。日本茶は慶事にも通ります。",
        "cele",
        "drink",
        3000,
        14999,
        groups=("family",),
    ),
    GiftIdea(
        "果汁100%ジュースの詰合せ",
        "お子さんのいるお宅でも安心して受け取ってもらえます。",
        "cele",
        "drink",
        3000,
        9999,
        groups=("family", "other"),
    ),
    GiftIdea(
        "スペシャルティコーヒーの豆・器具セット",
        "こだわりのある相手に。日常が少し豊かになる贈り物です。",
        "cele",
        "drink",
        10000,
        None,
        groups=("friend",),
    ),
    # タオル・寝具
    GiftIdea(
        "泉州タオルのセット",
        "吸水性が高く実用的。控えめな予算でも見劣りしません。",
        "cele",
        "towel",
        1000,
        4999,
    ),
    GiftIdea(
        "今治タオルのギフト",
        "肌ざわりと品質で名の通ったブランド。内祝いの鉄板です。",
        "cele",
        "towel",
        3000,
        14999,
        tip="色は白・生成りなど淡い色が万人向けです。",
    ),
    GiftIdea(
        "タオルケット・肌掛け",
        "毎日使えて長く残る、しっかりした贈り物。",
        "cele",
        "towel",
        8000,
        24999,
        groups=("family",),
    ),
    GiftIdea(
        "上質な羽毛・今治の寝具セット",
        "高額のお返しで実用性も伝えたいときに。",
        "cele",
        "towel",
        25000,
        None,
        groups=("family",),
    ),
    # 食器・キッチン
    GiftIdea(
        "波佐見焼・美濃焼の小皿セット",
        "普段づかいできる器。ひとり暮らしの相手にも重すぎません。",
        "cele",
        "tableware",
        2000,
        4999,
        groups=("friend",),
    ),
    GiftIdea(
        "保温タンブラー・マグ",
        "実用一点張りで長く使ってもらえる贈り物です。",
        "cele",
        "tableware",
        3000,
        9999,
        groups=("work", "friend"),
    ),
    GiftIdea(
        "ペアグラス・酒器",
        "ご夫婦へのお返しに。結婚内祝いでよく選ばれます。",
        "cele",
        "tableware",
        5000,
        14999,
        tip="割れ物は「壊れる」を連想する方もいます。相手の考え方に配慮を。",
        groups=("friend", "family"),
    ),
    GiftIdea(
        "ホーロー鍋・上質なキッチンツール",
        "台所に長く置かれる、存在感のあるお返し。",
        "cele",
        "tableware",
        15000,
        None,
        groups=("family",),
    ),
    # お酒
    GiftIdea(
        "クラフトビールの飲み比べ",
        "気取らず楽しんでもらえる、友人向けのお返し。",
        "cele",
        "sake",
        3000,
        7999,
        groups=("friend",),
    ),
    GiftIdea(
        "地酒の飲み比べセット",
        "小瓶で数種類。お酒好きの相手に外れがありません。",
        "cele",
        "sake",
        3000,
        9999,
        groups=("friend", "work"),
    ),
    GiftIdea(
        "大吟醸・純米大吟醸",
        "化粧箱入りで格があり、目上の方にも通ります。",
        "cele",
        "sake",
        5000,
        24999,
        tip="お酒を召し上がらない相手には避けましょう。",
        groups=("family", "work"),
    ),
    GiftIdea(
        "記念年のワイン",
        "出来事の年に合わせて選べる、記憶に残る一本。",
        "cele",
        "sake",
        10000,
        None,
        groups=("friend",),
    ),
    # カタログギフト
    GiftIdea(
        "選べるカタログギフト",
        "好みがわからないときの最適解。相手が自分で選べます。",
        "cele",
        "catalog",
        1000,
        None,
        tip="金額がわかりにくい形なので、目上の方にも使いやすい品です。",
    ),
    GiftIdea(
        "グルメ専門のカタログギフト",
        "食べ物に絞ったカタログ。消えもので残らないのが利点です。",
        "cele",
        "catalog",
        3000,
        29999,
    ),
    GiftIdea(
        "体験ギフト（食事・旅行）",
        "モノではなく時間を贈る。親しい相手に印象が残ります。",
        "cele",
        "catalog",
        10000,
        None,
        groups=("friend", "family"),
    ),
)

# --- 弔事（香典返し）-------------------------------------------------------
_MOURN: tuple[GiftIdea, ...] = (
    # 飲料
    GiftIdea(
        "銘茶の詰合せ",
        "香典返しの最も一般的な品。日持ちし、場所も取りません。",
        "mourn",
        "drink",
        1000,
        9999,
        tip="包装は白・銀・藍など落ち着いた色で。",
    ),
    GiftIdea(
        "海苔とお茶の詰合せ",
        "弔事の定番を組み合わせた、間違いのない品です。",
        "mourn",
        "drink",
        3000,
        9999,
    ),
    GiftIdea(
        "コーヒー・紅茶の詰合せ",
        "若い世代のご家庭にはお茶よりなじむことがあります。",
        "mourn",
        "drink",
        2000,
        9999,
        groups=("friend", "work"),
    ),
    GiftIdea(
        "高級銘茶（玉露・かぶせ茶）",
        "高額の香典返しでも、あとに残らない消えものとして整います。",
        "mourn",
        "drink",
        10000,
        None,
    ),
    # 食品
    GiftIdea(
        "海苔・乾物の詰合せ",
        "常温で長く置ける、弔事の王道。かさばらず配りやすい品です。",
        "mourn",
        "food",
        1000,
        9999,
    ),
    GiftIdea(
        "佃煮・椎茸などの乾物",
        "日常の食卓で使い切れる、負担にならない贈り物。",
        "mourn",
        "food",
        2000,
        9999,
    ),
    GiftIdea(
        "落ち着いた包装の焼き菓子",
        "個包装で配りやすく、法要のお返しにも向きます。",
        "mourn",
        "food",
        2000,
        9999,
        tip="紅白や華美な柄の入った菓子は避けましょう。",
        groups=("work", "other"),
    ),
    GiftIdea(
        "上質な調味料・だしの詰合せ",
        "高額でも残らない、実用の効く消えもの。",
        "mourn",
        "food",
        10000,
        None,
    ),
    # タオル・寝具
    GiftIdea(
        "白いタオルのセット",
        "白は「悲しみを包み、拭い去る」とされる弔事の定番です。",
        "mourn",
        "towel",
        1000,
        9999,
    ),
    GiftIdea(
        "今治タオルの無地ギフト",
        "実用品ながら質が伝わる、落ち着いた色味のセット。",
        "mourn",
        "towel",
        5000,
        14999,
    ),
    GiftIdea(
        "タオルケット・寝具",
        "高額の香典返しで、形に残っても重くなりにくい品です。",
        "mourn",
        "towel",
        10000,
        None,
    ),
    # 洗剤・日用品
    GiftIdea(
        "洗剤・石けんの詰合せ",
        "「悲しみを洗い流す」に通じる、古くからの香典返しです。",
        "mourn",
        "daily",
        1000,
        5999,
    ),
    GiftIdea(
        "線香・ろうそくの詰合せ",
        "仏事にそのまま使っていただける、静かな贈り物。",
        "mourn",
        "daily",
        2000,
        9999,
        tip="香りの好みが分かれるため、無香・微香のものが無難です。",
    ),
    GiftIdea(
        "上質なタオル・日用品の詰合せ",
        "日常で必ず使う品をまとめた、負担のない構成です。",
        "mourn",
        "daily",
        5000,
        None,
    ),
    # カタログギフト
    GiftIdea(
        "弔事用カタログギフト",
        "表紙も挨拶文も弔事仕様。相手に選んでいただけます。",
        "mourn",
        "catalog",
        1000,
        None,
        tip="遠方の方への香典返しは、持ち運びの負担が少ないこの形が親切です。",
    ),
    GiftIdea(
        "グルメ中心の弔事カタログ",
        "消えものに絞れるので、あとに残したくない場合に向きます。",
        "mourn",
        "catalog",
        3000,
        None,
    ),
)

GIFT_IDEAS: tuple[GiftIdea, ...] = _CELE + _MOURN


# --- のし・時期のマナー（用途カテゴリ slug ごと）---------------------------
ETIQUETTE: dict[str, dict[str, str]] = {
    "baby": {
        "title": "出産内祝いののし",
        "omotegaki": "内祝",
        "mizuhiki": "紅白の蝶結び（何度あってもよいお祝い）",
        "name": "赤ちゃんの名前（読み間違いを防ぐためふりがなを添えて）",
        "timing": "生後1か月ごろ、お宮参りの頃までに",
        "note": "命名のお披露目も兼ねます。内のし（包装紙の内側にのし）が控えめで一般的です。",
    },
    "wedding": {
        "title": "結婚内祝いののし",
        "omotegaki": "内祝",
        "mizuhiki": "紅白の結び切り（10本／一度きりのお祝い）",
        "name": "新姓、または両家の名字を連名で",
        "timing": "挙式後1か月以内に",
        "note": "蝶結びは「何度でも」の意味になるため使いません。結び切りを選びます。",
    },
    "school": {
        "title": "入学内祝いののし",
        "omotegaki": "内祝",
        "mizuhiki": "紅白の蝶結び",
        "name": "お子さんの名前",
        "timing": "入学後1か月以内に",
        "note": "お子さん本人からのお礼のひとことを添えると、とても喜ばれます。",
    },
    "housewarming": {
        "title": "新築内祝いののし",
        "omotegaki": "内祝",
        "mizuhiki": "紅白の蝶結び",
        "name": "世帯主の名字",
        "timing": "引っ越し後1〜2か月以内に",
        "note": "「新築内祝」としても構いません。"
        "新居へ招いてもてなす形でもよく、招けない方に品を贈ります。",
    },
    "kaiki": {
        "title": "快気内祝いののし",
        "omotegaki": "快気祝",
        "mizuhiki": "紅白の結び切り（繰り返さないように）",
        "name": "本人の名字",
        "timing": "退院・床上げから10日ほどを目安に",
        "note": "療養が続く場合は「快気内祝」「御見舞御礼」に。"
        "「病を残さない」の意味で、食品や洗剤など消えものを選ぶのが習わしです。",
    },
    "koden": {
        "title": "香典返しののし（掛け紙）",
        "omotegaki": "志",
        "mizuhiki": "黒白の結び切り（関西・西日本では黄白）",
        "name": "喪主の名字、または「◯◯家」",
        "timing": "四十九日の忌明け後、1か月以内に",
        "note": "西日本では「満中陰志」とすることもあります。"
        "お祝い事ではないため、掛け紙にのし（熨斗鮑）は付けません。挨拶状を添えます。",
    },
    "ochugen": {
        "title": "お中元をいただいたら",
        "omotegaki": "御礼",
        "mizuhiki": "紅白の蝶結び",
        "name": "ご自身の名字",
        "timing": "いただいてから3日以内にお礼状を",
        "note": "お中元・お歳暮は日頃のご挨拶。お返しは必須ではなく、お礼状だけで十分です。",
    },
    "oseibo": {
        "title": "お歳暮をいただいたら",
        "omotegaki": "御礼",
        "mizuhiki": "紅白の蝶結び",
        "name": "ご自身の名字",
        "timing": "いただいてから3日以内にお礼状を",
        "note": "お返しは必須ではありません。贈る場合は年明けの「御年賀」「寒中御見舞」でも。",
    },
    "general": {
        "title": "内祝いののし",
        "omotegaki": "内祝",
        "mizuhiki": "紅白の蝶結び",
        "name": "ご自身の名字",
        "timing": "いただいてから1か月以内に",
        "note": "金額の半分（半返し）が目安。同額以上は「受け取れない」の意に取られることも。",
    },
}


class GiftGuide:
    """GiftCatalogPort の実装。編集済みの定番リストから決定論的に提案する。"""

    def suggest(
        self, budget: int, relationship: str, purpose: str, category: str | None = None
    ) -> list[dict[str, Any]]:
        tone = tone_slug(purpose)
        group = group_of(relationship)
        pool = [i for i in GIFT_IDEAS if i.tone == tone]
        if category:
            narrowed = [i for i in pool if i.category == category]
            if narrowed:  # 未知の品目が来ても画面を空にしない（安全側）
                pool = narrowed
        order = [cat for cat, _label in ITEM_CATEGORIES.get(tone, [])]
        ranked = sorted(
            pool,
            key=lambda i: (
                _budget_distance(i, budget),  # 予算に合うものが先
                0 if group in i.groups else 1,  # 続柄グループに合うものが先
                order.index(i.category) if i.category in order else len(order),
                i.title,  # 同点は安定（決定論的な並び）
            ),
        )
        band = band_of(budget)
        return [self._to_suggestion(i, band) for i in ranked[:_MAX_ITEMS]]

    def available_categories(self, budget: int, purpose: str) -> list[dict[str, str]]:
        """その用途のトーンで選べる品目を、タブ表示順・表示名つきで返す。"""
        tone = tone_slug(purpose)
        return [{"slug": cat, "label": label} for cat, label in ITEM_CATEGORIES.get(tone, [])]

    def etiquette(self, purpose: str) -> dict[str, str]:
        """用途に応じた のし・水引・時期 の案内。未知の用途はトーンで振り分ける。"""
        return dict(ETIQUETTE[slug_of(purpose)])

    def _to_suggestion(self, idea: GiftIdea, band: str) -> dict[str, Any]:
        key = item_category_key(idea.tone, idea.category)
        return {
            "title": idea.title,
            "summary": idea.summary,
            "price_band": band_label(band),  # リクエスト予算の帯（選択時に記録へ残す）
            "price_hint": _price_hint(idea),  # この品自体の相場（カードの表示用）
            "category": idea.category,
            "category_label": ITEM_CATEGORY_LABELS.get(key, ""),
            "tip": idea.tip,
        }


def _price_hint(idea: GiftIdea) -> str:
    """この品が収まりやすい価格帯の表示（"¥3,000〜¥15,000" / 上限なしは "¥25,000〜"）。

    high は X,999 で持つので +1 して切りのよい額に見せる。
    """
    if idea.high is None:
        return f"¥{idea.low:,}〜"
    return f"¥{idea.low:,}〜¥{idea.high + 1:,}"


def _budget_distance(idea: GiftIdea, budget: int) -> int:
    """予算とアイデアの適正帯とのズレ（円）。0 は予算にぴったり収まる。"""
    if budget < idea.low:
        return idea.low - budget
    if idea.high is not None and budget > idea.high:
        return budget - idea.high
    return 0
