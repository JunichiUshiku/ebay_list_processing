#!/usr/bin/env python3
"""
compare_images.py - 参照画像 vs 候補画像群の比較CLIツール

Gemini APIを使用して、参照画像と複数の候補画像を比較し、
同一商品かどうかを判定する。結果はJSONとしてstdoutに出力する。

使用方法:
    python tools/gemini/compare_images.py \
        --ref "images/Target-Product/405912557904.jpg" \
        --candidates /tmp/mercari_resized_*.png

環境変数:
    GEMINI_API_KEY: Google Gemini APIキー（必須）
"""

import argparse
import glob
import json
import os
import sys
from pathlib import Path


def load_dotenv():
    """~/.claude/skills/gemini-extract/.env から環境変数を読み込む（未設定キーのみ）"""
    env_path = Path.home() / ".claude/skills/gemini-extract/.env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


# モジュール読み込み時に .env を自動ロード
load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="参照画像と候補画像群を比較し、同一商品かどうかをGemini APIで判定する"
    )
    parser.add_argument(
        "--ref",
        required=True,
        help="参照画像ファイルパス",
    )
    parser.add_argument(
        "--candidates",
        nargs="+",
        required=True,
        help="候補画像ファイルパス（ワイルドカード可）",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="使用するGeminiモデル（デフォルト: gemini-2.5-flash）",
    )
    return parser.parse_args()


def expand_candidates(candidates: list[str]) -> list[str]:
    """ワイルドカードパターンを展開してファイルリストを返す"""
    expanded = []
    for pattern in candidates:
        matched = sorted(glob.glob(pattern))
        expanded.extend(matched)
    return expanded


def load_image_as_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def get_mime_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mime_map.get(ext, "image/jpeg")


def build_prompt(num_candidates: int) -> str:
    candidates_desc = "\n".join(
        f"- 候補画像{i+1}（インデックス{i}）" for i in range(num_candidates)
    )
    return f"""あなたは商品画像の比較専門家です。

以下の画像を比較してください：
- 参照画像（1枚目）: 仕入れ対象の商品
{candidates_desc}

以下の観点で判定してください：

1. **同一商品の判定** (same_product):
   - 参照画像の商品と完全に同一モデルの商品が候補の中にあるか判定
   - 型番・形状・色・デザインが一致する場合に true

2. **確信度** (confidence):
   - high: 型番・形状・色が明確に一致（同一商品確定）
   - medium: 主要特徴は一致するが確証不足
   - low: 同シリーズだが別モデルの可能性がある

3. **最良候補のインデックス** (best_candidate_index):
   - 参照画像に最も近い候補のインデックス（0始まり）
   - same_product が false の場合でも最も近い候補を指定

4. **付属品状態** (accessory_status):
   - complete: 付属品が完全に揃っている
   - missing: 付属品が不足している（本体は同一モデル）
   - unknown: 画像からは判定不能

5. **不足付属品リスト** (missing_accessories):
   - 不足している付属品の名称リスト（例: ["リモコン", "電源ケーブル"]）
   - 不足なし・判定不能の場合は空リスト

6. **判定理由** (notes):
   - 判定の根拠を日本語で記載（例: ["型番XYZ-100が一致", "色が異なる"]）

必ず以下のJSON形式で回答してください（説明文不要）:
{{
  "same_product": true または false,
  "confidence": "high" または "medium" または "low",
  "best_candidate_index": 数値（0始まり）,
  "accessory_status": "complete" または "missing" または "unknown",
  "missing_accessories": [],
  "notes": ["判定理由1", "判定理由2"]
}}"""


def compare_images(ref_path: str, candidate_paths: list[str], model: str) -> dict:
    """Gemini APIを使って画像比較を実行する"""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {
            "error": "google-genai パッケージが未インストールです。pip install google-genai を実行してください",
            "same_product": False,
            "confidence": "low",
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "error": "GEMINI_API_KEY 環境変数が未設定です",
            "same_product": False,
            "confidence": "low",
        }

    client = genai.Client(api_key=api_key)

    # 画像データを構築
    contents = []

    # 参照画像
    ref_bytes = load_image_as_bytes(ref_path)
    ref_mime = get_mime_type(ref_path)
    contents.append(types.Part.from_bytes(data=ref_bytes, mime_type=ref_mime))

    # 候補画像
    for candidate_path in candidate_paths:
        cand_bytes = load_image_as_bytes(candidate_path)
        cand_mime = get_mime_type(candidate_path)
        contents.append(types.Part.from_bytes(data=cand_bytes, mime_type=cand_mime))

    # プロンプト
    prompt = build_prompt(len(candidate_paths))
    contents.append(types.Part.from_text(text=prompt))

    # スキーマファイルの読み込み
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "compare_result.schema.json"

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    result_text = response.text.strip()

    # JSONとしてパース
    result = json.loads(result_text)

    # フィールドの正規化
    if "confidence" in result:
        # "mid" は "medium" に統一
        if result["confidence"] == "mid":
            result["confidence"] = "medium"

    # 必須フィールドのデフォルト値補完
    result.setdefault("same_product", False)
    result.setdefault("confidence", "low")
    result.setdefault("best_candidate_index", 0)
    result.setdefault("accessory_status", "unknown")
    result.setdefault("missing_accessories", [])
    result.setdefault("notes", [])

    return result


def main():
    args = parse_args()

    # 参照画像の存在確認
    if not os.path.exists(args.ref):
        result = {
            "error": f"参照画像が見つかりません: {args.ref}",
            "same_product": False,
            "confidence": "low",
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 候補画像のワイルドカード展開
    candidate_paths = expand_candidates(args.candidates)

    if not candidate_paths:
        result = {
            "error": "候補画像が見つかりません",
            "same_product": False,
            "confidence": "low",
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 存在しないファイルを除外
    candidate_paths = [p for p in candidate_paths if os.path.exists(p)]
    if not candidate_paths:
        result = {
            "error": "候補画像ファイルが存在しません",
            "same_product": False,
            "confidence": "low",
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 画像比較を実行
    result = compare_images(args.ref, candidate_paths, args.model)

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
