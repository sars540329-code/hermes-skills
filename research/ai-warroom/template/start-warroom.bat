@echo off
chcp 65001 >nul
title AI 戰情室（關掉這個視窗就停止）
set "PY=%USERPROFILE%\.ai-warroom\venv\Scripts\python.exe"
if not exist "%PY%" (
  echo 找不到戰情室的 Python 環境：%PY%
  echo 請回到 Claude，跟它說「用 ai-warroom 幫我修好戰情室」。
  pause
  exit /b 1
)
"%PY%" "%~dp0warroom.py" %*
pause
