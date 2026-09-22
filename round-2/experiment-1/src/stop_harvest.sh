#!/bin/bash
# Stop ONLY this workspace's harvest workers.
#
# Selection is by /proc/<pid>/cwd resolving to THIS workspace directory, never by
# process name. Several pipeline runs share this machine and `pkill -f method.py`
# would kill their harvests too -- and would match this script's own cmdline.
WS="$(cd "$(dirname "$0")" && pwd)"
found=0
for p in /proc/[0-9]*; do
  [ "$(readlink "$p/cwd" 2>/dev/null)" = "$WS" ] || continue
  cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
  case "$cmd" in *"--stage harvest"*) ;; *) continue ;; esac
  pid=${p#/proc/}
  echo "stopping harvest worker PID=$pid"
  kill "$pid" 2>/dev/null && found=$((found+1))
done
echo "signalled $found worker(s); waiting up to 90s for clean exit"
for _ in $(seq 18); do
  alive=0
  for p in /proc/[0-9]*; do
    [ "$(readlink "$p/cwd" 2>/dev/null)" = "$WS" ] || continue
    cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
    case "$cmd" in *"--stage harvest"*) alive=$((alive+1)) ;; esac
  done
  [ "$alive" -eq 0 ] && { echo "all harvest workers exited"; exit 0; }
  sleep 5
done
echo "WARNING: $alive worker(s) still alive after 90s"
