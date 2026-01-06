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

## 処理進捗チェックリスト

このチェックリストをコピーして進行状況を追跡：

```
処理進捗：
- [ ] Step 0: skill-state.json作成
- [ ] Step 1: 参照ファイル読み込み
- [ ] Step 2: データ取得・処理対象特定（total: ___件）
- [ ] Step 3: 5タブ作成 + eBayナビゲート
- [ ] Step 4-5: バッチ処理
  - [ ] バッチ1 (行___-___): 検索 → 書き込み → 進捗更新
  - [ ] バッチ2 (行___-___): 検索 → 書き込み → 進捗更新
  - [ ] バッチ3 (行___-___): 検索 → 書き込み → 進捗更新
  - [ ] ... (必要に応じて追加)
- [ ] Step 6: LINE通知送信
- [ ] Step 7: サマリー報告
- [ ] Step 8: skill-state.json削除（正常完了時のみ）
```

**重要**: 各バッチ完了後に必ず skill-state.json を更新すること

---

## Step 0: skill-state.json作成（必須・最初に実行）

スキル開始時に必ず実行中状態を記録：

```bash
cat > ~/.claude/skill-state.json << 'EOF'
{
  "skill": "ebay-sold-count",
  "target_rows": [],
  "cursor": 0,
  "total": 0,
  "message": "【重要】まず Skill ツールで skill: ebay-sold-count を実行し、全指示を再ロードすること。その後、進捗に従って処理を継続。"
}
EOF
```

データ取得後、target_rows（アイテム番号リスト）とtotal件数を更新：

```bash
# アイテム番号リストをJSON配列として構築
TARGET_ROWS_JSON='["403498476787","405090876155","403498476788"]'

cat > ~/.claude/skill-state.json << EOF
{
  "skill": "ebay-sold-count",
  "target_rows": ${TARGET_ROWS_JSON},
  "cursor": 0,
  "total": 118,
  "message": "【重要】まず Skill ツールで skill: ebay-sold-count を実行し、全指示を再ロードすること。進捗: 0/118件完了、次はアイテム403498476787から処理開始。"
}
EOF
```

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

### MCPツール表記について

**重要**: 本スキルは以下のMCPツール表記を使用:
- `mcp__google-sheets__get_sheet_data` ✅ 正しい形式
- `mcp__google-sheets__update_cells` ✅ 正しい形式
- `mcp__google-sheets__batch_update_cells` ✅ 正しい形式
- `mcp__claude-in-chrome__tabs_context_mcp` ✅ 正しい形式
- `mcp__claude-in-chrome__navigate` ✅ 正しい形式
- `mcp__claude-in-chrome__javascript_tool` ✅ 正しい形式

**注意**: `serverName:tool_name` 形式は本環境では使用しない。

### 2-2: 処理モード判定とデータ取得（アイテム番号ベース）

**重要**: トークン制限（25,000トークン）を回避するため、必要な列のみを段階的に取得する。

#### アイテムナンバー指定時

1. **C列のみ取得**
   ```
   mcp__google-sheets__get_sheet_data
   spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
   sheet: AI作業用
   range: C:C
   ```

2. **アイテム番号リスト生成**（行番号は保存しない）
   - C列から指定されたアイテムナンバーを検索
   - 存在確認のみ行い、アイテム番号をリストに追加
   - 見つからないアイテムは警告を表示

   ```javascript
   const targetItems = ["403498476787", "405090876155"];  // ユーザー指定
   const targetRows = [];  // アイテム番号のみのリスト
   const notFound = [];

   for (const itemNum of targetItems) {
     const exists = columnC.some(cell => cell?.trim() === itemNum.trim());
     if (exists) {
       targetRows.push(itemNum);
     } else {
       notFound.push(itemNum);
     }
   }

   if (notFound.length > 0) {
     console.warn(`見つかりませんでした: ${notFound.join(', ')}`);
   }

   // target_rows: ["403498476787", "405090876155"]
   ```

3. **skill-state.json に保存**
   ```bash
   TARGET_ROWS_JSON=$(printf '%s\n' "${targetRows[@]}" | jq -R . | jq -s .)
   cat > ~/.claude/skill-state.json << EOF
   {
     "skill": "ebay-sold-count",
     "target_rows": ${TARGET_ROWS_JSON},
     "cursor": 0,
     "total": ${#targetRows[@]},
     "message": "進捗: 0/${#targetRows[@]}件完了、次はアイテム${targetRows[0]}から処理開始。"
   }
   EOF
   ```

**注意**: E列の取得は処理時（Step 4）に行うため、ここでは取得しない。

#### 全件処理時

1. **X列とC列を並列取得**
   ```
   # 並列取得でパフォーマンス最適化
   mcp__google-sheets__get_sheet_data (2回並列実行)
   - range: X:X
   - range: C:C
   ```

2. **アイテム番号リスト生成**（行番号は保存しない）
   - X列で空セルの行を特定
   - その行のC列からアイテム番号を取得
   - アイテム番号のみをリストに追加

   ```javascript
   const targetRows = [];  // アイテム番号のみのリスト

   for (let i = 1; i < columnX.length; i++) {  // Skip header
     // X列が空の場合
     if (!columnX[i] || columnX[i].trim() === "") {
       const itemNumber = columnC[i]?.trim() || "";
       if (itemNumber) {
         targetRows.push(itemNumber);  // アイテム番号のみ追加
       }
     }
   }

   // target_rows: ["403498476787", "405090876155", "403498476788", ...]
   ```

3. **skill-state.json に保存**
   ```bash
   TARGET_ROWS_JSON=$(printf '%s\n' "${targetRows[@]}" | jq -R . | jq -s .)
   cat > ~/.claude/skill-state.json << EOF
   {
     "skill": "ebay-sold-count",
     "target_rows": ${TARGET_ROWS_JSON},
     "cursor": 0,
     "total": ${#targetRows[@]},
     "message": "進捗: 0/${#targetRows[@]}件完了、次はアイテム${targetRows[0]}から処理開始。"
   }
   EOF
   ```

**注意**: E列の取得は処理時（Step 4）に行うため、ここでは取得しない。

**300行制限対応**: X列/C列が300行を超える場合はバッチ取得

```javascript
async function fetchColumnInBatches(column, maxRows = 300) {
  let allData = [];
  let offset = 2;  // Skip header

  while (true) {
    const range = `${column}${offset}:${column}${offset + maxRows - 1}`;
    const batch = await getSheetData({range});
    if (batch.length === 0) break;

    allData = allData.concat(batch);
    if (batch.length < maxRows) break;
    offset += maxRows;
  }
  return allData;
}

// X列とC列をバッチ取得
const [columnX, columnC] = await Promise.all([
  fetchColumnInBatches('X'),
  fetchColumnInBatches('C')
]);
```

#### 大量データの処理時間見積もり

**1000件以上の場合はユーザー確認**:
```
WARNING: 1,250件の処理対象があります。
推定処理時間: 約50分（5件/分 × 250バッチ）
続行しますか？
```

**注意**:
- E列データの取得は Step 4 の処理時に5件バッチごとに実行
- C列データ（アイテム→行マップ）は処理開始時に1回だけ取得
- 処理中断時は skill-state.json から再開可能

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

## Step 4: 並列処理で販売数調査（1バッチ = 5件）

### ⚠️ 重要: 即時書き込みルール

各バッチの処理は以下の順序を**厳守**：

```
1. 5件分のURL構築
2. 5タブに並列ナビゲート
3. 結果取得（90日間）
4. 必要に応じて6ヶ月検索
5. 【必須】スプレッドシートへ5件書き込み
6. 【必須】skill-state.json更新
7. 次のバッチへ進む
```

**禁止事項**: 結果をメモリに蓄積して後でまとめて書き込むこと

---

### 4-0: 初期化とループ準備（アイテム番号ベース）

#### 再開時の境界チェック

skill-state.json が存在する場合、処理完了済みかチェック：

```javascript
if (cursor >= total) {
  console.log("処理完了済み");
  fs.unlinkSync('~/.claude/skill-state.json');
  return;
}
```

#### C列取得とアイテム→行マップ作成

処理開始時に1回だけ実行（各バッチで再取得は不要）：

```javascript
// C列全体を取得
const columnC = await getSheetData({range: "C:C"});

// アイテム番号 → 行番号のマップを作成
const itemToRowMap = {};
columnC.forEach((item, index) => {
  if (item?.trim()) {
    itemToRowMap[item.trim()] = index + 1;  // 1-based indexing
  }
});

// 例: {"403498476787": 33, "405090876155": 45, ...}
```

#### cursorベースのループ

```javascript
while (cursor < total) {
  // 5件バッチ取得
  const batchEnd = Math.min(cursor + 5, total);
  const batchItems = target_rows.slice(cursor, batchEnd);

  // 各アイテムの行番号を解決
  const batchWithRows = batchItems.map(itemNumber => ({
    item: itemNumber,
    row: itemToRowMap[itemNumber]
  }));

  // E列データ取得（該当行のみ）
  const eColumnData = await Promise.all(
    batchWithRows.map(({row}) =>
      getSheetData({range: `E${row}:E${row}`})
    )
  );

  // キーワード抽出
  const keywords = eColumnData.map(([url]) =>
    extractKeywordFromURL(url)
  );

  // 以降、4-1 からの処理を実行...
  // （URL構築、並列ナビゲート、結果取得、書き込み、cursor更新）

  cursor = batchEnd;
}
```

---

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

## Step 5.5: skill-state.json更新（各バッチ後に必須）

各バッチのスプレッドシート書き込み完了後、**必ず**進捗を更新：

```bash
# cursor更新（5件バッチ完了ごとに+5）
CURSOR=$((CURSOR + 5))

# 次のアイテム番号を取得
NEXT_ITEM=$(jq -r ".target_rows[$CURSOR] // \"完了\"" ~/.claude/skill-state.json)

# アトミック書き込み（tmp → rename）
TEMP_FILE="$HOME/.claude/skill-state.json.tmp.$$"
cat > "$TEMP_FILE" << EOF
{
  "skill": "ebay-sold-count",
  "target_rows": $(jq -c '.target_rows' ~/.claude/skill-state.json),
  "cursor": ${CURSOR},
  "total": $(jq -r '.total' ~/.claude/skill-state.json),
  "message": "【重要】まず Skill ツールで skill: ebay-sold-count を実行し、全指示を再ロードすること。進捗: ${CURSOR}/$(jq -r '.total' ~/.claude/skill-state.json)件完了、次はアイテム${NEXT_ITEM}から処理継続。"
}
EOF
mv "$TEMP_FILE" "$HOME/.claude/skill-state.json"
```

**更新項目**:
| 項目 | 説明 |
|------|------|
| `target_rows` | アイテム番号リスト（不変） |
| `cursor` | 処理完了した件数（インデックス） |
| `total` | 処理対象の総件数（不変） |
| `message` | オートコンパクト後の再開指示（次のアイテム番号を含む） |

**重要**:
- cursor は処理済み件数を示すインデックス
- target_rows は変更しない（常に全アイテムリスト）
- アトミック書き込み（tmp → rename）で競合を防止
- この更新により、オートコンパクト発生後もSessionStartフックが正確な再開位置を注入できる

---

## Step 6: LINE通知送信（バッチ分割版）

### 6-1: アイテムリストのバッチ分割

処理完了後、結果を100件ごとに分割:

```bash
# 疑似コード
items = [all_processed_items]
batch_size = 100
batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
total_pages = len(batches)
```

### 6-2: 各バッチの送信ループ

```bash
for page in {1..${total_pages}}; do
  # メッセージ構築
  if [ $page -eq 1 ]; then
    # 1通目: サマリー含む
    message="【eBay販売件数調査完了】[ページ ${page}/${total_pages}]
処理: ${total}件（成功: ${success} / エラー: ${error}）
処理時間: ${duration}

ID: 90日間 / 6ヶ月間
${batch_items}"
  else
    # 2通目以降: アイテムのみ
    message="【eBay販売件数調査】[ページ ${page}/${total_pages}]
ID: 90日間 / 6ヶ月間
${batch_items}"
  fi

  # 続きフッター or URL
  if [ $page -lt $total_pages ]; then
    message="${message}

▼続きは次のメッセージへ"
  else
    message="${message}

結果: https://docs.google.com/spreadsheets/d/1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g"
  fi

  # 送信（リトライ付き - notify-line.sh内で3回リトライ）
  .claude/hooks/notify-line.sh "$message"

  # レート制限対策（最後以外）
  [ $page -lt $total_pages ] && sleep 1
done
```

### メッセージ形式例

**1通目（page 1/3）**:
```
【eBay販売件数調査完了】[ページ 1/3]
処理: 300件（成功: 295 / エラー: 5）
処理時間: 25分

ID: 90日間 / 6ヶ月間
405237152554: 5件 / -
405237187303: 1件 / 3件
405237190822: 0件 / 2件
... (100件まで)

▼続きは次のメッセージへ
```

**2通目（page 2/3）**:
```
【eBay販売件数調査】[ページ 2/3]
ID: 90日間 / 6ヶ月間
405238000001: 12件 / -
... (100件まで)

▼続きは次のメッセージへ
```

**3通目（page 3/3）**:
```
【eBay販売件数調査】[ページ 3/3]
ID: 90日間 / 6ヶ月間
405238200001: 7件 / -
... (残り100件)

結果: https://docs.google.com/spreadsheets/d/1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
```

### エッジケース

**301件処理時**:
- 4メッセージ: 100+100+100+1
- 最後のメッセージは1件のみでもページ表示 "4/4"

**100件以下**:
```
【eBay販売件数調査完了】
処理: 50件（成功: 50 / エラー: 0）
処理時間: 5分

ID: 90日間 / 6ヶ月間
405237152554: 5件 / -
... (50件)

結果: https://docs.google.com/spreadsheets/d/...
```
（ページ表示なし）

**全エラー時**:
```
【eBay販売件数調査完了】
処理: 50件（成功: 0 / エラー: 50）

エラー詳細:
行10: URLエラー
行15: タイムアウト
...
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

## Step 8: skill-state.json削除（完了時必須）

すべての処理が正常完了した後、進捗ファイルを削除：

```bash
rm -f ~/.claude/skill-state.json
```

**重要**:
- 正常完了時のみ削除（エラー中断時は残す）
- 削除しないと次回オートコンパクト時に完了済みスキルの再開指示が注入される

---

## 並列処理のループ（5件単位）

### ループ処理フロー

```
for each バッチ (5件単位):
    1. URL構築（5件分）
    2. 5タブ並列ナビゲート
    3. 結果取得
    4. 6ヶ月検索（必要な場合）
    5. 【必須】スプレッドシート書き込み（5件分）
    6. 【必須】skill-state.json更新
    7. 進捗報告: 「進捗: 20/100件完了（20%）」
    8. 次のバッチへ
```

### 20件ごとのタブリフレッシュ（詳細手順）

**目的**: メモリリーク防止 + chrome://newtab/ 状態回避

**実行タイミング**: 20件、40件、60件...処理完了後（バッチ書き込み後）

**前提条件チェック**:
- ✅ 直前バッチのスプレッドシート書き込み完了
- ✅ skill-state.json 更新完了（lastRow記録済み）
- ✅ 次の開始行番号をメモリに保持

---

#### Step 1: 現在のタブを閉じる

```bash
# 既存の5タブIDを使用してクローズ
for tab_id in "${TAB_IDS[@]}"; do
  echo "Closing tab: $tab_id"
  # MCPツールでタブクローズ
done
```

#### Step 2: 新規タブを5つ作成

```
mcp__claude-in-chrome__tabs_create_mcp × 5回（並列実行可）
```

**保存**: 新タブIDを配列に格納
```
NEW_TAB_IDS=(12345 12346 12347 12348 12349)
```

#### Step 3: 各タブを eBay.com へナビゲート（必須）

**⚠️ 重要**: chrome://newtab/ 状態ではJavaScript実行不可 → 先にeBayへナビゲート

```
mcp__claude-in-chrome__navigate × 5回（並列実行可）
tabId: 12345, url: https://www.ebay.com
tabId: 12346, url: https://www.ebay.com
tabId: 12347, url: https://www.ebay.com
tabId: 12348, url: https://www.ebay.com
tabId: 12349, url: https://www.ebay.com
```

**待機**: ナビゲート完了を待つ
```
mcp__claude-in-chrome__computer
action: wait
duration: 2-3
```

#### Step 4: タイムスタンプを再取得

**理由**: タブリフレッシュ後は新しいタイムスタンプが必要

いずれかのタブで実行:
```javascript
(function() {
  const now = Date.now();
  const start_90d = now - (90 * 24 * 60 * 60 * 1000);
  const start_180d = now - (180 * 24 * 60 * 60 * 1000);
  return JSON.stringify({
    now: now,
    start_90d: start_90d,
    start_180d: start_180d
  });
})()
```

**保存**: 取得したタイムスタンプを変数に保持

#### Step 5: 処理を再開（正しい位置から）

**skill-state.json から再開位置を取得**:
```bash
LAST_ROW=$(jq -r '.progress.lastRow' ~/.claude/skill-state.json)
NEXT_ROW=$((LAST_ROW + 1))
```

**次のバッチを開始**:
- 行 ${NEXT_ROW} から5件分のE列データを取得
- 新しいタイムスタンプでURL構築
- 新しいタブIDで並列ナビゲート

---

### 実行例: 20件完了時のリフレッシュ

```
現在の状態:
- completed: 20件
- lastRow: 44
- 次の処理: 行45-49

リフレッシュ実行:
1. タブ12301-12305をクローズ
2. タブ12401-12405を作成
3. 各タブを ebay.com へナビゲート ← chrome://newtab/回避
4. タイムスタンプ再取得: {now: 1704557000000, ...}
5. 行45から処理再開
```

### エラーハンドリング

**タブ作成失敗**:
```
ERROR: タブ作成に失敗しました
対応: リトライ3回 → 失敗時は処理中断、ユーザー通知
```

**ナビゲート失敗**:
```
WARNING: タブ12401のナビゲート失敗
対応: 該当タブのみ再ナビゲート → 3回失敗で処理中断
```

**タイムスタンプ取得失敗**:
```
ERROR: JavaScript実行失敗（chrome://newtab/ 状態の可能性）
対応: Step 3を再実行 → eBayへの再ナビゲート
```

**skill-state.json 消失**:
```
ERROR: skill-state.json が見つかりません
対応: 最後の書き込み行を手動確認、新規state作成
```

---

## 実行パラメータ

| 指定 | 動作 |
|------|------|
| 「全て」 | X列が空の全行を処理 |
| 行番号指定 | 指定行以降のX列空の行を処理 |
| 件数指定 | 指定件数のみ処理 |
| アイテムナンバー指定 | C列から該当行を検索して処理 |
