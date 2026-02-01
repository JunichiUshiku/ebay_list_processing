# プロジェクトルール

## eBay仕入れ処理

ユーザーから以下のような処理指示があった場合は、**必ず Skill ツールで `ebay-sourcing` を実行すること**：

- 「仕入れ先を探して」
- 「在庫仕入れ」
- 「国内サイトで検索」
- アイテムIDを指定した処理依頼
- スプレッドシートの商品検索依頼

### 禁止事項

- SKILL.mdの内容を「参考情報」として自己判断で処理を進めることは禁止
- スキルを実行せずにブラウザ操作だけで処理を完了させることは禁止

### 正しい実行方法

```
Skill ツール
skill: "ebay-sourcing"
```

これにより、SKILL.mdに定義された11サイト一括検索などのワークフローが確実に実行される。

## eBay販売件数調査

ユーザーから以下のような処理指示があった場合は、**必ず Skill ツールで `ebay-sold-count` を実行すること**：

**全件処理（X列が空の行すべて）**:
- 「販売件数を調べて」
- 「sold count」
- 「90日間の販売数」
- 「リサーチ」
- 「販売履歴」
- スプレッドシートの販売数調査依頼

**アイテムナンバー指定（C列から該当行を検索）**:
- 「{アイテムナンバー}の販売数を調べて」
- 複数アイテムナンバーを改行区切りで指定した場合
- 例: 「403498476787、405090876155の販売数」

### 正しい実行方法

```
Skill ツール
skill: "ebay-sold-count"
```

これにより、SKILL.mdに定義されたeBay Product Research検索と販売件数記録のワークフローが確実に実行される。

## ブラウザ操作の優先順位

ブラウザを使用する際は、以下の優先順位で選択すること：

### 1. agent-browser（優先）

```bash
agent-browser open <url>
agent-browser snapshot -i
agent-browser click @e1
```

**利点**:
- コンパクトな出力（ref付きで操作しやすい）
- `--profile` オプションで認証状態を永続化可能
- `--session` オプションで並列セッション管理可能

### 2. Claude in Chrome（フォールバック）

以下の場合にのみ Claude in Chrome を使用：

- agent-browser でページが正常に読み込めない場合
- 複雑なJavaScript操作が必要な場合
- リアルタイムのDOM監視が必要な場合
- agent-browser がインストールされていない環境

```
mcp__claude-in-chrome__navigate
mcp__claude-in-chrome__read_page
mcp__claude-in-chrome__computer
```

### 3. Playwright MCP（特殊用途）

テスト自動化や特殊なブラウザ制御が必要な場合：

```
mcp__playwright__browser_navigate
mcp__playwright__browser_snapshot
```

---

## Claude in Chrome MCP セキュリティ制限

Claude in Chrome MCPは、セキュリティ対策として以下のデータをJavaScript実行結果（javascript_tool）として返すことをブロックする：

- URLやクエリ文字列を含むデータ
- クッキー情報
- セッション情報

### ブロックされる操作例

| 操作 | コード例 | 結果 |
|------|---------|------|
| URL取得 | `window.location.href` | ブロック |
| URL含むJSON | `JSON.stringify({url: location.href})` | ブロック |
| クエリ文字列 | `location.search` | ブロック |

### 代替方法

1. **URL生成時に保持**: ナビゲート用URLを生成した時点で変数に保持
2. **結果取得は数値・テキストのみ**: javascript_toolでは数値やテキストのみ取得
3. **保持したURLを再利用**: HYPERLINKなどに使用する場合は保持済みURLを使用
