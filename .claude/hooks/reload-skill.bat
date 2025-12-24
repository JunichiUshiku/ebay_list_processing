@echo off
set STATE_FILE=%USERPROFILE%\.claude\skill-state.json
if exist "%STATE_FILE%" (
  type "%STATE_FILE%"
  del "%STATE_FILE%"
)
