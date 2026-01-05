# ワークフロー詳細手順

## 目次

1. [参照ファイル読み込み](#step-1-参照ファイル読み込み)
2. [データ取得・処理対象特定](#step-2-データ取得処理対象特定)
3. [5タブ作成 + eBayナビゲート](#step-3-5タブ作成--ebayナビゲート)
4. [並列処理で販売数調査](#step-4-並列処理で販売数調査)
5. [結果をスプレッドシートに記録](#step-5-結果をスプレッドシートに記録)
6. [LINE通知送信](#step-6-line通知送信)
7. [サマリー報告](#step-7-サマリー報告)

---

## Step 1: 参照ファイル読み込み

```
Read: .claude/skills/ebay-sold-count/references/selectors.md
```

このファイルには以下が記載:
- タイムスタンプ取得関数
- DOM要素のセレクター
- エラー検出コード

---

## Step 2: データ取得・処理対象特定

### 2-1: ヘッダー確認

```
mcp__google-sheets__get_sheet_data
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: X1:Y1
```

ヘッダーが空の場合:
```
mcp__google-sheets__update_cells
range: X1:Y1
data: [["販売数（90日間）", "販売数（6ヶ月間）"]]
```

### 2-2: 処理モード判定とデータ取得（最適化版）

**重要**: トークン制限（25,000トークン）を回避するため、必要な列のみを段階的に取得する。

#### アイテムナンバー指定時

1. **C列のみ取得**
   ```
   mcp__google-sheets__get_sheet_data
   spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
   sheet: AI作業用
   range: C:C
   ```

2. **行番号特定**
   - C列から指定されたアイテムナンバーを検索
   - 該当行の行番号を特定（例: 15行目）

3. **該当行のE列のみ取得**
   ```
   mcp__google-sheets__get_sheet_data
   range: E15:E15
   ```

4. **キーワード抽出**
   ```
   E列URL: https://www.ebay.com/sch/i.html?_nkw=Crab+Plate&_sacat=0
   抽出: Crab Plate（+を空白に変換）
   ```

#### 全件処理時

1. **X列のみ取得**
   ```
   mcp__google-sheets__get_sheet_data
   range: X:X
   ```

2. **処理対象行の特定**
   - X列で空セルの行番号をリストアップ
   - 例: [10, 15, 20, 25, 30, ...]

3. **該当行のE列を取得**
   - 個別または小バッチで取得（トークン制限を考慮）
   - 連続する行がある場合は範囲指定で効率化
   - 例1（個別）: `E10:E10`, `E15:E15`, `E20:E20`
   - 例2（連続範囲）: `E10:E20` （行10〜20がすべて対象の場合）

4. **キーワード抽出**
   - 各URLからキーワードを抽出

---

## Step 3: 5タブ作成 + eBayナビゲート

### 3-1: タブ作成

```
mcp__claude-in-chrome__tabs_context_mcp（初回のみ）
mcp__claude-in-chrome__tabs_create_mcp × 5回
```

### 3-2: eBayへナビゲート（必須）

**重要**: 新規タブは `chrome://newtab/` 状態でJavaScript実行不可

```
mcp__claude-in-chrome__navigate
tabId: {タブID}
url: https://www.ebay.com
```

※ 5タブ並列でナビゲート実行

### 3-3: タイムスタンプ取得

ナビゲート完了後、いずれかのタブでタイムスタンプを取得:

```javascript
(function() {
  const now = Date.now();
  const start = now - (90 * 24 * 60 * 60 * 1000);
  return JSON.stringify({now: now, start: start});
})()
```

※ 数値のみなのでMCPセキュリティでブロックされない

---

## Step 4: 並列処理で販売数調査

### 4-1: URL構築（Claude側で実行）

タイムスタンプ取得後、URLをClaude側で構築:

```
https://www.ebay.com/sh/research?marketplace=EBAY-US
  &keywords={encodeURIComponent(キーワード)}
  &dayRange=90
  &startDate={start}
  &endDate={now}
  &categoryId=0&offset=0&limit=50&tabName=SOLD&tz=Asia%2FTokyo
```

**重要**: 構築したURLを保持（HYPERLINK用に再利用）

### 4-2: 各タブに並列ナビゲート

```
mcp__claude-in-chrome__navigate
tabId: {タブ1のID}
url: {URL1}

mcp__claude-in-chrome__navigate
tabId: {タブ2のID}
url: {URL2}

... (5タブ分を同一メッセージで)
```

### 4-3: ロード完了待機

```
mcp__claude-in-chrome__computer
action: wait
duration: 3-4
```

### 4-4: 結果取得

```javascript
const cells = document.querySelectorAll('.research-table-row__totalSoldCount');
Array.from(cells).reduce((sum, cell) => sum + (parseInt(cell.innerText) || 0), 0);
```

### 4-5: 6ヶ月間追加検索（条件付き）

**条件**: 90日間のTotal Soldが2未満の場合のみ

6ヶ月URL構築:
```
dayRange=180
startDate={now - 180日分のミリ秒}
```

再ナビゲート → 結果取得

---

## Step 5: 結果をスプレッドシートに記録

### HYPERLINK形式で書き込み

```
mcp__google-sheets__batch_update_cells
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
ranges: {
  "X{行番号}": [['=HYPERLINK("{保持したURL}", "{販売数}")']],
  "Y{行番号}": [['=HYPERLINK("{6ヶ月URL}", "{販売数}")']]  // 条件該当時のみ
}
```

**注意**: URL内の `"` は `""` にエスケープ

---

## Step 6: LINE通知送信

処理完了後に必ず実行:

```bash
.claude/hooks/notify-line.sh "【eBay販売件数調査完了】
処理: {処理件数}件（成功: {成功件数} / エラー: {エラー件数}）
処理時間: {DURATION}

ID: 90日間 / 6ヶ月間
405237152554: 5件 / -
405237187303: 1件 / 3件
405237190822: 0件 / 2件
...

結果: https://docs.google.com/spreadsheets/d/1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g"
```

**表示ルール**:
- 処理した全アイテムをリスト表示
- 90日間 < 2: 「ID: X件 / Y件」（6ヶ月検索を実行）
- 90日間 >= 2: 「ID: X件 / -」（6ヶ月検索を実行せず）

※ 環境変数未設定時はスキップ（エラーにしない）

---

## Step 7: サマリー報告

| 項目 | 結果 |
|------|------|
| 処理件数 | {処理した件数} |
| 成功 | {成功件数} |
| エラー | {エラー件数}（行番号: {該当行}） |
| 6ヶ月検索実行 | {6ヶ月検索を実行した件数} |

---

## 並列処理のループ（5件単位）

1. Step 4-5を繰り返し
2. 5件ごとに進捗報告: 「進捗: 20/100件完了（20%）」
3. 20件ごとにタブリフレッシュ（メモリ管理）

---

## 実行パラメータ

| 指定 | 動作 |
|------|------|
| 「全て」 | X列が空の全行を処理 |
| 行番号指定 | 指定行以降のX列空の行を処理 |
| 件数指定 | 指定件数のみ処理 |
| アイテムナンバー指定 | C列から該当行を検索して処理 |
