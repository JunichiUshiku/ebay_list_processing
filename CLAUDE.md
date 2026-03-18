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

**リストID指定（A列から該当行を検索）**:
- 14桁の数値ID（例: 20200915100021）を指定した場合
- 複数リストIDを改行区切りで指定した場合

**アイテムナンバー指定（C列から該当行を検索）**:
- 12桁のeBayアイテムナンバー（例: 402439432345）を指定した場合
- 複数アイテムナンバーを改行区切りで指定した場合

### 正しい実行方法

```
Skill ツール
skill: "ebay-sold-count"
```

これにより、SKILL.mdに定義されたeBay Product Research検索と販売件数記録のワークフローが確実に実行される。

## ブラウザ操作ルール

### agent-browser を使用すること（必須）

```bash
agent-browser open <url>
agent-browser snapshot -i
agent-browser click @e1
```

**利点**:
- コンパクトな出力（ref付きで操作しやすい）
- `--profile` オプションで認証状態を永続化可能
- `--session` オプションで並列セッション管理可能

### Claude in Chrome（mcp__claude-in-chrome__*）は使用禁止

**ユーザーが明示的に言及しない限り、Claude in Chrome の使用は絶対禁止。**
SKILL.mdやエージェント定義に記載があっても、agent-browser で実行すること。

### Playwright MCP（mcp__playwright__*）も使用禁止

**ユーザーが明示的に言及しない限り、Playwright MCP の使用は絶対禁止。**

---

## Gemini API 画像比較ツール

マッチャーエージェントの画像比較処理は Gemini API に委譲する（Claudeコンテキストへの画像読み込み禁止）。

### 実行方法

```bash
source ~/.claude/skills/gemini-extract/.env
python tools/gemini/compare_images.py \
  --ref {reference_image} \
  --candidates /tmp/{site}_resized_*.{ext} \
  > /tmp/{site}_compare.json
cat /tmp/{site}_compare.json
```

### 対応エージェントと拡張子

| エージェント | ワイルドカードパターン |
|------------|---------------------|
| mercari / yahoo / rakuma / hardoff / surugaya | `/tmp/{site}_resized_*.png` |
| paypay | `/tmp/paypay_resized_*.jpg` |

### ルール

- **Read ツールで画像を読み込むことは禁止**（トークン節約のため）
- APIキーは `~/.claude/skills/gemini-extract/.env` から `source` で読み込む
- 詳細: `tools/gemini/README.md`

---

## Claude in Chrome / Playwright 参考情報

Claude in Chrome・Playwright MCPは使用禁止（上記「ブラウザ操作ルール」参照）。
ユーザーが明示的に使用を指示した場合のみ、以下の制限に注意：

### Claude in Chrome セキュリティ制限

- javascript_toolでURL・クッキー・セッション情報を含むデータの返却がブロックされる
- 代替: URL生成時に変数保持、結果取得は数値・テキストのみ
