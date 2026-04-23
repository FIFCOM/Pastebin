#!/usr/bin/env bash

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/app/docker/runtime-common.sh
. "${SCRIPT_DIR}/runtime-common.sh"

HOST_VALUE="${HOST:-0.0.0.0}"
PORT_VALUE="${PORT:-8000}"

prepare_runtime_environment
wait_for_database_command "from app.core.init_db import create_tables; create_tables()"

exec uvicorn main:app --host "${HOST_VALUE}" --port "${PORT_VALUE}"
