# 並列処理仕様

## ⚠️ CRITICAL: 必須事項

**6件以上の処理対象がある場合、以下は必須です**:

1. **Taskツール使用必須**: メインエージェントが自分で処理を続行することは**禁止**
2. **サブエージェント並列起動**: `subagent_type: "general-purpose"` で起動
3. **単一メッセージで複数起動**: 全Taskツール呼び出しを1つのレスポンスで送信

**禁止事項**:
- ❌ メインエージェントが6件以上を自分でループ処理
- ❌ サブエージェントを1つずつ順番に起動
- ❌ Taskツールを使わずにブラウザ操作を継続

---

## 概要

5件を超える処理対象がある場合、Taskツールを使用してサブエージェントを並列起動する。
各サブエージェントは最大5件を担当し、即時スプレッドシート書き込みを行う。

---

## 処理モード判定

| 条件 | モード | 説明 |
|------|--------|------|
| total <= 5 | シングル | 従来通りメインエージェントが処理 |
| total > 5 | パラレル | **必ず**Taskツールでサブエージェント並列起動 |

---

## エージェント数計算ロジック

```javascript
function calculateAgentCount(totalItems) {
  const itemsPerAgent = 5;
  const maxAgents = 5;
  const requiredAgents = Math.ceil(totalItems / itemsPerAgent);
  return Math.min(requiredAgents, maxAgents);
}

// 例:
// 3件 → 1エージェント（シングルモード）
// 5件 → 1エージェント（シングルモード）
// 6件 → 2エージェント
// 10件 → 2エージェント
// 15件 → 3エージェント
// 25件 → 5エージェント
// 100件 → 5エージェント（各20件）
```

### 件数別エージェント配分

| 処理件数 | エージェント数 | 配分 |
|---------|--------------|------|
| 1-5件 | シングルモード | - |
| 6-10件 | 2 | 5件 + 残り |
| 11-15件 | 3 | 5件 × 3 |
| 16-20件 | 4 | 5件 × 4 |
| 21-25件 | 5 | 5件 × 5 |
| 26件以上 | 5 | 均等分割 |

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    メインエージェント                        │
│                                                             │
│  Step 0: skill-state.json作成                               │
│  Step 1: 参照ファイル読み込み                                │
│  Step 2: データ取得・処理対象特定                            │
│  Step 3: 処理モード判定                                      │
│           │                                                 │
│           ├─ total <= 5 ──→ シングルモード（Step 4へ）       │
│           │                                                 │
│           └─ total > 5 ──→ パラレルモード                   │
│                    │                                        │
│  Step 3-P: サブエージェント準備                              │
│    3-P-1: エージェント数計算                                 │
│    3-P-2: アイテム分割                                       │
│    3-P-3: C列取得（item_to_row_map作成）                    │
│    3-P-4: タイムスタンプ取得                                 │
│    3-P-5: Taskツールで並列起動                               │
│           （タブ作成はサブエージェント側）                    │
│           │                                                 │
│           │ 並列実行                                         │
│           ↓                                                 │
│  ┌────────┴────────┬────────┬────────┬────────┐            │
│  ▼                 ▼        ▼        ▼        ▼            │
│  SubAgent1       SubAgent2  ...   SubAgent5                │
│  5件処理          5件処理          5件処理                   │
│  ↓                ↓               ↓                        │
│  即時書込         即時書込         即時書込                   │
│  └────────────────┴────────────────┘                        │
│                    ↓                                        │
│  Step 4-P: 結果統合                                         │
│  Step 5: LINE通知送信                                       │
│  Step 6: サマリー報告                                        │
│  Step 7: skill-state.json削除                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 3-P: サブエージェント準備

### 3-P-1: エージェント数計算

```javascript
const total = target_rows.length;
const agentCount = Math.min(Math.ceil(total / 5), 5);
```

### 3-P-2: アイテム分割

```javascript
function divideItems(items, agentCount) {
  const result = [];
  const baseSize = Math.floor(items.length / agentCount);
  const extra = items.length % agentCount;

  let start = 0;
  for (let i = 0; i < agentCount; i++) {
    // 余りを先頭のエージェントに1つずつ配分
    const size = baseSize + (i < extra ? 1 : 0);
    result.push(items.slice(start, start + size));
    start += size;
  }
  return result;
}

// 例: 12件を3エージェントで分割
// → [[item1-4], [item5-8], [item9-12]]  // 4件, 4件, 4件

// 例: 27件を5エージェントで分割
// → [[6件], [6件], [5件], [5件], [5件]]
```

### 3-P-3: C列取得とマップ作成

```
mcp__google-sheets__get_sheet_data
spreadsheet_id: 1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g
sheet: AI作業用
range: C:C
```

```javascript
const itemToRowMap = {};
columnC.forEach((item, index) => {
  if (item?.trim()) {
    itemToRowMap[item.trim()] = index + 1;  // 1-based
  }
});
```

### 3-P-4: タイムスタンプ取得

**注意**: タブ作成はサブエージェント側で実行。各サブエージェントが自分で5タブを作成・管理するため、メインエージェントはタブを作成しない。

```javascript
(function() {
  const now = Date.now();
  const start_90d = now - (90 * 24 * 60 * 60 * 1000);
  const start_180d = now - (180 * 24 * 60 * 60 * 1000);
  return JSON.stringify({now, start_90d, start_180d});
})()
```

### 3-P-5: Taskツールで並列起動

**注意**: タブIDは渡さない（サブエージェント側で各自5タブを作成）

```
# 全エージェントを単一メッセージで並列起動
# ※ tab_ids パラメータは削除（サブエージェント側でタブ作成）
Task(
  description: "エージェント1: 5件リサーチ",
  prompt: `
    ebay-sold-count-worker サブエージェントとして実行。

    ## 入力パラメータ
    agent_id: 1
    assigned_items: ["item1", "item2", "item3", "item4", "item5"]
    item_to_row_map: {"item1": 33, "item2": 45, ...}
    timestamps: {"now": 1704557000000, "start_90d": ..., "start_180d": ...}

    ## 実行手順
    1. .claude/agents/ebay-sold-count-worker.md を読み込む
    2. 指示に従って処理を実行
    3. 結果JSONを返却
  `,
  subagent_type: "general-purpose"
)

Task(
  description: "エージェント2: 5件リサーチ",
  prompt: ...同様...,
  subagent_type: "general-purpose"
)

// ... 必要なエージェント数分
```

---

## Step 4-P: 結果統合

全サブエージェントの結果を統合：

```javascript
const allResults = [agent1Result, agent2Result, ...];

const summary = {
  total: 0,
  success: 0,
  error: 0,
  six_month_searched: 0
};

const processedItems = [];

for (const result of allResults) {
  if (result.success) {
    summary.total += result.summary.total;
    summary.success += result.summary.success;
    summary.error += result.summary.error;
    summary.six_month_searched += result.summary.six_month_searched;
    processedItems.push(...result.processed);
  } else {
    // エージェント失敗の場合
    summary.error += result.summary?.total || 0;
  }
}
```

---

## skill-state.json（パラレルモード）

```json
{
  "skill": "ebay-sold-count",
  "mode": "parallel",
  "target_rows": ["item1", "item2", ...],
  "cursor": 0,
  "total": 25,
  "agent_count": 5,
  "agent_status": {
    "1": "running",
    "2": "running",
    "3": "completed",
    "4": "running",
    "5": "running"
  },
  "message": "並列処理モード: 5エージェント起動中 (1/5完了)"
}
```

---

## タブ管理

### シングルモード
- 5タブ固定
- メインエージェントが管理

### パラレルモード
- 各サブエージェントが自分で5タブを作成・管理
- メインエージェントはタブを作成しない
- タブ競合は発生しない（各エージェントが独立してタブを作成）

### サブエージェント側のタブ作成手順

各サブエージェントは処理開始時に以下を実行：
1. `mcp__claude-in-chrome__tabs_context_mcp` で初期化
2. `mcp__claude-in-chrome__tabs_create_mcp` × 5回でタブ作成
3. `mcp__claude-in-chrome__navigate` × 5回でeBayへナビゲート

---

## エラーハンドリング

### サブエージェント起動失敗時のリトライ

| 状況 | 対応 |
|------|------|
| 一部エージェント起動失敗 | 失敗分のみ再起動（最大3回） |
| 3回リトライ後も失敗 | **メインエージェントがその分を担当** |
| 全エージェント起動失敗 | メインエージェントが全件処理 |

**リトライフロー**:
```
初回起動 → 失敗検知 → リトライ1 → 失敗 → リトライ2 → 失敗 → リトライ3 → 失敗
→ メインエージェントがフォールバック処理
```

### サブエージェント単体の失敗（起動後）

| エラー | 対応 |
|--------|------|
| 一部アイテム失敗 | 失敗分を記録、他は続行 |
| ログイン切れ | 該当エージェント中断、結果返却 |
| CAPTCHA | 該当エージェント中断、結果返却 |
| タイムアウト | リトライ3回後にエラー記録 |

### 全エージェント失敗時

```javascript
if (allResults.every(r => !r.success)) {
  // フォールバック: シングルモードで再試行
  console.log("全エージェント失敗 → シングルモードで再試行");
  // skill-state.json を更新してシングルモード実行
}
```

---

## パフォーマンス

### 期待される処理時間

| 件数 | シングル | パラレル | 短縮率 |
|------|---------|---------|--------|
| 5件 | 5分 | - | - |
| 10件 | 10分 | 5分 | 50% |
| 25件 | 25分 | 5分 | 80% |
| 100件 | 100分 | 20分 | 80% |

※ 1件あたり約1分として計算

---

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| `.claude/agents/ebay-sold-count-worker.md` | サブエージェント定義 |
| `references/workflow-detail.md` | 詳細ワークフロー |
| `references/selectors.md` | URL構築・DOM操作 |
| `references/error-handling.md` | エラーハンドリング |
