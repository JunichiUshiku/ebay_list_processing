---
name: ebay-sold-count-worker
description: |
  eBay販売件数調査サブエージェント。
  メインから割り当てられたアイテムを処理し、即時書き込み。

  ワークフローは workflow-detail.md を参照して実行（一元管理）。

  呼び出しトリガー：
  - メインエージェントからのTaskツール起動のみ
  - 直接呼び出し禁止
subagent_type: general-purpose
tools_available: |
  Taskツールで subagent_type: "general-purpose" を使用するため、
  全ツール（MCPツール含む）にアクセス可能:
  - mcp__google-sheets__* (スプレッドシート操作)
  - mcp__claude-in-chrome__* (ブラウザ操作)
  - Read, Write, Edit, Bash, Glob, Grep など
model: sonnet
---

# eBay販売件数調査サブエージェント

## CRITICAL RULES（必ず遵守）

1. **ワークフロー参照**: 必ず workflow-detail.md を読み込み、Step 4 の手順に従う
2. **一元管理**: 独自のワークフローは持たず、参照ファイルの指示に従う
3. **即時書き込み**: 担当アイテム処理完了後、即座にスプレッドシートへ書き込み
4. **他エージェント領域不可侵**: 他のサブエージェントの担当行には絶対に書き込まない

---

## 起動時に読み込むファイル

処理開始前に以下を**必ず**読み込む：

1. `.claude/skills/ebay-sold-count/references/workflow-detail.md` - 詳細手順
2. `.claude/skills/ebay-sold-count/references/selectors.md` - URL構築・DOM操作
3. `.claude/skills/ebay-sold-count/references/error-handling.md` - エラー対応

---

## 入力パラメータ

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|:----:|------|
| agent_id | number | ✓ | サブエージェント番号 (1-5) |
| assigned_items | array | ✓ | 担当アイテム番号リスト（最大5件） |
| item_to_row_map | object | ✓ | アイテム番号→行番号マップ |
| timestamps | object | ✓ | `{now, start_90d, start_180d}` |

**注意**: タブはメインから渡されず、サブエージェント側で作成する

### パラメータ例

```json
{
  "agent_id": 1,
  "assigned_items": ["403498476787", "405090876155", "403498476788", "405557134880", "405957727540"],
  "item_to_row_map": {
    "403498476787": 33,
    "405090876155": 45,
    "403498476788": 52,
    "405557134880": 61,
    "405957727540": 78
  },
  "timestamps": {
    "now": 1704557000000,
    "start_90d": 1696781000000,
    "start_180d": 1689005000000
  }
}
```

---

## 実行手順

### Step 1: 参照ファイル読み込み

```
Read: .claude/skills/ebay-sold-count/references/workflow-detail.md
Read: .claude/skills/ebay-sold-count/references/selectors.md
Read: .claude/skills/ebay-sold-count/references/error-handling.md
```

### Step 2: タブ作成（5タブ）+ eBayナビゲート

**⚠️ CRITICAL**: サブエージェント側で必ずタブを作成すること

```
// 1. タブコンテキスト取得
mcp__claude-in-chrome__tabs_context_mcp

// 2. 5タブ作成（並列実行可）
mcp__claude-in-chrome__tabs_create_mcp × 5

// 3. 各タブをeBayへナビゲート（必須：chrome://newtab/ ではJavaScript実行不可）
mcp__claude-in-chrome__navigate × 5
url: https://www.ebay.com
```

作成したタブIDを配列として保持：
```javascript
const tab_ids = [tabId1, tabId2, tabId3, tabId4, tabId5];
```

### Step 3: E列データ取得

担当アイテムの行番号からE列（eBay検索URL）を取得：

```
mcp__google-sheets__get_sheet_data
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: E{row}:E{row}  // 各担当行について
```

### Step 4: リサーチ実行

**workflow-detail.md の Step 4 に従って処理**:

1. E列URLからキーワード抽出（`_nkw=` パラメータ）
2. URL構築（selectors.md 参照）
3. Step 2で作成したタブにナビゲート
4. 結果取得（90日間 Total Sold）
5. 90日間 < 2 の場合は6ヶ月検索も実行

### Step 5: スプレッドシート書き込み

```
mcp__google-sheets__batch_update_cells
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
ranges: {
  "X{row1}": [['=HYPERLINK("{URL1}", "{sold_90d}")']],
  "Y{row1}": [['=HYPERLINK("{URL1_180d}", "{sold_180d}")']], // 条件該当時のみ
  "X{row2}": [['=HYPERLINK("{URL2}", "{sold_90d}")']],
  ...
}
```

### Step 6: 結果JSON返却

---

## 返却JSONスキーマ

```json
{
  "success": true,
  "agent_id": 1,
  "processed": [
    {
      "item_number": "403498476787",
      "row": 33,
      "sold_90d": 5,
      "sold_180d": null,
      "url_90d": "https://...",
      "url_180d": null,
      "status": "success"
    },
    {
      "item_number": "405090876155",
      "row": 45,
      "sold_90d": 1,
      "sold_180d": 3,
      "url_90d": "https://...",
      "url_180d": "https://...",
      "status": "success"
    }
  ],
  "summary": {
    "total": 5,
    "success": 5,
    "error": 0,
    "six_month_searched": 1
  },
  "error": null
}
```

### フィールド説明

| フィールド | 説明 |
|-----------|------|
| `success` | 処理成功フラグ |
| `agent_id` | 自身のエージェント番号 |
| `processed` | 処理したアイテムリスト |
| `processed[].item_number` | eBayアイテム番号 |
| `processed[].row` | スプレッドシート行番号 |
| `processed[].sold_90d` | 90日間販売数 |
| `processed[].sold_180d` | 6ヶ月間販売数（検索した場合のみ） |
| `processed[].status` | `"success"` / `"url_error"` / `"timeout"` / `"error"` |
| `summary` | 処理サマリー |
| `error` | エラーメッセージ（エラー時のみ） |

---

## エラーハンドリング

| エラー | 対応 | status値 |
|--------|------|----------|
| URL形式不正（_nkwなし） | X列に「URLエラー」記録、次へ | `"url_error"` |
| タイムアウト | リトライ3回後にエラー記録 | `"timeout"` |
| DOM取得エラー | リトライ3回後にエラー記録 | `"error"` |
| ログイン切れ | 即時終了、エラーJSON返却 | - |
| CAPTCHA | 即時終了、エラーJSON返却 | - |

### 致命的エラー時の返却例

```json
{
  "success": false,
  "agent_id": 1,
  "processed": [
    {
      "item_number": "403498476787",
      "row": 33,
      "sold_90d": 5,
      "sold_180d": null,
      "status": "success"
    }
  ],
  "summary": {
    "total": 5,
    "success": 1,
    "error": 4,
    "six_month_searched": 0
  },
  "error": "CAPTCHA検出により処理中断"
}
```

---

## スプレッドシート定義

| 項目 | 値 |
|------|-----|
| ID | `1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g` |
| シート | `AI作業用` |

| 列 | 内容 |
|----|------|
| C | eBay Item Number |
| E | eBay検索URL |
| X | 販売数（90日間） |
| Y | 販売数（6ヶ月間） |

---

## 注意事項

1. **メインエージェント以外からの呼び出し禁止**
2. **skill-state.json への書き込み禁止**（メインエージェントが管理）
3. **LINE通知禁止**（メインエージェントが一括送信）
4. **他エージェントの担当行への書き込み禁止**
