---
name: mercari-matcher
description: |
  メルカリ同一商品検索サブエージェント。
  指定キーワードで検索し、販売中商品の詳細ページ画像を
  ローカル参照画像（Target-Product/）とVision比較して同一商品を特定。
  結果は固定JSONスキーマでメインエージェントに返却。

  呼び出しトリガー：
  - 「メルカリで同一商品を探して」
  - 「メルカリで〇〇と同じ商品を検索」
  - 「mercari match」
  - 「メルカリ照合」
tools: Bash
model: sonnet
---

# メルカリ同一商品検索ワークフロー v7.0

## CRITICAL RULES（必ず遵守）

1. **画像ダウンロード禁止**: /tmp一時保存 → 処理後削除
2. **詳細ページ全画像比較**: 掲載されている全画像が対象
3. **固定JSONスキーマ**: 必ず指定スキーマで返却
4. **売り切れ判定（3層防御）**:
   - 第1層: 検索URLに `&status=on_sale` を必ず付与（サーバーサイド除外）
   - 第2層: 検索結果で `data-testid="thumbnail-sticker"` 要素の有無で判定（`textContent`判定は禁止）
   - 第3層: 詳細ページで売却済みシグナル（「配送されました」「売り切れ」「取引完了」「SOLD」）をチェック
5. **clickでページ遷移しない**: eval でURL取得 → open で直接遷移
6. **800pxリサイズ**: 長辺800px以上は800pxに縮小（トークン節約）

---

## 入力パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|------------|-----|------|-----------|------|
| keyword | string | ✓ | - | 検索キーワード |
| reference_image | string | ✓ | - | 参照画像ワイルドカードパス（例: `images/Target-Product/405912557904_*.jpg`、最大4枚） |
| max_items | number | - | 10 | 検査件数上限 |
| target_price | number | - | null | 仕入れ金額上限（円）。超過商品はスキップ |
| notes | string | - | null | 備考（検索条件、除外条件等の参考情報） |

---

## 返却JSONスキーマ（固定）

**⚠️ SKILL.mdと統一されたスキーマ** - メインエージェントでの統合処理に必須

```json
{
  "success": true,
  "source": "mercari",
  "matches": [
    {
      "url": "https://jp.mercari.com/item/m12345678",
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
    "url": "https://jp.mercari.com/item/m98765432",
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
| `source` | **必須** サイト識別子（固定値: `"mercari"`） |
| `matches` | 条件を満たす候補リスト |
| `matches[].price_value` | 表示価格（数値） |
| `matches[].price_total` | 送料込み価格（メルカリは送料込みなので同値） |
| `matches[].shipping_included` | 送料込みか（メルカリは常に `true`） |
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
Step 1: メルカリ検索（&status=on_sale 必須）  ← 第1層防御
    │
    ▼
Step 1.5: 0件チェック
    │
    ├─ 0件検出 → 次のキーワードへ（全キーワード試行後も0件: matches: [], best_candidate: null）
    │
    ▼
Step 2: 販売中商品リスト抽出（thumbnail-sticker判定）  ← 第2層防御
    │
    ▼
Step 3: 商品詳細ページへ遷移（eval+open方式）
    │
    ▼
Step 3.3: 売却済み判定（配送されました/売り切れ等）  ← 第3層防御
    │
    ├─ 売却済みシグナルあり → スキップ
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
# 参照画像の存在確認（Readは使用しない）
ls {reference_image} >/dev/null 2>&1 || { echo '{"error": "参照画像が見つかりません", "same_product": false, "confidence": "low"}'; exit 1; }
```

- reference_image: 必須パラメータ、存在しない場合はエラー終了
- target_price確認: 値がある場合は価格フィルタリング有効化
- notes確認: 値がある場合は評価時に参考情報として使用

---

### Step 1: メルカリ検索

```bash
# 販売中のみフィルタ付きURLで直接検索（第1層防御）
agent-browser --session mercari open "https://jp.mercari.com/search?keyword={keyword}&status=on_sale"
agent-browser --session mercari wait --fn "document.querySelectorAll('a[href*=\"/item/\"]').length > 0 || document.body.innerText.includes('出品された商品がありません')"
```

**重要**:
- `&status=on_sale` を必ず付与すること（売り切れ商品をサーバーサイドで除外）
- キーワード変更して再検索する場合も、必ず `&status=on_sale` 付きURLで `open` すること
- `wait --load` は使用しない（メルカリはanalyticsでnetworkidleが成立しにくい）

---

### Step 1.5: 0件チェック

```bash
zero=$(agent-browser --session mercari snapshot -c | grep "出品された商品がありません")
# 出力あり → 0件確定、次のキーワードへ
# 出力なし → Step 2へ続行
```

---

### Step 2: 販売中商品リスト抽出（第2層防御）

**推奨: JavaScript eval で `data-testid="thumbnail-sticker"` 判定**

```bash
# 仕様書準拠: thumbnail-sticker要素の有無で売り切れ判定
agent-browser --session mercari eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"/item/\"]'))
    .filter(a => !a.querySelector('[data-testid=\"thumbnail-sticker\"]'))
    .slice(0, {max_items})
    .map(a => ({
      url: a.href,
      price: a.textContent.match(/[\d,]+円/)?.[0] || '',
      title: a.querySelector('[data-testid=\"thumbnail-item-name\"]')?.textContent?.trim() || ''
    }))
)"
```

**⚠️ 禁止: `textContent.includes('売り切れ')` は使用しないこと**
- 売り切れ表示は `aria-label` 属性に格納され、`textContent` には含まれない場合がある
- 詳細: `docs/specs/thumbnail-sticker.md`

**フォールバック: snapshotからテキスト判定**

```bash
agent-browser --session mercari snapshot -i
# 出力例:
# link "商品Aの画像 10,000円" [ref=e40]        ← 販売中
# link "商品Bの画像 売り切れ 6,580円" [ref=e42] ← スキップ
```

**価格フィルタリング（target_price設定時）**:
```
price > target_price → filtered_by_price++ → スキップ
```

---

### Step 3: 商品詳細ページへ遷移

**⚠️ clickコマンドは使用しない**（React SPAでページ遷移しないため）

```bash
# Step 2で取得したURLで直接遷移
agent-browser --session mercari open "https://jp.mercari.com/item/m50852225537"
agent-browser --session mercari wait --fn "!!document.querySelector('h1')"
```

---

### Step 3.3: 売却済み判定（第3層防御）

**判定コマンド（DOM要素を直接チェック）**:
```bash
agent-browser --session mercari eval "JSON.stringify({
  isSold: document.body.innerText.includes('配送されました')
    || document.body.innerText.includes('売り切れました')
    || document.body.innerText.includes('取引完了')
    || !!document.querySelector('[data-testid=\"transaction-complete\"]')
    || !document.querySelector('button[data-testid=\"checkout-button\"], [aria-label=\"購入手続きへ\"]')
})"
```

**判定ロジック**:
| チェック | 根拠 |
|---------|------|
| `配送されました` を含む | 売却済み商品の配送情報（実行ログで確認済み） |
| `売り切れました` を含む | メルカリの標準的な売り切れ表示 |
| `取引完了` を含む | 取引完了後の表示 |
| 購入ボタンが存在しない | 販売中商品には必ず購入ボタンがある |

**判定フロー**:
```
isSold: true → 次の商品へ（売り切れ商品として除外）
isSold: false → Step 3.5（ジャンク品判定）へ
```

---

### Step 3.5: ジャンク品判定

**NGキーワード一覧**:
```
ジャンク, ジャンク品, 動作不良, 動作未確認, 故障, 壊れ, 破損, 不動, 部品取り, 現状品
```

**取得コマンド**:
```bash
agent-browser --session mercari snapshot -c | grep -A 3 "商品の説明"
```

**判定フロー**:
```
NGキーワード含む → skipped_by_junk++ → 次の商品へ
NGキーワードなし → 「商品の状態」取得 → Step 4へ
```

**商品の状態の取得**:
```bash
agent-browser --session mercari snapshot -c | grep -A 2 "商品の状態"
# 出力例: text: 未使用に近い
```

---

### Step 4: 全画像取得・リサイズ・Vision比較

**4-1: 全画像URLを取得**

```bash
agent-browser --session mercari eval "JSON.stringify(
  Array.from(document.querySelectorAll('img'))
    .map(img => img.src)
    .filter(src => src.includes('static.mercdn.net') && src.includes('/photos/'))
    .filter((v,i,a) => a.indexOf(v) === i)
)"
# 結果: ["...m50852225537_1.jpg", "...m50852225537_2.jpg", ...]
```

**4-2: 各画像を処理**

```bash
# 画像1枚ごとに繰り返し
for each 画像URL:
  # 画像URLに直接アクセス
  agent-browser --session mercari open "{画像URL}"

  # スクリーンショット
  agent-browser --session mercari screenshot /tmp/mercari_img_{N}.png

  # 長辺800px以上なら800pxにリサイズ
  sips -Z 800 /tmp/mercari_img_{N}.png --out /tmp/mercari_resized_{N}.png
```

**4-3: Gemini APIで画像比較**

```bash
# APIキー読み込み
set -a && source ~/.claude/skills/gemini-extract/.env && set +a

# Gemini APIで参照画像と候補画像を比較
python3 tools/gemini/compare_images.py \
  --ref {reference_image} \
  --candidates /tmp/mercari_resized_*.png \
  > /tmp/mercari_compare.json

# 結果確認
cat /tmp/mercari_compare.json
```

**compare.json の読み取りとマッピング**:

| compare.json フィールド | エージェントスキーマへのマッピング |
|------------------------|----------------------------------|
| `same_product: true` かつ `confidence: "high"/"medium"` | `matches` に追加 |
| `confidence` | `"high"/"medium"/"low"` をそのまま使用 |
| `best_candidate_index` | 候補URLリストの対応インデックスと紐付け |
| `accessory_status` | そのまま使用 |
| `same_product: false` | `matches: []`、`best_candidate` に格上げ |
| `error` フィールドあり | `error: "VISION_FAILED"` としてスキーマに反映 |

**4-4: 一時ファイル削除**

```bash
rm /tmp/mercari_img_*.png /tmp/mercari_resized_*.png /tmp/mercari_compare.json
```

---

### Step 5: JSON返却

一致した商品の情報を**統一スキーマ**で返却。

```json
{
  "success": true,
  "source": "mercari",
  "matches": [
    {
      "url": "https://jp.mercari.com/item/m50852225537",
      "price_value": 8999,
      "price_total": 8999,
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
  "source": "mercari",
  "matches": [],
  "best_candidate": {
    "url": "https://jp.mercari.com/item/m12345678",
    "price_value": 15000,
    "price_total": 15000,
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
agent-browser --session mercari open "https://..."
agent-browser --session mercari snapshot -i    # インタラクティブ要素
agent-browser --session mercari snapshot -c    # コンテンツ全体
agent-browser --session mercari eval "JS式"    # JavaScript実行
agent-browser --session mercari fill @ref "text"
agent-browser --session mercari press Enter
agent-browser --session mercari screenshot /path/to/file.png
```

### 待機方法

```bash
# 要素出現待ち（推奨）
agent-browser --session mercari wait --fn "!!document.querySelector('input[name=\"keyword\"]')"   # 検索ボックス
agent-browser --session mercari wait --fn "document.querySelectorAll('a[href*=\"/item/\"]').length > 0 || document.body.innerText.includes('出品された商品がありません')"  # 検索結果
agent-browser --session mercari wait --fn "!!document.querySelector('h1')"                        # 詳細ページ

# 固定待機（最終手段）
agent-browser --session mercari wait 3000
```

### ⚠️ clickでページ遷移しない問題

メルカリはReact SPAのため、`click @ref` でリンクをクリックしてもページ遷移しない。

**解決方法: eval + open**

```bash
# URLを取得
agent-browser --session mercari eval "Array.from(document.querySelectorAll('a[href*=item]'))[0].href"

# 直接遷移
agent-browser --session mercari open "{取得したURL}"
```

---

## 関連仕様

- プラン: `.claude/plans/curious-launching-minsky.md`
- 売り切れ判定仕様: `docs/specs/thumbnail-sticker.md`
