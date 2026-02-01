---
name: surugaya-matcher
description: |
  駿河屋同一商品検索サブエージェント。
  指定キーワードで検索し、販売中商品の詳細ページ画像を
  ローカル参照画像（Target-Product/）とVision比較して同一商品を特定。
  結果は固定JSONスキーマでメインエージェントに返却。

  呼び出しトリガー：
  - 「駿河屋で同一商品を探して」
  - 「駿河屋で〇〇と同じ商品を検索」
  - 「surugaya match」
  - 「駿河屋照合」
tools: Read, Bash, Glob
model: sonnet
---

# 駿河屋同一商品検索ワークフロー v1.0

## CRITICAL RULES（必ず遵守）

1. **画像ダウンロード禁止**: /tmp一時保存 → 処理後削除
2. **詳細ページ全画像比較**: 掲載されている全画像が対象
3. **固定JSONスキーマ**: 必ず指定スキーマで返却
4. **売り切れ判定**: 「品切れ」「売り切れ」テキストで判定
5. **clickでページ遷移しない**: eval でURL取得 → open で直接遷移
6. **800pxリサイズ**: 長辺800px以上は800pxに縮小（トークン節約）
7. **駿河屋直販 vs マケプレ**: 両方の価格を確認、seller_typeで区別

---

## 入力パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| keyword | string | ✓ | - | 検索キーワード |
| reference_image | string | ✓ | - | 参照画像ファイルパス（例: `images/Target-Product/405912557904.jpg`） |
| max_items | number | - | 10 | 検査件数上限 |
| target_price | number | - | null | 仕入れ金額上限（円）。超過商品はスキップ |
| notes | string | - | null | 備考（検索条件、除外条件等の参考情報） |

---

## 返却JSONスキーマ（固定）

**⚠️ 他サイトマッチャーと統一されたスキーマ** - メインエージェントでの統合処理に必須

```json
{
  "success": true,
  "source": "surugaya",
  "matches": [
    {
      "url": "https://www.suruga-ya.jp/product/detail/147000347",
      "price_value": 6080,
      "price_total": 6580,
      "shipping_included": false,
      "condition": "中古",
      "condition_group": "used",
      "confidence": "high",
      "accessory_status": "unknown",
      "seller_type": "marketplace"
    }
  ],
  "best_candidate": {
    "url": "https://www.suruga-ya.jp/product/detail/147000347",
    "price_value": 13800,
    "price_total": 13800,
    "shipping_included": true,
    "condition": "中古",
    "condition_group": "used",
    "confidence": "high",
    "reason_code": "price_over",
    "accessory_status": "unknown",
    "seller_type": "surugaya"
  },
  "checked_count": 2,
  "skipped_by_junk": 0,
  "filtered_by_price": 1,
  "error": null
}
```

### フィールド説明

| フィールド | 説明 |
|-----------|------|
| `source` | **必須** サイト識別子（固定値: `"surugaya"`） |
| `matches` | 条件を満たす候補リスト |
| `matches[].price_value` | 表示価格（数値） |
| `matches[].price_total` | 送料込み価格（1,500円未満は送料500円加算） |
| `matches[].shipping_included` | 送料込みか（`true`: 1,500円以上、`false`: 1,500円未満） |
| `matches[].condition` | 商品の状態（「中古」「新品」等） |
| `matches[].condition_group` | `"new"` / `"used"` |
| `matches[].confidence` | `high` / `medium` / `low` |
| `matches[].accessory_status` | `"complete"` / `"missing"` / `"unknown"`（付属品状態） |
| `matches[].seller_type` | `"surugaya"` / `"marketplace"`（出品者タイプ） |
| `best_candidate` | 条件未達でも同一商品の最安値（参考情報、なければ `null`） |
| `best_candidate.reason_code` | 条件未達の理由（`price_over` / `condition_mismatch`） |
| `checked_count` | 検査した商品数 |
| `skipped_by_junk` | ジャンク品としてスキップした件数 |
| `filtered_by_price` | 価格超過でスキップした件数 |

### condition_group 判定ルール

| condition（商品の状態） | condition_group |
|------------------------|-----------------|
| 新品 | `"new"` |
| 新品通常 | `"new"` |
| 新品未開封 | `"new"` |
| 未開封 | `"new"` |
| 中古 | `"used"` |
| 中古良い | `"used"` |
| 中古可 | `"used"` |
| 中古通常 | `"used"` |
| 良い | `"used"` |
| 可 | `"used"` |
| ワケアリ | `"used"` |

### 送料計算ルール

| 商品価格 | 送料 | shipping_included | price_total計算 |
|---------|------|-------------------|-----------------|
| 1,500円以上 | 無料 | `true` | price_value |
| 1,500円未満 | 500円 | `false` | price_value + 500 |

---

## ワークフロー

```
Step 0: 初期化
    │
    ▼
Step 1: 駿河屋検索
    │
    ▼
Step 2: 商品リスト抽出（駿河屋直販 + マケプレ）
    │
    ▼
Step 3: 商品詳細ページへ遷移（eval+open方式）
    │
    ▼
Step 3.5: ジャンク品判定
    │
    ├─ NGキーワード含む → スキップ（skipped_by_junk++）
    │
    ▼
Step 4: 全画像取得・リサイズ・Vision比較
    │
    ▼
Step 5: JSON返却
```

---

### Step 0: 初期化

```bash
# 参照画像の存在確認
ls {reference_image}

# 参照画像を読み込み（Vision比較用）
Read {reference_image}
```

- reference_image: 必須パラメータ、存在しない場合はエラー終了
- target_price確認: 値がある場合は価格フィルタリング有効化
- notes確認: 値がある場合は評価時に参考情報として使用

---

### Step 1: 駿河屋検索

```bash
# 基本検索
agent-browser --session surugaya open "https://www.suruga-ya.jp/search?search_word={keyword}"
sleep 3
agent-browser --session surugaya snapshot -i
```

**価格フィルタを使用する場合:**

```bash
# 最大価格指定（例: 6100円以下）
agent-browser --session surugaya open "https://www.suruga-ya.jp/search?search_word={keyword}&price=[0,{max_price}]"
sleep 3
```

**在庫ありのみで検索:**

```bash
agent-browser --session surugaya open "https://www.suruga-ya.jp/search?search_word={keyword}&inStock=On"
sleep 3
```

**重要**: `wait --load` は使用しない（analyticsでnetworkidleが成立しにくい）

---

### Step 2: 商品リスト抽出

**方法A: snapshotからテキスト判定**

```bash
agent-browser --session surugaya snapshot -c
# 出力例:
# heading "ランドネットディスク" [ref=e40]
# text "中古：￥13,800"                              ← 駿河屋直販価格
# text "マケプレ ￥6,080"
# link "(10点の中古品)" [ref=e82]                    ← マケプレ一覧へのリンク
#   /url: /product/other/147000347
```

**方法B: JavaScript eval で商品情報を一括取得**

```bash
# 駿河屋直販商品（/product/detail/へのリンク）
agent-browser --session surugaya eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"/product/detail/\"]'))
    .filter(a => !a.href.includes('tenpo_cd'))  // マケプレ個別リンクを除外
    .slice(0, 10)
    .map(a => ({
      url: a.href,
      title: a.textContent.trim().slice(0, 100),
      type: 'surugaya'
    }))
    .filter((v,i,a) => a.findIndex(t => t.url === v.url) === i)
)"

# マケプレ一覧リンク（(N点の中古品)、(N点の新品)）
agent-browser --session surugaya eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"/product/other/\"]'))
    .filter(a => a.textContent.match(/\\(\\d+点の/))
    .slice(0, 10)
    .map(a => ({
      url: a.href,
      text: a.textContent.trim(),
      type: 'marketplace_list'
    }))
)"
```

**価格抽出（駿河屋価格 + マケプレ価格）:**

```bash
agent-browser --session surugaya eval "
  const text = document.body.innerText;
  const surugayaMatch = text.match(/中古：￥([\\d,]+)/);
  const newMatch = text.match(/新品：￥([\\d,]+)/);
  const marketplaceMatch = text.match(/マケプレ\\s*￥([\\d,]+)/);
  const stockMatch = text.match(/\\((\\d+)点の(中古品|新品)\\)/);
  JSON.stringify({
    surugaya_used_price: surugayaMatch ? parseInt(surugayaMatch[1].replace(/,/g, '')) : null,
    surugaya_new_price: newMatch ? parseInt(newMatch[1].replace(/,/g, '')) : null,
    marketplace_price: marketplaceMatch ? parseInt(marketplaceMatch[1].replace(/,/g, '')) : null,
    marketplace_stock: stockMatch ? parseInt(stockMatch[1]) : 0,
    marketplace_type: stockMatch ? stockMatch[2] : null
  })
"
```

**価格フィルタリング（target_price設定時）**:
```
price > target_price → filtered_by_price++ → スキップ
```

---

### Step 3: 商品詳細ページへ遷移

**⚠️ clickコマンドは使用しない**（SPAでページ遷移しないことがあるため）

#### 遷移フロー判定

```
検索結果ページ
    │
    ├─「(N点の中古品)」「(N点の新品)」リンクがある
    │   └─→ /product/other/{商品ID} でマケプレ一覧へ（Step 3-A）
    │
    └─ リンクがない（駿河屋直販のみ）
        └─→ /product/detail/{商品ID} で商品詳細へ（Step 3-B）
```

#### Step 3-A: マケプレ一覧経由の遷移

**1. マケプレ一覧ページへ遷移:**

```bash
# (N点の中古品)リンクから取得したURLで遷移
agent-browser --session surugaya open "https://www.suruga-ya.jp/product/other/604064212"
sleep 3
```

**2. マケプレ一覧のコンテンツ確認:**

```bash
agent-browser --session surugaya snapshot -c
# 出力例（テーブル形式）:
# row "1,000円 新品通常 ゲームステーション本厚木店..."
#   cell "1,000円"
#   cell "新品通常":
#     link "新品通常" [ref=e82]
#       /url: /product/detail/604064212?tenpo_cd=400435&branch_number=9000
#   cell "ゲームステーション本厚木店..."
# row "1,430円 新品通常 ユニオンリバー..."
#   ...
```

**3. 個別商品への遷移（コンディションリンク経由）:**

```bash
# コンディション列のリンクURLを取得
agent-browser --session surugaya eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"tenpo_cd\"]'))
    .filter(a => a.textContent.match(/新品|中古|良い|可|通常/))
    .map(a => ({
      url: a.href,
      condition: a.textContent.trim()
    }))
)"

# 個別商品詳細ページへ遷移
agent-browser --session surugaya open "https://www.suruga-ya.jp/product/detail/604064212?tenpo_cd=400435&branch_number=9000"
sleep 3
```

#### Step 3-B: 駿河屋直販の遷移

```bash
# 商品タイトルリンクから直接遷移
agent-browser --session surugaya open "https://www.suruga-ya.jp/product/detail/602236211"
sleep 3
```

### マケプレ一覧ページの構造

| 列 | 内容 | 例 |
|----|------|-----|
| 価格 | 販売価格（税込） | 1,000円 |
| コンディション | 状態（**リンク先が個別商品**） | 新品通常、中古良い |
| 販売 | 店舗名・評価 | ゲームステーション本厚木店 5.0(482件) |
| 配送 | 発送期間 | 1日〜5日以内に発送 |

**コンディションのバリエーション:**
- 新品通常、新品未開封
- 中古良い、中古可、中古通常
- ワケアリ（訳あり品）

---

### Step 3.5: ジャンク品判定

**NGキーワード一覧**:
```
ジャンク, ジャンク品, 動作不良, 動作未確認, 故障, 壊れ, 破損, 不動, 部品取り, 現状品
```

**取得コマンド**:
```bash
agent-browser --session surugaya snapshot -c | grep -A 10 "商品説明"
```

**判定フロー**:
```
NGキーワード含む → skipped_by_junk++ → 次の商品へ
NGキーワードなし → Step 4へ
```

---

### Step 4: 全画像取得・リサイズ・Vision比較

**4-1: 全画像URLを取得**

```bash
agent-browser --session surugaya eval "JSON.stringify(
  Array.from(document.querySelectorAll('img'))
    .map(img => img.src)
    .filter(src => src.includes('suruga-ya.jp') && (src.includes('/photo/') || src.includes('/database/')))
    .filter(src => !src.includes('logo') && !src.includes('icon') && !src.includes('banner'))
    .filter((v,i,a) => a.indexOf(v) === i)
)"
```

**4-2: 各画像を処理**

```bash
# 画像1枚ごとに繰り返し
for each 画像URL:
  # 画像URLに直接アクセス
  agent-browser --session surugaya open "{画像URL}"

  # スクリーンショット
  agent-browser --session surugaya screenshot /tmp/surugaya_img_{N}.png

  # 長辺800px以上なら800pxにリサイズ
  sips -Z 800 /tmp/surugaya_img_{N}.png --out /tmp/surugaya_resized_{N}.png
```

**4-3: Vision比較**

```bash
# 全画像を読み込み
Read /tmp/surugaya_resized_1.png
Read /tmp/surugaya_resized_2.png
...

# 参照画像と比較してconfidence判定
```

**confidence判定基準**:

| レベル | 条件 |
|--------|------|
| **high** | 型番・形状・色が一致（本体の同一性確定） |
| **medium** | 主要特徴は一致するが確証不足 |
| **low** | 同シリーズだが別モデルの可能性 |

**accessory_status判定基準**:

| 値 | 条件 |
|----|------|
| **complete** | 付属品が完全一致 |
| **missing** | 付属品が不足（本体は同一モデル） |
| **unknown** | 判定不能（デフォルト値・後方互換） |

**notes評価（notes設定時）**:
notesに記載された条件に対する評価を `notes_evaluation` に記載

**4-4: 一時ファイル削除**

```bash
rm /tmp/surugaya_img_*.png /tmp/surugaya_resized_*.png
```

---

### Step 5: JSON返却

一致した商品の情報を**統一スキーマ**で返却。

```json
{
  "success": true,
  "source": "surugaya",
  "matches": [
    {
      "url": "https://www.suruga-ya.jp/product/detail/147000347",
      "price_value": 6080,
      "price_total": 6580,
      "shipping_included": false,
      "condition": "中古",
      "condition_group": "used",
      "confidence": "high",
      "accessory_status": "unknown",
      "seller_type": "marketplace"
    }
  ],
  "best_candidate": null,
  "checked_count": 2,
  "skipped_by_junk": 0,
  "filtered_by_price": 1,
  "error": null
}
```

**best_candidateの記載例**（条件未達だが同一商品がある場合）:
```json
{
  "success": true,
  "source": "surugaya",
  "matches": [],
  "best_candidate": {
    "url": "https://www.suruga-ya.jp/product/detail/147000347",
    "price_value": 13800,
    "price_total": 13800,
    "shipping_included": true,
    "condition": "中古",
    "condition_group": "used",
    "confidence": "high",
    "reason_code": "price_over",
    "accessory_status": "unknown",
    "seller_type": "surugaya"
  },
  "checked_count": 2,
  "skipped_by_junk": 0,
  "filtered_by_price": 2,
  "error": null
}
```

---

## エラーハンドリング

| エラー | 対応 | error値 |
|--------|------|---------|
| 参照画像なし | 即時終了 | "参照画像が見つかりません" |
| 検索結果0件 | 正常終了 | null（matches: []） |
| ジャンク品 | スキップ | null（skipped_by_junk++） |
| 価格超過 | スキップ | null（filtered_by_price++） |
| タイムアウト | リトライ3回 | "タイムアウト" |
| CAPTCHA | 処理中断 | "CAPTCHA検出により中断" |

---

## agent-browser リファレンス

### 基本コマンド

```bash
agent-browser --session surugaya open "https://..."
agent-browser --session surugaya snapshot -i    # インタラクティブ要素
agent-browser --session surugaya snapshot -c    # コンテンツ全体
agent-browser --session surugaya eval "JS式"    # JavaScript実行
agent-browser --session surugaya fill @ref "text"
agent-browser --session surugaya press Enter
agent-browser --session surugaya screenshot /path/to/file.png
```

### 待機方法

```bash
sleep 3  # 推奨（analyticsでnetworkidleが成立しにくい）
```

### ⚠️ clickでページ遷移しない問題

駿河屋もJavaScriptベースのため、`click @ref` でリンクをクリックしてもページ遷移しないことがある。

**解決方法: eval + open**

```bash
# URLを取得
agent-browser --session surugaya eval "Array.from(document.querySelectorAll('a[href*=\"/product/detail/\"]'))[0].href"

# 直接遷移
agent-browser --session surugaya open "{取得したURL}"
```

---

## 駿河屋特有の注意点

### 価格体系

1. **駿河屋直販価格**: 駿河屋が在庫を持つ商品の価格
2. **マケプレ価格**: マーケットプレイス出品者の価格（通常より安い）

```bash
# 価格取得
agent-browser --session surugaya eval "
  const text = document.body.innerText;
  return {
    surugaya: text.match(/中古：￥([\\d,]+)/)?.[1],
    marketplace: text.match(/マケプレ\\s*￥([\\d,]+)/)?.[1]
  };
"
```

### マーケットプレイス一覧

マケプレ商品が複数ある場合は `/product/other/{商品ID}` で一覧表示:

```bash
agent-browser --session surugaya open "https://www.suruga-ya.jp/product/other/147000347"
```

### 在庫確認

```bash
agent-browser --session surugaya eval "
  const text = document.body.innerText;
  const match = text.match(/\\((\\d+)点の中古品\\)/);
  return match ? parseInt(match[1]) : 0;
"
```

### 商品カテゴリ

駿河屋はカテゴリ別のURLパターンがある:
- ゲーム: `/product/detail/`
- 本: `/product-other/detail/`
- DVD/CD: `/product-other/detail/`

---

## 関連仕様

- メルカリ版: `.claude/agents/mercari-matcher.md`
- ラクマ版: `.claude/agents/rakuma-matcher.md`
- プラン: `.claude/plans/eager-wandering-adleman.md`
