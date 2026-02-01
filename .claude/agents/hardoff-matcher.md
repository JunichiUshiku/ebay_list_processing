---
name: hardoff-matcher
description: |
  ハードオフ（オフモール）同一商品検索サブエージェント。
  指定キーワードで検索し、販売中商品の詳細ページ画像を
  ローカル参照画像（Target-Product/）とVision比較して同一商品を特定。
  結果は固定JSONスキーマでメインエージェントに返却。

  呼び出しトリガー：
  - 「ハードオフで同一商品を探して」
  - 「ハードオフで〇〇と同じ商品を検索」
  - 「hardoff match」
  - 「オフモール照合」
tools: Read, Bash, Glob
model: sonnet
---

# ハードオフ同一商品検索ワークフロー v1.0

## CRITICAL RULES（必ず遵守）

1. **画像ダウンロード禁止**: /tmp一時保存 → 処理後削除
2. **詳細ページ全画像比較**: 掲載されている全画像が対象
3. **固定JSONスキーマ**: 必ず指定スキーマで返却
4. **ジャンク品判定**: リンクテキスト・ハッシュタグの「ジャンク」で判定
5. **clickでページ遷移しない**: eval でURL取得 → open で直接遷移
6. **800pxリサイズ**: 長辺800px以上は800pxに縮小（トークン節約）

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
  "source": "hardoff",
  "matches": [
    {
      "url": "https://netmall.hardoff.co.jp/product/12345/",
      "price_value": 8500,
      "price_total": 8500,
      "shipping_included": false,
      "condition": "B",
      "condition_group": "used",
      "confidence": "high",
      "accessory_status": "complete"
    }
  ],
  "best_candidate": {
    "url": "https://netmall.hardoff.co.jp/product/67890/",
    "price_value": 12000,
    "price_total": 12000,
    "shipping_included": false,
    "condition": "B",
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
| `source` | **必須** サイト識別子（固定値: `"hardoff"`） |
| `matches` | 条件を満たす候補リスト |
| `matches[].price_value` | 表示価格（数値） |
| `matches[].price_total` | 送料込み価格（ハードオフは送料別のため別途計算が必要） |
| `matches[].shipping_included` | 送料込みか（ハードオフは常に `false`） |
| `matches[].condition` | 商品ランク（A/B/C/S/N等）|
| `matches[].condition_group` | `"new"` / `"used"`（N=new、それ以外はused） |
| `matches[].confidence` | `high` / `medium` / `low` |
| `matches[].accessory_status` | `"complete"` / `"missing"` / `"unknown"`（付属品状態） |
| `best_candidate` | 条件未達でも同一商品の最安値（参考情報、なければ `null`） |
| `best_candidate.reason_code` | 条件未達の理由（`price_over` / `condition_mismatch`） |
| `checked_count` | 検査した商品数 |
| `skipped_by_junk` | ジャンク品としてスキップした件数 |
| `filtered_by_price` | 価格超過でスキップした件数 |

### condition_group 判定ルール

| condition（商品ランク） | condition_group |
|------------------------|-----------------|
| N（新品） | `"new"` |
| S（未使用品） | `"new"` |
| A/B/C | `"used"` |
| ジャンク | スキップ対象 |

---

## ワークフロー

```
Step 0: 初期化
    │
    ▼
Step 1: ハードオフ検索
    │
    ▼
Step 2: 価格フィルター適用（target_price設定時）
    │
    ▼
Step 3: 販売中商品リスト抽出
    │
    ├─ ジャンク品 → スキップ（skipped_by_junk++）
    │
    ▼
Step 4: 商品詳細ページへ遷移（eval+open方式）
    │
    ▼
Step 5: 全画像取得・リサイズ・Vision比較
    │
    ▼
Step 6: JSON返却
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

### Step 1: ハードオフ検索

```bash
agent-browser --session hardoff open "https://netmall.hardoff.co.jp/"
sleep 3
agent-browser --session hardoff snapshot -i
agent-browser --session hardoff fill @e5 "{keyword}"
agent-browser --session hardoff press Enter
sleep 3
```

**重要**:
- 検索ボックスは `textbox "全国の1点ものを探そう"` で特定
- 検索結果URL形式: `/search/?q={keyword}&s=7`

---

### Step 2: 価格フィルター適用（target_price設定時）

```bash
agent-browser --session hardoff snapshot -i
# 価格ボタンをクリック（通常 "価格" というテキストで特定）
agent-browser --session hardoff click @価格ボタンref
sleep 1

agent-browser --session hardoff snapshot -i
# 上限入力フィールドに価格を入力（textbox "上限なし"）
agent-browser --session hardoff fill @上限入力ref "{target_price}"
# 検索するボタンをクリック
agent-browser --session hardoff click @検索ボタンref
sleep 3
```

**フィルター後URL形式**: `/search/?q={keyword}&s=7&p=-{max_price}`

---

### Step 3: 販売中商品リスト抽出

**JavaScript eval でURL・価格・ジャンク判定を一括取得**

```bash
agent-browser --session hardoff eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"/product/\"]'))
    .slice(0, 10)
    .map(a => ({
      url: a.href,
      text: a.textContent,
      isJunk: a.textContent.includes('ジャンク')
    }))
)"
```

**ジャンク品判定**:
```
isJunk === true → skipped_by_junk++ → スキップ
```

---

### Step 4: 商品詳細ページへ遷移

**⚠️ clickコマンドは使用しない**

```bash
# Step 3で取得したURLで直接遷移
agent-browser --session hardoff open "https://netmall.hardoff.co.jp/product/5100444/"
sleep 3
```

---

### Step 4.5: 詳細ページ情報取得

**価格・ランク・ジャンク判定を取得**:

```bash
agent-browser --session hardoff snapshot -c | grep -E "(円|ジャンク|商品ランク|#)"
```

**ジャンク品の再確認**（ハッシュタグ判定）:
```bash
agent-browser --session hardoff eval "JSON.stringify(
  Array.from(document.querySelectorAll('a[href*=\"/hashtag/\"]'))
    .map(a => a.textContent)
)"
# 結果例: ["#楽器", "#JUNK品", "#ジャンク", "#YAMAHA", ...]
```

NGハッシュタグ: `#ジャンク`, `#ジャンク品`, `#JUNK品`, `#JUNK手前`

---

### Step 5: 全画像取得・リサイズ・Vision比較

**5-1: 全画像URLを取得**

```bash
agent-browser --session hardoff eval "JSON.stringify(
  Array.from(document.querySelectorAll('button img'))
    .filter(i => i.src.includes('imageflux.jp'))
    .map(i => i.src)
)"
# 結果: ["https://p1-d9ebd2ee.imageflux.jp/c!/w=1280,h=1280,.../101056/abc123.jpg", ...]
```

**5-2: 各画像を処理**

```bash
# 画像1枚ごとに繰り返し
for each 画像URL:
  # 画像URLに直接アクセス
  agent-browser --session hardoff open "{画像URL}"

  # スクリーンショット
  agent-browser --session hardoff screenshot /tmp/hardoff_img_{N}.png

  # 長辺800px以上なら800pxにリサイズ
  sips -Z 800 /tmp/hardoff_img_{N}.png --out /tmp/hardoff_resized_{N}.png
```

**5-3: Vision比較**

```bash
# 全画像を読み込み
Read /tmp/hardoff_resized_1.png
Read /tmp/hardoff_resized_2.png
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
| **unknown** | 判定不能（デフォルト値） |

**5-4: 一時ファイル削除**

```bash
rm /tmp/hardoff_img_*.png /tmp/hardoff_resized_*.png
```

---

### Step 6: JSON返却

一致した商品の情報を**統一スキーマ**で返却。

```json
{
  "success": true,
  "source": "hardoff",
  "matches": [
    {
      "url": "https://netmall.hardoff.co.jp/product/5100444/",
      "price_value": 35200,
      "price_total": 35200,
      "shipping_included": false,
      "condition": "ジャンク",
      "condition_group": "used",
      "confidence": "high",
      "accessory_status": "unknown"
    }
  ],
  "best_candidate": null,
  "checked_count": 3,
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
agent-browser --session hardoff open "https://..."
agent-browser --session hardoff snapshot -i    # インタラクティブ要素
agent-browser --session hardoff snapshot -c    # コンテンツ全体
agent-browser --session hardoff eval "JS式"    # JavaScript実行
agent-browser --session hardoff fill @ref "text"
agent-browser --session hardoff press Enter
agent-browser --session hardoff click @ref
agent-browser --session hardoff screenshot /path/to/file.png
```

### 待機方法

```bash
sleep 3  # 推奨
```

---

## ハードオフ固有の注意点

### 送料について

- ハードオフは**送料別**（shipping_included: false）
- 送料は配送先都道府県により異なる
- 詳細は各商品ページの「送料について詳しくはこちら」リンク参照

### 商品ランク表記

| 表記 | 意味 |
|------|------|
| n / N | 新品 |
| s / S | 未使用品 |
| a / A | 状態良好 |
| b / B | 使用感あり |
| c / C | 難あり |
| ジャンク品 | 動作未保証 |

### 画像URLの構造

```
https://p1-d9ebd2ee.imageflux.jp/c!/w=1280,h=1280,a=0,u=1,q=75/{store_id}/{image_hash}.jpg
```

- `store_id`: 店舗ID（例: 101056）
- `image_hash`: 画像ハッシュ

---

## 関連仕様

- プラン: `.claude/plans/inherited-pondering-taco.md`
- 参考: `.claude/agents/mercari-matcher.md`
