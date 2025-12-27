#!/bin/bash
# LINE Messaging API 通知スクリプト
# 使用法: ./notify-line.sh "メッセージ"
#
# 必要な環境変数:
#   LINE_CHANNEL_TOKEN - チャネルアクセストークン
#   LINE_USER_ID - 送信先ユーザーID

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

# メッセージ内の改行とダブルクォートをエスケープ
ESCAPED_MESSAGE=$(echo "$MESSAGE" | sed 's/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed 's/\\n$//')

# LINE Messaging API で送信
RESPONSE=$(curl -s -X POST https://api.line.me/v2/bot/message/push \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LINE_CHANNEL_TOKEN" \
  -d "{
    \"to\": \"$LINE_USER_ID\",
    \"messages\": [{\"type\": \"text\", \"text\": \"$ESCAPED_MESSAGE\"}]
  }")

# レスポンスチェック（sentMessagesが含まれていれば成功）
if echo "$RESPONSE" | grep -q "sentMessages"; then
  echo "OK: LINE通知送信完了"
  exit 0
elif [ -z "$RESPONSE" ] || [ "$RESPONSE" = "{}" ]; then
  echo "OK: LINE通知送信完了"
  exit 0
else
  echo "ERROR: $RESPONSE"
  exit 1
fi
