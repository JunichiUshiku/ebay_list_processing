# compare_images.py

Gemini APIを使用して、参照画像と候補商品画像を比較し、同一商品かどうかを判定するCLIツール。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install google-genai pydantic
# または
pip install -r requirements.txt
```

### 2. APIキーの設定

`~/.claude/skills/gemini-extract/.env` に以下を記載（設定済み）:

```
GEMINI_API_KEY=your_api_key_here
```

エージェントからの呼び出し時は `source` で読み込む:

```bash
source ~/.claude/skills/gemini-extract/.env
```

## 使用方法

### 基本実行

```bash
source ~/.claude/skills/gemini-extract/.env

python tools/gemini/compare_images.py \
  --ref "images/Target-Product/405912557904.jpg" \
  --candidates /tmp/mercari_resized_1.png /tmp/mercari_resized_2.png
```

### ワイルドカード使用

```bash
source ~/.claude/skills/gemini-extract/.env

python tools/gemini/compare_images.py \
  --ref "images/Target-Product/405912557904.jpg" \
  --candidates /tmp/mercari_resized_*.png
```

### モデル指定（省略可）

```bash
python tools/gemini/compare_images.py \
  --ref "images/Target-Product/405912557904.jpg" \
  --candidates /tmp/mercari_resized_*.png \
  --model gemini-2.5-flash
```

## 出力形式

成功時（stdout）:

```json
{
  "same_product": true,
  "confidence": "high",
  "best_candidate_index": 0,
  "accessory_status": "complete",
  "missing_accessories": [],
  "notes": ["型番・形状・色が一致"]
}
```

エラー時（stdout、終了コード1）:

```json
{
  "error": "GEMINI_API_KEY 環境変数が未設定です",
  "same_product": false,
  "confidence": "low"
}
```

## フィールド説明

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `same_product` | boolean | 同一商品かどうか |
| `confidence` | string | `"high"` / `"medium"` / `"low"` |
| `best_candidate_index` | integer | 最良候補のインデックス（0始まり） |
| `accessory_status` | string | `"complete"` / `"missing"` / `"unknown"` |
| `missing_accessories` | array | 不足付属品リスト |
| `notes` | array | 判定理由の文字列リスト |

## エージェントからの呼び出し例

```bash
# APIキー読み込み
source ~/.claude/skills/gemini-extract/.env

# 画像比較実行
python tools/gemini/compare_images.py \
  --ref "{reference_image}" \
  --candidates /tmp/mercari_resized_*.png \
  > /tmp/mercari_compare.json

# 結果確認
cat /tmp/mercari_compare.json
```

## エラーハンドリング

| エラー | 対応 |
|--------|------|
| `GEMINI_API_KEY` 未設定 | エラーJSON出力・終了コード1 |
| 参照画像なし | エラーJSON出力・終了コード1 |
| 候補画像なし | エラーJSON出力・終了コード1 |
| API呼び出し失敗 | エラーJSON出力・終了コード1 |
