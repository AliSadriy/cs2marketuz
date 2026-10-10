#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$(realpath "$0")")"
mkdir -p logs

# .env ixtiyoriy: systemd EnvironmentFile yoki shell muhiti ham ishlaydi.
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${MINIAPP_HOST:=127.0.0.1}"
: "${MINIAPP_PORT:=8080}"
: "${MINIAPP_DEV_MODE:=0}"
export MINIAPP_HOST MINIAPP_PORT MINIAPP_DEV_MODE

pids=()
stop_all() {
  trap - TERM INT EXIT
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop_all TERM INT EXIT

run_forever() {
  local name="$1"; shift
  local delay=3
  while true; do
    printf '%s %s starting\n' "$(date -Is)" "$name" >>"logs/${name}.log"
    "$@" >>"logs/${name}.log" 2>&1 || true
    printf '%s %s stopped; restart in %ss\n' "$(date -Is)" "$name" "$delay" >>"logs/${name}.log"
    sleep "$delay"
  done
}

run_forever miniapp python3 api_server.py & pids+=("$!")
run_forever bot python3 bot.py & pids+=("$!")

printf 'CS2MarketUZ: bot va Mini App API ishga tushdi (API port: %s)\n' "$MINIAPP_PORT"
wait
