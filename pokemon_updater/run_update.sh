#!/usr/bin/env bash
# 전체 갱신 cron 래퍼: 중복 실행 방지(flock) + 날짜별 로그
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
mkdir -p logs
LOG="logs/full_$(date +%Y%m%d).log"
exec 9>"/tmp/pokemon_updater_full.lock"
if ! flock -n 9; then
  echo "$(date '+%F %T') 이미 실행 중이므로 종료" >> "$LOG"
  exit 1
fi
PY="${PYTHON:-python3}"
echo "==== $(date '+%F %T') 전체 갱신 시작 ====" >> "$LOG"
"$PY" update_all.py >> "$LOG" 2>&1
RC=$?
echo "==== $(date '+%F %T') 종료 (exit=$RC) ====" >> "$LOG"
exit $RC
