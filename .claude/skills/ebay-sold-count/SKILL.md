---
name: ebay-sold-count
description: eBay販売履歴件数調査ワークフロー（並列処理版）。スプレッドシートのE列eBay検索URLからキーワードを抽出し、eBay Seller Hub Product Researchで90日間の販売件数（Total Sold合計）を調べてX列に記録する。90日間の販売件数が2未満の場合は6ヶ月間で再検索しY列に記録。5タブ並列処理により従来比70%の時間短縮を実現。「販売件数を調べて」「sold count」「90日間の販売数」「リサーチ」で全件処理。アイテムナンバーを指定した場合（例:「403498476787の販売数を調べて」）はC列から該当行を検索して処理。
---

# eBay販売件数調査処理（並列処理版）

## 🚨 CRITICAL RULES (MUST PRESERVE AFTER COMPACTION)

**REQUIRED**: Read `references/selectors.md` FIRST before any processing
**METHOD**: URL直接ナビゲート（UI操作不要）
**PARALLEL**: 5タブ同時処理

**必須**: 処理開始前に `references/selectors.md` を必ず読み込む
**方式**: URLパラメータでキーワード・期間を指定して直接ナビゲート
**並列**: 5タブで同時にページロード、順次結果取得

---

## 🔴 必須参照ファイル（最初に読み込むこと）

**以下のファイルをReadツールで読み込んでから処理を開始すること。**

| ファイル | パス | 内容 |
|----------|------|------|
| セレクター | `.claude/skills/ebay-sold-count/references/selectors.md` | URL生成、DOM要素セレクター、エラー検出コード |

```
Read: .claude/skills/ebay-sold-count/references/selectors.md
```

**⚠️ このファイルを読み込まずに処理を開始することは禁止。**

---

## スプレッドシート定義

**Spreadsheet ID**: `1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g`
**Sheet名**: `AI作業用`

| 列 | 内容 | 備考 |
|----|------|------|
| C | eBay Item Number | アイテムナンバー指定時の検索対象 |
| E | eBay検索URL | `_nkw=`パラメータからキーワード抽出 |
| X | 販売数（90日間） | 処理結果を記録（値あり→スキップ） |
| Y | 販売数（6ヶ月間） | X列が2未満の場合のみ記録 |

ヘッダー: 1行目、データ: 2行目から

---

## 🚀 並列処理ワークフロー概要

```
[初期化]
1. TodoWriteでタスク登録
2. 参照ファイル読み込み
3. スプレッドシートからデータ取得
4. 処理対象行を特定
5. 5タブを作成

[並列処理ループ]（5件単位）
6. 5つのURLを生成（キーワード+90日間）
7. 各タブに並列ナビゲート
8. 全タブのロード完了を待機
9. 各タブから結果取得（Total Sold + URL）
10. 90日間が2未満の場合 → 6ヶ月URLに再ナビゲート
11. 5件分をバッチ書き込み
12. 次の5件へ

[完了]
13. サマリー報告
```

---

## ワークフロー詳細

### Step 1: TodoWriteでタスク登録（必須・最初に実行）

**⚠️ このステップを最初に実行すること。スキップ禁止。**

TodoWriteツールで以下のタスクを登録し、進捗を可視化:

```
TodoWrite:
- 参照ファイル（selectors.md）を読み込む (pending) ← 最初に実行
- スプレッドシートからデータ取得 (pending)
- 処理対象行の特定 (pending)
- 5タブを作成 (pending)
- 並列処理で販売数調査 (pending)
- 結果をスプレッドシートに記録 (pending)
- サマリー報告を出力 (pending)
```

### Step 2: 参照ファイル読み込み（必須）

**TodoWrite更新**: `参照ファイル（selectors.md）を読み込む` → `in_progress`

```
Read: .claude/skills/ebay-sold-count/references/selectors.md
```

このファイルには以下が記載されている:
- URL生成テンプレート
- DOM要素のセレクター一覧
- ロード完了検出コード
- CAPTCHA・ログイン切れ検出コード

**TodoWrite更新**: `参照ファイル（selectors.md）を読み込む` → `completed`

### Step 3: X列・Y列ヘッダー確認

1. X1・Y1セルを取得:
```
mcp__google-sheets__get_sheet_data
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: X1:Y1
```

2. ヘッダーが空の場合 → 書き込み:
```
mcp__google-sheets__update_cells
range: X1:Y1
data: [["販売数（90日間）", "販売数（6ヶ月間）"]]
```

### Step 4: 必要な列のみデータ取得

**TodoWrite更新**: `スプレッドシートからデータ取得` → `in_progress`

4列を個別に取得（並列実行可）:
- C列（アイテムナンバー）: `range: C:C`
- E列（eBay URL）: `range: E:E`
- X列（90日間販売件数）: `range: X:X`
- Y列（6ヶ月間販売件数）: `range: Y:Y`

**TodoWrite更新**: `スプレッドシートからデータ取得` → `completed`

### Step 5: 処理対象の決定

**TodoWrite更新**: `処理対象行の特定` → `in_progress`

**アイテムナンバー指定あり**:
- C列から検索し**行番号を特定**
- 特定した行番号と同じ行のE列からURL取得
- X列の値に関係なく処理

**指定なし（全件処理）**:
- X列が空 → 未処理、検索実行対象
- X列に数値あり → 処理済み、スキップ

**キーワード抽出**:
E列URLから`_nkw=`パラメータを抽出:
```
入力: https://www.ebay.com/sch/i.html?_nkw=Crab+Plate&_sacat=0
抽出: Crab Plate（+を空白に変換）
```

**エラーケース**: `_nkw=`が存在しない → X列に「URLエラー」記録

**TodoWrite更新**: `処理対象行の特定` → `completed`

### Step 6: 5タブを作成

**TodoWrite更新**: `5タブを作成` → `in_progress`

```
mcp__claude-in-chrome__tabs_context_mcp（初回のみ）
mcp__claude-in-chrome__tabs_create_mcp × 5回
```

5つのタブIDを保持しておく。

**TodoWrite更新**: `5タブを作成` → `completed`

### Step 7: 並列処理ループ（5件単位）

**TodoWrite更新**: `並列処理で販売数調査` → `in_progress`

#### 7-1: URL生成（5件分）

処理対象から5件を取得し、各キーワードに対してURLを生成:

```javascript
// selectors.md のテンプレートを使用（startDate/endDate必須）
const endDate = Date.now();
const startDate90 = endDate - (90 * 24 * 60 * 60 * 1000);
const url = `https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=${encodeURIComponent(keyword)}&dayRange=90&endDate=${endDate}&startDate=${startDate90}&categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo`;
```

**重要**: `startDate`と`endDate`がないと期間計算が不正確になる。

#### 7-2: 各タブに並列ナビゲート

**同一メッセージ内で5つのnavigate呼び出しを実行**:

```
mcp__claude-in-chrome__navigate
tabId: {タブ1のID}
url: {URL1}

mcp__claude-in-chrome__navigate
tabId: {タブ2のID}
url: {URL2}

... (5タブ分)
```

#### 7-3: ロード完了待機

各タブでページロード完了を確認:

```
mcp__claude-in-chrome__computer
tabId: {タブID}
action: wait
duration: 3
```

その後、ロード完了を確認:
```
mcp__claude-in-chrome__javascript_tool
tabId: {タブID}
text: !!document.querySelector('.research-table-row__totalSoldCount') || !!document.querySelector('.research-table__no-results')
```

**エラーチェック**（各タブで実行）:
```javascript
// CAPTCHA検出
!!document.querySelector('iframe[title*="reCAPTCHA"]') || !!document.querySelector('.g-recaptcha')

// ログイン切れ検出
window.location.href.includes('/signin')
```

**CAPTCHA検出時**: 処理中断、ユーザーに手動解除を依頼
**ログイン切れ検出時**: 処理中断、ユーザーに再ログインを依頼

#### 7-4: 結果取得（順次）

各タブから結果を取得:

```
mcp__claude-in-chrome__javascript_tool
tabId: {タブID}
text: const cells = document.querySelectorAll('.research-table-row__totalSoldCount'); Array.from(cells).reduce((sum, cell) => sum + (parseInt(cell.innerText) || 0), 0);
```

同時にURLも取得:
```
mcp__claude-in-chrome__javascript_tool
tabId: {タブID}
text: window.location.href
```

#### 7-5: 6ヶ月間追加検索（条件付き）

**条件**: 90日間のTotal Soldが**2未満**の場合のみ実行

該当するタブのみ、6ヶ月間URLに再ナビゲート:
```javascript
const endDate = Date.now();
const startDate180 = endDate - (180 * 24 * 60 * 60 * 1000);
const url = `https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=${encodeURIComponent(keyword)}&dayRange=180&endDate=${endDate}&startDate=${startDate180}&categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo`;
```

再度ロード待機 → 結果取得

**条件分岐まとめ**:
| 90日間の結果 | 6ヶ月検索 | X列 | Y列 |
|--------------|-----------|-----|-----|
| 2以上 | 実行しない | 90日間の値（リンク付き） | 空 |
| 2未満（0, 1） | 実行する | 90日間の値（リンク付き） | 6ヶ月間の値（リンク付き） |

### Step 8: 結果記録（バッチ書き込み）

**TodoWrite更新**: `結果をスプレッドシートに記録` → `in_progress`

5件分をまとめてMCPツールでバッチ書き込み:

#### 書き込み形式: HYPERLINK関数

販売数に検索結果URLへのリンクを埋め込む:

```
mcp__google-sheets__batch_update_cells
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
ranges: {
  "X{行番号1}": [['=HYPERLINK("{90日間検索URL1}", "{販売数1}")']],
  "X{行番号2}": [['=HYPERLINK("{90日間検索URL2}", "{販売数2}")']],
  ...
  "Y{行番号}": [['=HYPERLINK("{6ヶ月間検索URL}", "{販売数}")']]  // 条件該当時のみ
}
```

**例**:
```
"X5": [['=HYPERLINK("https://www.ebay.com/sh/research?marketplace=EBAY-US&keywords=Crab+Plate&dayRange=90&tabName=SOLD", "3")']]
```
→ セルには「3」と表示され、クリックで検索結果ページに遷移

**注意事項**:
- URL内に `"` が含まれる場合は `""` にエスケープする
- エラー時（URLエラー、タイムアウト等）はリンクなしで文字列のみ記録
- 販売数が0でもリンク付きで記録（検索結果確認のため有用）

### Step 9: ループ継続

1. Step 7-8を繰り返し
2. **5件ごとに進捗報告**: 「進捗: 20/100件完了（20%）」
3. **20件ごとにタブリフレッシュ**（メモリ管理）: タブを閉じて再作成

**TodoWrite更新**:
- `並列処理で販売数調査` → `completed`
- `結果をスプレッドシートに記録` → `completed`

### Step 10: 完了処理

**TodoWrite更新**: `サマリー報告を出力` → `in_progress`

**サマリー報告（テーブル形式）**:

| 項目 | 結果 |
|------|------|
| 処理件数 | {処理した件数} |
| 成功 | {成功件数} |
| エラー | {エラー件数}（行番号: {該当行}） |
| 6ヶ月検索実行 | {6ヶ月検索を実行した件数} |
| 処理時間 | {開始から終了までの時間} |

**TodoWrite更新**: `サマリー報告を出力` → `completed`

---

## エラーハンドリング

| エラー種別 | 検出方法 | 対応 | 記録値 |
|------------|----------|------|--------|
| URL形式不正 | `_nkw=`なし | 次へスキップ | 「URLエラー」 |
| ログイン切れ | URL検出 | 処理中断 | ユーザー通知 |
| CAPTCHA出現 | iframe検出 | 処理中断 | ユーザー通知 |
| 検索結果なし | DOM検出 | 正常終了 | 0（リンク付き） |
| ページタイムアウト | 10秒経過 | リトライ3回 | 「タイムアウト」 |
| DOM要素未検出 | querySelector失敗 | リトライ3回 | 「取得エラー」 |
| 書き込み失敗 | MCP例外 | リトライ2回 | ログ出力 |

**リトライ間隔**: 2秒→5秒→10秒

---

## 実行パラメータ

| 指定 | 動作 |
|------|------|
| 「全て」 | X列が空の全行を処理 |
| 行番号指定 | 指定行以降のX列空の行を処理 |
| 件数指定 | 指定件数のみ処理 |
| アイテムナンバー指定 | C列から該当行を検索して処理 |

---

## 期待される効率化効果

| 項目 | 従来（順次） | 並列処理版 | 改善率 |
|------|------------|-----------|--------|
| 100件処理時間 | 8-10分 | 2.5-3分 | **-70%** |
| UI操作回数 | 300回 | 0回 | **-100%** |
| MCP呼び出し | 多数 | 最適化済み | **-50%** |

---

## 前提条件

- Google Sheets MCPサーバー設定済み
- eBay Seller Hubアクセス権限あり（ログイン済み）
- Chrome拡張（claude-in-chrome）でブラウザ操作可能
