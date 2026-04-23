#!/usr/bin/env bash

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/app/docker/runtime-common.sh
. "${SCRIPT_DIR}/runtime-common.sh"

CLEANUP_INTERVAL_SECONDS="${CLEANUP_INTERVAL_SECONDS:-900}"
CLEANUP_RUN_ON_START="${CLEANUP_RUN_ON_START:-true}"
CLEANUP_TASKS_VALUE="${CLEANUP_TASKS:-}"

prepare_runtime_environment
wait_for_database_command "from app.core.init_db import create_tables; create_tables()"

run_cleanup_once() {
  if [ -n "${CLEANUP_TASKS_VALUE}" ]; then
    read -r -a cleanup_tasks <<< "${CLEANUP_TASKS_VALUE}"
    python -m app.cleanup_cli "${cleanup_tasks[@]}"
    return
  fi

  python -m app.cleanup_cli
}

sleep_with_signal_handling() {
  sleep "${CLEANUP_INTERVAL_SECONDS}" &
  wait $!
}

trap 'exit 0' INT TERM

if [ "${CLEANUP_RUN_ON_START}" = "true" ]; then
  run_cleanup_once
fi

while true; do
  sleep_with_signal_handling
  run_cleanup_once
done
