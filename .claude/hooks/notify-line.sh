#!/bin/bash
# LINE Messaging API 通知スクリプト
# 使用法: ./notify-line.sh "メッセージ"
#
# 環境変数の読み込み元:
#   1. プロジェクトの .env ファイル
#   2. シェル環境変数

# スクリプトのディレクトリからプロジェクトルートの.envを読み込む
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
  export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

LINE_CHANNEL_TOKEN="${LINE_CHANNEL_TOKEN}"
LINE_USER_ID="${LINE_USER_ID}"
MESSAGE="$1"

# 環境変数チェック
if [ -z "$LINE_CHANNEL_TOKEN" ]; then
  echo "ERROR: LINE_CHANNEL_TOKEN が設定されていません"
  exit 1
fi

if [ -z "$LINE_USER_ID" ]; then
  echo "ERROR: LINE_USER_ID が設定されていません"
  exit 1
fi

if [ -z "$MESSAGE" ]; then
  echo "ERROR: メッセージが指定されていません"
  exit 1
fi

# レスポンスチェック関数
check_response() {
  local response="$1"
  if echo "$response" | grep -q "sentMessages"; then
    return 0
  elif [ -z "$response" ] || [ "$response" = "{}" ]; then
    return 0
  else
    return 1
  fi
}

# リトライループ（最大3回、指数バックオフ）
MAX_RETRIES=3
RETRY_DELAY=2

for attempt in $(seq 1 $MAX_RETRIES); do
  RESPONSE=$(node -e "
const msg = process.argv[1];
const userId = process.argv[2];
console.log(JSON.stringify({
  to: userId,
  messages: [{type: 'text', text: msg}]
}));
" "$MESSAGE" "$LINE_USER_ID" | curl -s -X POST https://api.line.me/v2/bot/message/push \
  -H "Content-Type: application/json; charset=UTF-8" \
  -H "Authorization: Bearer $LINE_CHANNEL_TOKEN" \
  --data-binary @-)

  if check_response "$RESPONSE"; then
    echo "OK: LINE通知送信完了 (試行回数: $attempt/$MAX_RETRIES)"
    exit 0
  else
    echo "WARNING: LINE通知送信失敗 (試行 $attempt/$MAX_RETRIES): $RESPONSE" >&2
    if [ $attempt -lt $MAX_RETRIES ]; then
      echo "INFO: ${RETRY_DELAY}秒後にリトライします..." >&2
      sleep $RETRY_DELAY
      RETRY_DELAY=$((RETRY_DELAY * 2))  # 指数バックオフ: 2s → 4s → 8s
    fi
  fi
done

# 全リトライ失敗 → ログのみ、ワークフロー継続（exit 0）
echo "ERROR: LINE通知送信が${MAX_RETRIES}回失敗しました。最後のレスポンス: $RESPONSE" >&2
echo "INFO: 処理結果はスプレッドシートに記録されています。"
exit 0  # ← ワークフロー継続のため0を返す
