#!/bin/bash
STATE_FILE="$HOME/.claude/skill-state.json"

if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
  rm "$STATE_FILE"  # 1回使用したら削除
fi
