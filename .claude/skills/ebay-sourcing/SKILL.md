---
name: ebay-sourcing
description: eBay販売商品の国内仕入れ先検索ワークフロー。国内11サイトで同一商品を検索し、希望価格・コンディション条件に合う仕入れ先を見つけてスプレッドシートに記録する。
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

| 列 | 内容 | 用途 |
|----|------|------|
| B | 商品名 | 検索キーワード |
| C | eBay Item Number | eBayページ確認 |
| F | 仕入価格（円） | 空/0→スキップ |
| P | コンディション | 新品/中古判定 |
| U | 結果URL | 処理済み判定 |
| V | その他候補URL | 最大5件 |
| W | 備考 | 価格、状態、エラー等 |

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

### Step 4: eBayページ確認

1. `mcp__claude-in-chrome__navigate` で `https://www.ebay.com/itm/{C列}` を開く
2. `mcp__claude-in-chrome__computer` (action: wait, duration: 3) でページロード待機
3. `mcp__claude-in-chrome__javascript_tool` でページ状態と画像URLを一括取得:
   ```javascript
   JSON.stringify({
     title: document.querySelector('h1.x-item-title__mainTitle')?.textContent?.trim() || null,
     image: document.querySelector('.ux-image-carousel-item img')?.src || null,
     isEnded: document.body.innerText.includes('This listing has ended'),
     isError: document.title.includes('Error Page') || !document.querySelector('h1.x-item-title__mainTitle')
   })
   ```
4. 正常/ENDEDの場合、商品画像を保存:
   ```bash
   curl -o "images/Target-Product/{C列}.jpg" "{image URL}"
   ```

| 状態 | 判定 | 対応 |
|------|------|------|
| 正常 | `isError: false`, `isEnded: false` | 画像保存 → Step 5へ |
| ENDED | `isEnded: true` | 画像保存 → Step 5へ |
| エラー | `isError: true` or `title: null` | W列に「ページなし」→ スキップ |


### Step 5: 検索キーワード確定

B列の値を検索キーワードとして使用（B列が空の場合はStep 3でスキップ済み）

### Step 6: 仕入れ先検索（サブエージェント並列実行）

Taskツールで仕入れ先検索サブエージェントを**並列実行**:

```
// 1メッセージで複数Taskを呼び出し → 並列実行
Task: mercari-matcher (prompt: ...)
Task: yahoo-auction-matcher (prompt: ...)  // 将来追加
Task: amazon-matcher (prompt: ...)         // 将来追加
...
```

**共通パラメータ**:
| パラメータ | 取得元 | 例 |
|-----------|--------|-----|
| keyword | B列 | "YAMAHA YTS-62" |
| reference_image | Step 4で保存 | "images/Target-Product/405912557904.jpg" |
| target_price | F列 | 50000 |
| notes | P列 | "中古" |

**現在有効なサブエージェント**:
- `mercari-matcher` → `.claude/agents/mercari-matcher.md`

**返却JSONスキーマ（共通）**:
各サブエージェントは同一スキーマで返却 → メインエージェントで統一処理

```json
{
  "success": true,
  "matches": [
    {
      "url": "https://...",
      "price_value": 8500,
      "condition": "未使用に近い",
      "confidence": "high"
    }
  ]
}
```

### Step 7: 仕入れ判断（結果統合）

全サブエージェントの返却JSONから最適な仕入れ先を選定:

1. 各サブエージェントの `matches` を収集
2. 以下の優先順位で1件を採用:
   - `confidence: high` を優先
   - 同一confidenceなら `price_value` が低い方
   - [reference/conditions.md](reference/conditions.md) のルールに従い判断
3. 採用されなかった候補はV列（その他候補）に記録

### Step 8: 結果記録

```
mcp__google-sheets__update_cells
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: U{行}:W{行}
data: [[ベストURL or「なし」, 候補URL, 備考]]
```

### Step 9: 後処理（行ごと）

1. 商品画像を削除: `rm -f images/Target-Product/{C列}.jpg`
2. 不要タブを閉じる
3. 10件ごとに進捗報告
4. 現在行をインクリメント → **Step 3.5へ戻る**

```
ループフロー:
  Step 3.5: 現在行 > lastRow ? → Yes → Step 10（終了）
                              → No  → スキップ判定
  ↓
  Step 4〜8: 処理実行
  ↓
  Step 9: 後処理 → 現在行++ → Step 3.5へ
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
- Claude in Chrome MCP設定済み
- Cookie同意ダイアログは「許可」で対応
