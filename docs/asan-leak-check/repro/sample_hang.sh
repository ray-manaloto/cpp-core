#!/bin/zsh
BIN=$1; OUT=$2
cd "$(dirname "$BIN")"
ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 nohup "./$(basename "$BIN")" > "$OUT.run.log" 2>&1 &
PID=$!
sleep 5
if ps -p $PID > /dev/null 2>&1; then
  echo "pid $PID alive; sampling..."
  timeout 20 sample $PID 2 -file "$OUT.sample.txt" > /dev/null 2>&1
  echo "sample rc=$?"
  kill -9 $PID 2>/dev/null
  wait $PID 2>/dev/null
else
  echo "pid $PID exited early"
fi
