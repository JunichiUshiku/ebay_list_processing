# Repository Guidelines

## まず読む
プロジェクト概要やディレクトリ構成は `CLAUDE.md` にまとめています。必ず先に確認し、本ファイルは補足として扱ってください。

## 運用ルール（最小限）
- 重要な作業手順・制約は `CLAUDE.md` を優先します。
- スキル実行ルールは `CLAUDE.md` の指示に従ってください。
- `.env` や `credentials/` の内容は機密情報として扱います。

## 参考コマンド
基本的な操作は `CLAUDE.md` に記載があります。必要に応じて以下を利用してください。

```bash
# スキルパッケージの編集
unzip ebay-sourcing.skill -d ./ebay-sourcing
zip -r ebay-sourcing.skill ebay-sourcing
```

## 変更時の注意
- 変更内容は小さく保ち、影響範囲を明確にします。
- 追加のルールが必要になった場合は、まず `CLAUDE.md` へ追記してください。
