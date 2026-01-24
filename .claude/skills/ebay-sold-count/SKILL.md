---
name: ebay-sold-count
description: eBay販売履歴件数調査ワークフロー（サブエージェント並列処理版）。スプレッドシートのE列eBay検索URLからキーワードを抽出し、eBay Seller Hub Product Researchで90日間の販売件数を調べてX列に記録。「販売件数を調べて」「sold count」「リサーチ」で全件処理。アイテムナンバー指定時はC列から検索。6件以上はサブエージェント並列起動で高速化。
---

# eBay販売件数調査（サブエージェント並列処理版）

## CRITICAL RULES

1. **参照ファイル必読**: 処理開始前に以下を必ず全て読み込む
   - `references/selectors.md` - URL構築・DOM操作・タイムスタンプ取得
   - `references/workflow-detail.md` - 詳細手順・進捗管理・バッチ処理
   - `references/error-handling.md` - エラー検出・リトライ・通知
   - `references/parallel-processing.md` - 並列処理仕様（6件以上の場合）

2. **処理モード判定必須**: 処理対象件数により自動判定
   - 5件以下: シングルモード（従来通り）
   - 6件以上: パラレルモード（サブエージェント並列）

3. **⚠️ 6件以上は必ずTaskツールでサブエージェント起動**:
   - **禁止**: メインエージェントが自分で全件処理すること
   - **必須**: Taskツールで `subagent_type: "general-purpose"` を使用し、並列起動
   - **起動失敗時**: 最大3回リトライ → 失敗ならメインエージェントがフォールバック
   - 詳細: workflow-detail.md Step 3-P-6, Step 3-P-7 参照

4. **即時書き込み必須**: 5件バッチ完了後、次のバッチ前に必ずスプレッドシート書き込み
   - 理由: オートコンパクト時のデータ損失防止
   - 詳細: workflow-detail.md 参照

5. **進捗記録必須**: 各バッチ書き込み後に skill-state.json 更新
   - 詳細: workflow-detail.md Step 5.5 参照

---

## 処理モード判定

| 条件 | モード | 説明 |
|------|--------|------|
| total <= 5 | シングル | メインエージェントが5タブで処理 |
| total > 5 | パラレル | サブエージェント並列起動（最大5エージェント） |

### エージェント数計算

```javascript
const agentCount = Math.min(Math.ceil(total / 5), 5);
```

| 処理件数 | エージェント数 |
|---------|--------------|
| 1-5件 | シングルモード |
| 6-10件 | 2 |
| 11-15件 | 3 |
| 16-20件 | 4 |
| 21件以上 | 5 |

詳細: [references/parallel-processing.md](references/parallel-processing.md)

---

## ワークフロー

TodoWriteで以下を登録し進捗追跡:

### シングルモード（5件以下）

- [ ] **Step 0: skill-state.json作成**（必須・最初に実行）
- [ ] 参照ファイル読み込み（selectors.md, workflow-detail.md, error-handling.md）
- [ ] データ取得・処理対象特定（total件数を確定）
- [ ] 5タブ作成 + eBayナビゲート
- [ ] 並列処理で販売数調査（5件単位 → 即時書き込み → 進捗更新）
- [ ] LINE通知送信
- [ ] サマリー報告
- [ ] **Step 8: skill-state.json削除**（正常完了時のみ）

### パラレルモード（6件以上）

- [ ] **Step 0: skill-state.json作成**（必須・最初に実行）
- [ ] 参照ファイル読み込み（+ parallel-processing.md）
- [ ] データ取得・処理対象特定（total件数を確定）
- [ ] **Step 3-P: サブエージェント準備**
  - [ ] エージェント数計算・アイテム分割
  - [ ] C列取得（item_to_row_map作成）
  - [ ] タブ作成（エージェント数 × 5タブ）
  - [ ] タイムスタンプ取得
  - [ ] Taskツールでサブエージェント並列起動
- [ ] **Step 4-P: 結果統合**
- [ ] LINE通知送信
- [ ] サマリー報告
- [ ] **Step 8: skill-state.json削除**（正常完了時のみ）

**詳細手順**: [references/workflow-detail.md](references/workflow-detail.md)
**並列処理仕様**: [references/parallel-processing.md](references/parallel-processing.md)

---

## スプレッドシート定義

| 項目 | 値 |
|------|-----|
| ID | `1pmbzGCHCqd0EiyuJBl6rfUEGXVITcBDMGPg9bQ67d-g` |
| シート | `AI作業用` |

| 列 | 内容 | 備考 |
|----|------|------|
| C | eBay Item Number | アイテム指定時の検索対象 |
| E | eBay検索URL | `_nkw=`からキーワード抽出 |
| X | 販売数（90日間） | 値あり→スキップ |
| Y | 販売数（6ヶ月間） | X列が2未満の場合のみ |

---

## エラーハンドリング

詳細は [references/error-handling.md](references/error-handling.md) を参照。

---

## 実行パラメータ

| 指定 | 動作 |
|------|------|
| 全件 | X列空の全行を処理 |
| アイテムナンバー | C列から該当行を検索して処理 |
| 件数指定 | 指定件数のみ処理 |

---

## MCP制限への対応

| 制限 | 対応方法 |
|------|----------|
| `chrome://newtab/`でJS実行不可 | タブ作成後eBayへナビゲート |
| URL文字列の戻り値ブロック | タイムスタンプ（数値）のみ取得、URLはClaude側で構築 |
| `window.location.href`ブロック | URL生成時に保持、HYPERLINK用に再利用 |

---

## LINE通知

### CRITICAL: 実装必須ルール

1. **スクリプト実行必須**: 必ず `.claude/hooks/notify-line.sh` を実行して送信
2. **環境変数**: `.env` の `LINE_CHANNEL_TOKEN` と `LINE_USER_ID` のみ使用
3. **禁止事項**: `LINE_NOTIFY_TOKEN` の使用禁止（LINE Notify サービスは使わない）
4. **エラー判定**: スクリプトが `exit 1` を返した場合のみ環境変数エラーと報告
   - `exit 1` の場合は **LINE通知をスキップして処理継続**
   - `exit 0` の場合は成功扱い（リトライ失敗でも処理継続）

### 送信仕様

処理完了後に必ず実行。**100件ごとに分割送信**（大量処理時のメッセージ長制限対策）。

### バッチ送信ルール

| 処理件数 | メッセージ数 | ページ表示 |
|---------|-------------|-----------|
| 1-100件 | 1通 | なし |
| 101-200件 | 2通 | 1/2, 2/2 |
| 201-300件 | 3通 | 1/3, 2/3, 3/3 |
| 301件以上 | 4通以上 | 1/4, 2/4... |

### 表示ルール

※処理した全アイテムをリスト表示
  - 90日間 < 2: 「ID: X件 / Y件」（6ヶ月検索を実行）
  - 90日間 >= 2: 「ID: X件 / -」（6ヶ月検索を実行せず）

### 詳細手順

詳細手順: [references/workflow-detail.md#step-6-line通知送信](references/workflow-detail.md)

---

## 参照ドキュメント

| ファイル | 内容 |
|----------|------|
| [references/selectors.md](references/selectors.md) | タイムスタンプ取得、URL構築、DOMセレクター |
| [references/workflow-detail.md](references/workflow-detail.md) | 各ステップの詳細手順 |
| [references/error-handling.md](references/error-handling.md) | エラー検出・リトライ戦略 |
| [references/parallel-processing.md](references/parallel-processing.md) | サブエージェント並列処理仕様 |

## サブエージェント定義

| ファイル | 内容 |
|----------|------|
| [.claude/agents/ebay-sold-count-worker.md](../../agents/ebay-sold-count-worker.md) | サブエージェント定義 |

---

## 前提条件

- Google Sheets MCP設定済み
- eBay Seller Hubログイン済み
- Claude in Chrome拡張有効
