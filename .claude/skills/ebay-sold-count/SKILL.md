---
name: ebay-sold-count
description: eBay販売履歴件数調査ワークフロー（並列処理版）。スプレッドシートのE列eBay検索URLからキーワードを抽出し、eBay Seller Hub Product Researchで90日間の販売件数を調べてX列に記録。「販売件数を調べて」「sold count」「リサーチ」で全件処理。アイテムナンバー指定時はC列から検索。
---

# eBay販売件数調査（並列処理版）

## CRITICAL RULES

1. **参照ファイル必読**: 処理前に `references/selectors.md` を読み込む
2. **タブ作成後ナビゲート必須**: 新規タブは `chrome://newtab/` でJS実行不可 → eBayへ先にナビゲート
3. **タイムスタンプ動的取得**: JSで数値のみ取得、URLはClaude側で構築（URL文字列はMCPでブロック）
4. **URL保持必須**: 生成したURLを保持しHYPERLINK作成に再利用（`window.location.href`は使用不可）
5. **データ取得制約（重要）**: トークン制限回避のため、必要最小限の列のみを取得
   - アイテムナンバー指定時: C列全行 → 該当行のE列のみ
   - 全件処理時: X列全行 → 空セルの行のE列のみ
   - ❌ 禁止例: `range: C:Y`、`range: A:Z`
   - ✅ 正解例: `range: C:C`、`range: E15:E15`
   - **E列バッチ取得上限: 最大300行**（超過時は分割取得、詳細は workflow-detail.md 参照）
6. **LINE通知必須**: 処理完了後に必ずLINE通知を送信
7. **即時書き込み必須（最重要）**: 各バッチ（5件）の検索完了後、**次のバッチに進む前に**必ずスプレッドシートへ書き込む
   - ❌ 禁止: 複数バッチの結果をメモリに保持して後でまとめて書き込む
   - ✅ 必須: 5件検索 → 5件書き込み → 進捗更新 → 次の5件検索...
   - 理由: オートコンパクト時のデータ損失防止
8. **進捗記録必須**: 各バッチ書き込み後に `skill-state.json` を更新（オートコンパクト後の再開用）
9. **20件ごとのタブリフレッシュ必須**: メモリリーク防止と chrome://newtab/ 状態回避
   - 詳細: [references/workflow-detail.md#20件ごとのタブリフレッシュ](references/workflow-detail.md)

---

## ワークフロー

TodoWriteで以下を登録し進捗追跡:

- [ ] **Step 0: skill-state.json作成**（必須・最初に実行）
- [ ] 参照ファイル読み込み（selectors.md）
- [ ] データ取得・処理対象特定（total件数を確定）
- [ ] 5タブ作成 + eBayナビゲート
- [ ] 並列処理で販売数調査（5件単位 → 即時書き込み → 進捗更新）
- [ ] LINE通知送信
- [ ] サマリー報告
- [ ] **Step 8: skill-state.json削除**（正常完了時のみ）

**詳細手順**: [references/workflow-detail.md](references/workflow-detail.md)

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

## 処理フロー概要

```
[Step 0: 進捗記録初期化]
0. skill-state.json作成（completed:0, total:0）

[初期化]
1. TodoWrite登録 → 参照ファイル読み込み → データ取得
2. skill-state.json更新（total件数を記録）
3. 5タブ作成 → 各タブをeBayへナビゲート

[並列処理ループ]（5件単位）
4. タイムスタンプ取得（JS: 数値のみ）
5. Claude側でURL構築 → 保持
6. 5タブに並列ナビゲート
7. Total Sold取得 → 90日<2なら6ヶ月再検索
8. **【即時書き込み】** スプレッドシートへ5件書き込み
9. **【進捗更新】** skill-state.json更新（completed+5, lastRow更新）
10. 次のバッチへ

[完了]
11. LINE通知送信 → サマリー報告
12. skill-state.json削除（正常完了時のみ）
```

---

## エラーハンドリング

| エラー | 対応 | 続行 |
|--------|------|------|
| ログイン切れ/CAPTCHA | 処理中断、ユーザー通知 | ❌ |
| 検索結果なし | 0として記録（リンク付き） | ✅ |
| タイムアウト/DOM未検出 | リトライ3回 | ✅ |
| URL形式不正 | 「URLエラー」記録 | ✅ |

**詳細**: [references/error-handling.md](references/error-handling.md)

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

※環境変数未設定時のみスキップ

---

## 参照ドキュメント

| ファイル | 内容 |
|----------|------|
| [references/selectors.md](references/selectors.md) | タイムスタンプ取得、URL構築、DOMセレクター |
| [references/workflow-detail.md](references/workflow-detail.md) | 各ステップの詳細手順 |
| [references/error-handling.md](references/error-handling.md) | エラー検出・リトライ戦略 |

---

## 前提条件

- Google Sheets MCP設定済み
- eBay Seller Hubログイン済み
- Claude in Chrome拡張有効
