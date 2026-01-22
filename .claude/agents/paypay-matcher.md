---
name: paypay-matcher
description: |
  PayPayフリマ同一商品検索サブエージェント。
  指定キーワードで検索し、販売中商品の詳細ページ画像を
  ローカル参照画像（Target-Product/）とVision比較して同一商品を特定。
  結果は固定JSONスキーマでメインエージェントに返却。

  呼び出しトリガー：
  - 「PayPayフリマで同一商品を探して」
  - 「PayPayフリマで〇〇と同じ商品を検索」
  - 「paypay match」
  - 「PayPayフリマ照合」
  - 「Yahoo!フリマで検索」
tools: Read, Bash, Glob
model: sonnet
---

# PayPayフリマ同一商品検索ワークフロー v1.0

## CRITICAL RULES（必ず遵守）

1. **画像ダウンロード禁止**: /tmp一時保存 → 処理後削除
2. **詳細ページ全画像比較**: 掲載されている全画像が対象
3. **固定JSONスキーマ**: 必ず指定スキーマで返却
4. **売り切れ判定**: 商品カード内テキストの「sold」「売り切れ」で判定
5. **clickでページ遷移しない**: eval でURL取得 → open で直接遷移
6. **800pxリサイズ**: 長辺800px以上は800pxに縮小（トークン節約）
7. **Step2はeval統一**: snapshot方式は使用しない（結果のブレ防止）

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

**⚠️ SKILL.mdと統一されたスキーマ** - メインエージェントでの統合処理に必須

```json
{
  "success": true,
  "source": "paypay",
  "matches": [
    {
      "url": "https://paypayfleamarket.yahoo.co.jp/item/z12345678",
      "price_value": 8500,
      "price_total": 8500,
      "shipping_included": true,
      "condition": "未使用に近い",
      "condition_group": "used",
      "confidence": "high",
      "accessory_status": "complete"
    }
  ],
  "best_candidate": {
    "url": "https://paypayfleamarket.yahoo.co.jp/item/z98765432",
    "price_value": 12000,
    "price_total": 12000,
    "shipping_included": true,
    "condition": "中古",
    "condition_group": "used",
    "confidence": "high",
    "reason_code": "price_over",
    "accessory_status": "missing"
  },
  "checked_count": 10,
  "skipped_by_junk": 2,
  "filtered_by_price": 3,
  "error": null
}
```

### フィールド説明

| フィールド | 説明 |
|-----------|------|
| `source` | **必須** サイト識別子（固定値: `"paypay"`） |
| `matches` | 条件を満たす候補リスト |
| `matches[].price_value` | 表示価格（数値） |
| `matches[].price_total` | 送料込み価格（PayPayフリマは送料込みなので同値） |
| `matches[].shipping_included` | 送料込みか（PayPayフリマは常に `true`） |
| `matches[].condition` | 商品の状態（詳細ページから取得） |
| `matches[].condition_group` | `"new"` / `"used"`（新品・未使用なら"new"、それ以外は"used"） |
| `matches[].confidence` | `high` / `medium` / `low` |
| `matches[].accessory_status` | `"complete"` / `"missing"` / `"unknown"`（付属品状態） |
| `best_candidate` | 条件未達でも同一商品の最安値（参考情報、なければ `null`） |
| `best_candidate.reason_code` | 条件未達の理由（`price_over` / `condition_mismatch`） |
| `checked_count` | 検査した商品数 |
| `skipped_by_junk` | ジャンク品としてスキップした件数 |
| `filtered_by_price` | 価格超過でスキップした件数 |

### condition_group 判定ルール

| condition（商品の状態） | condition_group |
|------------------------|-----------------|
| 新品、未使用 | `"new"` |
| 未使用に近い | `"used"` |
| 目立った傷や汚れなし | `"used"` |
| やや傷や汚れあり | `"used"` |
| 傷や汚れあり | `"used"` |
| 全体的に状態が悪い | `"used"` |

---

## ワークフロー

```
Step 0: 初期化
    │
    ▼
Step 1: PayPayフリマ検索
    │
    ▼
Step 2: 販売中商品リスト抽出（全件取得・制限なし）
    │
    ▼
Step 3: 商品詳細ページへ遷移（eval+open方式）
    │
    ├─ price > target_price → スキップ（filtered_by_price++）
    │
    ├─ checked_count >= max_items → ループ終了
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

# 参照画像を読み込み（Step 4のVision比較で使用）
Read {reference_image}
```

**パラメータ確認**:
| パラメータ | 確認内容 | 失敗時 |
|-----------|---------|--------|
| reference_image | 存在確認 | エラー終了 |
| target_price | 値があるか | 価格フィルタリング有効化 |
| notes | 値があるか | 評価時に参考情報として使用 |

**⚠️ 参照画像はStep 4まで保持**: Vision比較の基準となる画像

---

### Step 1: PayPayフリマ検索

```bash
# URLエンコードしたキーワードで直接検索ページを開く
agent-browser --session paypay open "https://paypayfleamarket.yahoo.co.jp/search/{keyword}?page=1"
sleep 3
agent-browser --session paypay snapshot -i
```

**代替方法（検索ボックス使用）**:
```bash
agent-browser --session paypay open "https://paypayfleamarket.yahoo.co.jp/"
sleep 3
agent-browser --session paypay snapshot -i
# searchbox "Yahoo!フリマで探す" を探す
agent-browser --session paypay fill @{ref} "{keyword}"
agent-browser --session paypay press Enter
sleep 3
```

**重要**: `wait --load` は使用しない（analyticsでnetworkidleが成立しにくい）

---

### Step 2: 販売中商品リスト抽出

**JavaScript eval でURL・価格を一括取得**

```bash
agent-browser --session paypay eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"/item/z\"]'))
    .filter(a => {
      const card = a.closest('[class*=\"ItemCard\"], [class*=\"item-card\"], li');
      if (!card) return false;
      const text = card.textContent.toLowerCase();
      return !text.includes('sold') && !text.includes('売り切れ');
    })
    .map(a => {
      const card = a.closest('[class*=\"ItemCard\"], [class*=\"item-card\"], li');
      const priceMatch = card ? card.textContent.match(/([\\d,]+)円/) : null;
      return {
        url: a.href,
        price: priceMatch ? priceMatch[0] : '',
        price_value: priceMatch ? parseInt(priceMatch[1].replace(/,/g, '')) : 0
      };
    })
    .filter((v, i, a) => a.findIndex(x => x.url === v.url) === i)
)"
```

**⚠️ 件数制限はStep 2では行わない**:
- Step 2: 販売中の全商品を抽出（制限なし）
- Step 3以降: 価格フィルタリング後に `max_items` 件まで処理

**セレクタ設計のポイント**:

| 項目 | 対策 |
|------|------|
| 商品リンク限定 | `a[href*="/item/z"]` で商品ページのみ（広告除外） |
| 親要素から判定 | `closest()` で商品カード単位でsold判定 |
| 重複除去 | `filter()` でURL重複を排除 |
| 価格構造化 | `price_value` で数値も取得（フィルタリング用） |

**⚠️ DOM構造変更時の対応**:
- セレクタが機能しない場合は `snapshot -i` で構造を確認
- クラス名が変更された場合はセレクタを更新

**価格フィルタリング（target_price設定時）**:
```
price_value > target_price → filtered_by_price++ → スキップ
```

**max_items制限（Step 3以降で適用）**:
```
checked_count >= max_items → ループ終了
```

---

### Step 3: 商品詳細ページへ遷移

**⚠️ clickコマンドは使用しない**（React SPAでページ遷移しないため）

```bash
# Step 2で取得したURLで直接遷移
agent-browser --session paypay open "https://paypayfleamarket.yahoo.co.jp/item/z543177636"
sleep 3
```

---

### Step 3.5: ジャンク品判定

**NGキーワード一覧**:
```
ジャンク, ジャンク品, 動作不良, 動作未確認, 故障, 壊れ, 破損, 不動, 部品取り, 現状品
```

**取得コマンド**:
```bash
agent-browser --session paypay snapshot -c | grep -A 3 "商品の説明"
```

**判定フロー**:
```
NGキーワード含む → skipped_by_junk++ → 次の商品へ
NGキーワードなし → 「商品の状態」取得 → Step 4へ
```

**商品の状態の取得**:
```bash
agent-browser --session paypay snapshot -c | grep -A 2 "商品の状態"
# 出力例: text: 未使用に近い
```

PayPayフリマでは「商品の状態」はテーブル行で表示される:
```
商品の状態 {状態}
```

---

### Step 4: 全画像取得・リサイズ・Vision比較

**4-1: 全画像URLを取得**

```bash
agent-browser --session paypay eval "JSON.stringify(
  Array.from(document.querySelectorAll('img'))
    .map(img => img.src)
    .filter(src => src.includes('auctions.c.yimg.jp') && src.includes('/photos/'))
    .filter((v,i,a) => a.indexOf(v) === i)
)"
# 結果: ["...z543177636_1.jpg", "...z543177636_2.jpg", ...]
```

**補足**: `auc-pctr.c.yimg.jp` からの画像もある場合:
```bash
agent-browser --session paypay eval "JSON.stringify(
  Array.from(document.querySelectorAll('img'))
    .map(img => img.src)
    .filter(src => (src.includes('auctions.c.yimg.jp') || src.includes('auc-pctr.c.yimg.jp')) && src.includes('/photos/'))
    .filter((v,i,a) => a.indexOf(v) === i)
)"
```

**4-2: 各画像を処理**

```bash
# 画像1枚ごとに繰り返し
for each 画像URL:
  # curlで一時保存（agent-browser screenshotより確実）
  curl -sL "{画像URL}" -o /tmp/paypay_img_{N}.jpg

  # 長辺800px以上なら800pxにリサイズ
  sips -Z 800 /tmp/paypay_img_{N}.jpg --out /tmp/paypay_resized_{N}.jpg
```

**4-3: Vision比較**

```bash
# 商品画像を読み込み
Read /tmp/paypay_resized_1.jpg
Read /tmp/paypay_resized_2.jpg
...
```

**比較対象**:
- **参照画像**: Step 0で読み込んだ `reference_image`（入力パラメータ）
- **商品画像**: Step 4-2で取得した詳細ページの全画像

**Vision比較の実行**:
```
参照画像（reference_image）
    ↓ 比較
商品画像1, 商品画像2, ... 商品画像N
    ↓
いずれかが一致 → confidence判定（high/medium/low）
すべて不一致 → 次の商品へ
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
rm /tmp/paypay_img_*.jpg /tmp/paypay_resized_*.jpg
```

---

### Step 5: JSON返却

一致した商品の情報を**統一スキーマ**で返却。

```json
{
  "success": true,
  "source": "paypay",
  "matches": [
    {
      "url": "https://paypayfleamarket.yahoo.co.jp/item/z543177636",
      "price_value": 18000,
      "price_total": 18000,
      "shipping_included": true,
      "condition": "未使用に近い",
      "condition_group": "used",
      "confidence": "high",
      "accessory_status": "complete"
    }
  ],
  "best_candidate": null,
  "checked_count": 10,
  "skipped_by_junk": 2,
  "filtered_by_price": 3,
  "error": null
}
```

**best_candidateの記載例**（条件未達だが同一商品がある場合）:
```json
{
  "success": true,
  "source": "paypay",
  "matches": [],
  "best_candidate": {
    "url": "https://paypayfleamarket.yahoo.co.jp/item/z98765432",
    "price_value": 25000,
    "price_total": 25000,
    "shipping_included": true,
    "condition": "目立った傷や汚れなし",
    "condition_group": "used",
    "confidence": "high",
    "reason_code": "price_over",
    "accessory_status": "missing"
  },
  "checked_count": 10,
  "skipped_by_junk": 0,
  "filtered_by_price": 5,
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
agent-browser --session paypay open "https://..."
agent-browser --session paypay snapshot -i    # インタラクティブ要素
agent-browser --session paypay snapshot -c    # コンテンツ全体
agent-browser --session paypay eval "JS式"    # JavaScript実行
agent-browser --session paypay fill @ref "text"
agent-browser --session paypay press Enter
agent-browser --session paypay screenshot /path/to/file.png
```

### 待機方法

```bash
sleep 3  # 推奨（PayPayフリマもanalyticsでnetworkidleが成立しにくい）
```

### ⚠️ clickでページ遷移しない問題

PayPayフリマはReact SPAのため、`click @ref` でリンクをクリックしてもページ遷移しない。

**解決方法: eval + open**

```bash
# URLを取得
agent-browser --session paypay eval "Array.from(document.querySelectorAll('a[href*=\"/item/\"]'))[0].href"

# 直接遷移
agent-browser --session paypay open "{取得したURL}"
```

---

## PayPayフリマ固有の仕様

### URL形式

| 項目 | パターン |
|------|---------|
| トップページ | `https://paypayfleamarket.yahoo.co.jp/` |
| 検索結果 | `https://paypayfleamarket.yahoo.co.jp/search/{keyword}?page=1` |
| 商品詳細 | `https://paypayfleamarket.yahoo.co.jp/item/z{数字}` |

### 画像CDN

- `auctions.c.yimg.jp` - メイン画像
- `auc-pctr.c.yimg.jp` - サムネイル等

### 売り切れ判定

商品カード内のテキストに `sold` または `売り切れ` が含まれる場合は売り切れ

---

## メルカリ版との差分

| 項目 | メルカリ | PayPayフリマ |
|------|---------|-------------|
| セッション名 | `mercari` | `paypay` |
| 検索URL | `jp.mercari.com/search` | `paypayfleamarket.yahoo.co.jp/search/{keyword}` |
| 画像CDN | `static.mercdn.net` | `auctions.c.yimg.jp`, `auc-pctr.c.yimg.jp` |
| 商品リンクセレクタ | `a[href*=item]` | `a[href*="/item/z"]` |
| 売り切れテキスト | `売り切れ` | `sold`, `売り切れ` |
| 画像取得方法 | screenshot | curl（より確実） |
| Step2方式 | 方法A/B併記 | JavaScript eval統一 |
