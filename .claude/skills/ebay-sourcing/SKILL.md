---
name: ebay-sourcing
description: eBay販売商品の国内仕入れ先を探すワークフロー。メルカリ・ヤフオク・PayPayフリマ・ラクマ・ハードオフ・駿河屋など国内11サイトで同一商品を検索し、希望価格・コンディション条件に合う仕入れ先を見つけてスプレッドシートのU列にURLを記録する。「仕入れ先を探して」「国内で仕入れ」「在庫仕入れ」「メルカリ/ヤフオクで同じ商品を探して」、eBayアイテムナンバー指定の仕入れ依頼、「スプレッドシートの商品を国内で探して」「U列が空の行を処理して」「ebay-sourcingを実行して」などの指示で必ず使うこと。
---

# eBay在庫仕入れ処理

## 必須ルール

- **11サイト全て**を検索対象とする
- eBay商品と**同一品**であることを画像・タイトルで確認
- **価格条件・コンディション条件**を厳守
- **データ取得制約**: 必要最小限の列のみ取得（`range: B2:C` のように特定列のみ）

---

## 参照ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [reference/sites.md](reference/sites.md) | 11サイトの検索URL・セレクター |
| [reference/ebay-selectors.md](reference/ebay-selectors.md) | eBayページのセレクター詳細 |
| [reference/conditions.md](reference/conditions.md) | 仕入れ判断ルール（価格・コンディション） |

---

## スプレッドシート定義

**Spreadsheet ID**: `1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g`
**Sheet名**: `AI作業用`

### 入力列

| 列 | 内容 | 用途 |
|----|------|------|
| B | 商品名 | 検索キーワード |
| C | eBay Item Number | eBayページ確認 |
| F | 仕入価格（円） | 空/0→スキップ |
| P | コンディション | 新品/中古判定 |

### 出力列

| 列 | 内容 | 記載ルール |
|----|------|-----------|
| U | 結果URL | URL=仕入れ可能 / `なし`=仕入れ不可 / `スキップ`=検索対象外 |
| V | その他候補URL | 最大5件、参考URLを含む |
| W | 備考 | 日本語形式（下記参照） |

### U列の記載パターン

| 状態 | U列 | 説明 |
|------|-----|------|
| 条件合致 | **URL** | 仕入れ可能 |
| 新品なし→中古代替 | **URL** | 許容範囲内の代替（仕入れ可能） |
| 価格オーバー等 | `なし` | 検索したが条件不合致 |
| 同一商品なし | `なし` | 11サイト検索したが見つからず |
| エラー/スキップ | `スキップ` | 検索対象外 |

### W列フォーマット仕様

**形式**: 日本語で視認しやすい形式

**サイト名表記**:
| source値 | W列表記 |
|----------|---------|
| `mercari` | メルカリ |
| `paypay` | PayPayフリマ |
| `yahoo` | ヤフオク |
| `rakuma` | ラクマ |
| `hardoff` | ハードオフ |
| `surugaya` | 駿河屋 |
| `amazon` | Amazon |
| `rakuten` | 楽天 |

**価格表記**: カンマ区切り + 「円」（例: `8,500円`）

**記載パターン**:

| 状態 | W列出力 | 説明 |
|------|---------|------|
| 条件合致 | `{サイト名} {価格}円 {コンディション}` | 仕入れ可能 |
| 条件合致（付属品不足） | `{サイト名} {価格}円 {コンディション}（付属品不足）` | 付属品不足だが仕入れ可能 |
| 新品なし→中古代替 | `{サイト名} {価格}円 {コンディション}（新品なし→中古許可）` | 許容範囲内 |
| 複数注釈 | `{サイト名} {価格}円 {コンディション}（新品なし→中古許可・付属品不足）` | 複数条件の組み合わせ |
| 価格超過 | `価格超過（{サイト名} {価格}円）` | 参考情報 |
| 同一商品なし | `同一商品なし` | 11サイト検索したが見つからず |
| eBayページエラー | `エラー（eBayページなし）` | ページ取得失敗 |

**記載例**:
```
# 条件合致
メルカリ 8,500円 傷や汚れあり

# 条件合致（付属品不足）
メルカリ 8,500円 中古（付属品不足）

# 新品なし→中古代替（許容範囲内）
メルカリ 9,800円 中古（新品なし→中古許可）

# 複数注釈の組み合わせ
メルカリ 9,800円 中古（新品なし→中古許可・付属品不足）

# 価格オーバー（参考情報）
価格超過（ヤフオク 12,000円）

# 同一商品なし
同一商品なし

# eBayページエラー
エラー（eBayページなし）
```

**注釈連結ルール**:
- 複数の注釈がある場合は括弧内を `・` で連結
- 例: `（新品なし→中古許可・付属品不足）`

---

## ワークフロー

### Step 1: タスク登録

TodoWriteで以下を登録:
- スプレッドシートからデータ取得
- eBayページで商品情報確認
- 国内11サイトで仕入れ先検索
- 結果をスプレッドシートに記録
- サマリー報告を出力

### Step 2: スキル状態記録

```bash
cat > ~/.claude/skill-state.json << 'EOF'
{
  "skill": "ebay-sourcing",
  "message": "スキル ebay-sourcing を再実行し、未処理の行から仕入れ先検索を再開してください。"
}
EOF
```

### Step 3: データ取得（初回のみ）

必要な列のみを取得（B, C, F, P, U列）:

```
mcp__google-sheets__get_sheet_data
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: B2:C, F2:F, P2:P, U2:U（個別に取得）
```

**停止条件の定義**:
- **最終行**: C列（eBay Item Number）に値がある最後の行
- **空行の扱い**: 途中の空行はスキップして継続（停止しない）
- **判定方法**: 取得データのC列を走査し、値がある最大行番号を `lastRow` として記録

```
lastRow = max(行番号 where C列 ≠ 空)
処理対象 = 2行目 〜 lastRow
```

### Step 3.5: スキップ判定（各行）

**終了判定**:
- 現在行 > `lastRow` → **Step 10へ**（全行処理完了）

**スキップ判定**:
| 条件 | 対応 |
|------|------|
| U列がURL/「なし」/「スキップ」 | 処理済み → 次の行へ |
| B列が空 | U列に「スキップ」記載 → 次の行へ |
| C列が空 | 空行 → 次の行へ（記載なし） |
| F列が空/0 | U列に「スキップ」記載 → 次の行へ |
| 上記以外 | Step 4へ進む |

### Step 4: eBayページ確認（agent-browser使用）

1. eBayプロファイルでページを開く:
   ```bash
   agent-browser --profile ~/.agent-browser-profiles/ebay --headed open "https://www.ebay.com/itm/{C列}"
   ```
2. ページ内容を取得:
   ```bash
   agent-browser snapshot -c
   ```
3. スナップショットからタイトル・画像URL・ページ状態を確認:
   - タイトル: `h1` 要素のテキスト
   - 画像URL: `img` 要素の `src` 属性（最大4枚）
   - ENDED判定: "This listing has ended" の有無
   - エラー判定: "Error Page" やタイトル不在
4. 画像URLが取得できない場合、JavaScriptで取得:
   ```bash
   agent-browser execute "JSON.stringify(Array.from(document.querySelectorAll('.ux-image-carousel-item img')).map(img => img.src).filter(src => src && !src.includes('data:')).filter((v,i,a) => a.indexOf(v) === i).slice(0, 4))"
   ```
5. 正常/ENDEDの場合、商品画像を最大4枚保存:
   ```bash
   # images配列の枚数分だけ実行（最大4枚）
   python3 -c "
   import ssl, urllib.request
   ctx = ssl.create_default_context()
   ctx.check_hostname = False
   ctx.verify_mode = ssl.CERT_NONE
   req = urllib.request.Request('{images[N]}', headers={'User-Agent': 'Mozilla/5.0'})
   with urllib.request.urlopen(req, context=ctx) as resp:
       data = resp.read()
   with open('images/Target-Product/{C列}_{N}.jpg', 'wb') as f:
       f.write(data)
   "
   ```
6. ブラウザを閉じる:
   ```bash
   agent-browser close
   ```

| 状態 | 判定 | 対応 |
|------|------|------|
| 正常 | タイトルあり、ENDEDなし | 画像保存（最大4枚） → Step 5へ |
| ENDED | "This listing has ended" あり | 画像保存（最大4枚） → Step 5へ |
| エラー | タイトルなし or Error Page | U列=`スキップ`、W列=`エラー（eBayページなし）` → 次の行へ |


### Step 5: 検索キーワード確定

B列の値を検索キーワードとして使用（B列が空の場合はStep 3でスキップ済み）

### Step 6: 仕入れ先検索（現在の1商品のみ・6サイト並列）

**現在処理中の1商品に対してのみ**、6サイトのサブエージェントを並列起動する。
次の商品のサブエージェントは、現在の商品のStep 8（結果記録）が完了するまで起動してはならない。

```
// 現在の1商品に対して6サイトを並列起動
Task: mercari-matcher (prompt: ...)
Task: paypay-matcher (prompt: ...)
Task: rakuma-matcher (prompt: ...)
Task: yahoo-auction-matcher (prompt: ...)
Task: hardoff-matcher (prompt: ...)
Task: surugaya-matcher (prompt: ...)

// ⚠ 全6サイトの結果が揃うまで待機してからStep 7へ進む
// ⚠ Step 8の記録が完了するまで次の商品のStep 4に進んではならない
```

**共通パラメータ**:
| パラメータ | 取得元 | 例 |
|-----------|--------|-----|
| keyword | B列 | "YAMAHA YTS-62" |
| reference_image | Step 4で保存 | "images/Target-Product/405912557904_*.jpg"（ワイルドカード、最大4枚） |
| target_price | F列 | 50000 |
| notes | P列 | "中古" |

**現在有効なサブエージェント（6サイト）**:
- `mercari-matcher` → `.claude/agents/mercari-matcher.md`
- `paypay-matcher` → `.claude/agents/paypay-matcher.md`
- `rakuma-matcher` → `.claude/agents/rakuma-matcher.md`
- `yahoo-auction-matcher` → `.claude/agents/yahoo-auction-matcher.md`
- `hardoff-matcher` → `.claude/agents/hardoff-matcher.md`
- `surugaya-matcher` → `.claude/agents/surugaya-matcher.md`

**返却JSONスキーマ（共通）**:
各サブエージェントは同一スキーマで返却 → メインエージェントで統一処理

```json
{
  "success": true,
  "source": "mercari",
  "matches": [
    {
      "url": "https://...",
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
    "url": "https://...",
    "price_value": 12000,
    "price_total": 13300,
    "shipping_included": false,
    "condition": "中古",
    "condition_group": "used",
    "confidence": "high",
    "reason_code": "price_over",
    "accessory_status": "missing"
  }
}
```

**フィールド説明**:
| フィールド | 説明 |
|-----------|------|
| `source` | サイト名 |
| `matches` | 条件を満たす候補リスト |
| `best_candidate` | 条件未達でも同一商品の最安値（参考情報） |
| `price_value` | 表示価格 |
| `price_total` | 送料込み価格（送料不明時は+1300円） |
| `shipping_included` | 送料込みかどうか |
| `condition_group` | `new` / `used` |
| `accessory_status` | 付属品状態（`complete` / `missing` / `unknown`） |
| `reason_code` | 条件未達の理由（best_candidate用） |
```

### Step 6.5: サブエージェント失敗時の処理

6サイト全ての結果が返るまで待機する。結果がJSON以外（エラーメッセージ、クォータ切れ等）の場合:

| 失敗数 | 対応 |
|--------|------|
| 1〜2サイト失敗 | 成功したサイトの結果のみでStep 7へ進む（W列に未検索サイトを併記） |
| 3サイト以上失敗 | 処理を中断し、ユーザーに状況を報告して指示を仰ぐ |

W列の未検索サイト併記例: `メルカリ 8,500円 中古（未検索: ヤフオク）`

### Step 7: 仕入れ判断（結果統合）

全サブエージェント（または成功分）の返却JSONから最適な仕入れ先を選定:

**7-1. matchesから条件合致候補を選定**:
1. 各サブエージェントの `matches` を収集
2. 以下の優先順位で1件を採用:
   - `confidence: high` を優先
   - 同一confidenceなら `accessory_status: complete` を優先
   - 同一条件なら `price_total` が低い方
   - [reference/conditions.md](reference/conditions.md) のルールに従い判断
3. 採用されなかった候補はV列（その他候補）に記録
4. `accessory_status` が `missing` の場合、W列に「付属品不足」を追記

**7-2. matchesが空の場合**:
1. 各サブエージェントの `best_candidate` を収集
2. `price_total` が最も低いものを参考情報として採用
3. U列=`なし`、V列=参考URL、W列=`価格超過（{サイト名} {価格}円）`

**7-3. best_candidateも空の場合**:
- U列=`なし`、W列=`同一商品なし`

### Step 8: 結果記録

```
mcp__google-sheets__update_cells
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: U{行}:W{行}
data: [[U列値, V列値, W列値]]
```

**記録パターン**:

| 状態 | U列 | V列 | W列 |
|------|-----|-----|-----|
| 条件合致 | ベストURL | 他候補URL | `メルカリ 8,500円 傷や汚れあり` |
| 新品なし→中古代替 | 代替URL | 他候補URL | `メルカリ 9,800円 中古（新品なし→中古許可）` |
| 価格オーバー等 | `なし` | 参考URL | `価格超過（ヤフオク 12,000円）` |
| 同一商品なし | `なし` | （空） | `同一商品なし` |
| eBayページエラー | `スキップ` | （空） | `エラー（eBayページなし）` |

### Step 9: 後処理（行ごと）

1. 商品画像を削除: `rm -f images/Target-Product/{C列}_*.jpg`
2. 不要タブを閉じる
3. 10件ごとに進捗報告
4. 現在行をインクリメント → **Step 3.5へ戻る**

```
ループフロー（1商品ずつ順次処理）:

  ┌─→ Step 3.5: 現在行 > lastRow ? → Yes → Step 10（終了）
  │                               → No  → スキップ判定
  │   ↓
  │   Step 4: eBayページ確認（現在の1商品）
  │   ↓
  │   Step 5: キーワード確定
  │   ↓
  │   Step 6: 6サイト並列検索（現在の1商品のみ）
  │   ↓
  │   Step 6.5: 全結果待機・失敗判定
  │   ↓
  │   Step 7: 結果統合・仕入れ判断
  │   ↓
  │   Step 8: スプレッドシートに記録 ← ここで初めて次の商品に進める
  │   ↓
  └── Step 9: 後処理 → 現在行++
```

### Step 10: 完了処理

サマリー報告を出力:

| 項目 | 結果 |
|------|------|
| 処理件数 | {N} |
| 仕入れ先発見 | {N} |
| 見つからず | {N} |
| スキップ | {N} |
| エラー | {N} |

---

## 実行パラメータ

| 指定 | 動作 |
|------|------|
| 「全て」 | 上から順に全件処理 |
| アイテムナンバー指定 | 指定行のみ処理 |
| 再処理 | U列を消して再実行 |

---

## 前提条件

- Google Sheets MCPサーバー設定済み
- agent-browser インストール済み
- eBayプロファイル設定済み（`~/.agent-browser-profiles/ebay`）
- Cookie同意ダイアログは「許可」で対応
- **Claude in Chrome / Playwright MCPの使用禁止**（ユーザー明示指示時のみ例外）
