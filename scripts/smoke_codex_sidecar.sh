#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_DIR="${NANOMEM_SMOKE_DIR:-"$ROOT_DIR/.nanomem/smoke-codex-sidecar-$(date +%Y%m%d%H%M%S)"}"
FIXTURE_DIR="$ROOT_DIR/tests/fixtures/codex_hooks"
CONFIG_FILE="$SMOKE_DIR/nanomem.json"
SERVER_LOG="$SMOKE_DIR/server.log"
READ_OUTPUT="$SMOKE_DIR/hook-read.json"
CAPTURE_OUTPUT="$SMOKE_DIR/hook-capture.json"
DEBUG_DIR="$SMOKE_DIR/hook-debug"
TURN_DIR="$SMOKE_DIR/turns"
DB_FILE="$SMOKE_DIR/nanomem.db"
OWNER_ID="${NANOMEM_SMOKE_OWNER_ID:-codex-smoke-user}"
NAMESPACE="${NANOMEM_SMOKE_NAMESPACE:-personal}"
SERVER_PID=""

cleanup() {
  stop_server
}
trap cleanup EXIT

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: $command_name" >&2
    exit 1
  fi
}

free_port() {
  python - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

write_config() {
  python - "$CONFIG_FILE" "$SMOKE_DIR" "$DB_FILE" <<'PY'
import json
import sys
from pathlib import Path

config_file = Path(sys.argv[1])
data_dir = Path(sys.argv[2])
db_file = Path(sys.argv[3])
config_file.write_text(
    json.dumps(
        {
            "data_dir": str(data_dir),
            "store": {
                "backend": "sqlite",
                "path": str(db_file),
            },
            "index": {
                "backend": "dense",
            },
            "extraction": {
                "backend": "heuristic",
            },
            "read": {
                "default_recency_policy": "balanced",
                "default_max_units": 10,
            },
        },
        indent=2,
        sort_keys=True,
    ),
    encoding="utf-8",
)
PY
}

wait_for_server() {
  local base_url="$1"
  python - "$base_url" "$SERVER_LOG" <<'PY'
import sys
import time
import urllib.request

base_url = sys.argv[1]
server_log = sys.argv[2]
for _ in range(80):
    try:
        with urllib.request.urlopen(f"{base_url}/v1/health", timeout=0.5) as response:
            if response.status == 200:
                sys.exit(0)
    except Exception:
        time.sleep(0.1)

print(f"NanoMem server did not become healthy. See {server_log}", file=sys.stderr)
sys.exit(1)
PY
}

start_server() {
  local base_url="$1"
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m nanomem.server.main \
      --config "$CONFIG_FILE" \
      --host 127.0.0.1 \
      --port "$PORT" \
      >> "$SERVER_LOG" 2>&1 &
  SERVER_PID="$!"
  wait_for_server "$base_url"
}

stop_server() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  SERVER_PID=""
}

seed_memory() {
  local base_url="$1"
  python - "$base_url" "$OWNER_ID" "$NAMESPACE" <<'PY'
import json
import sys
import urllib.request

base_url, owner_id, namespace = sys.argv[1:4]
payload = {
    "scope": {
        "owner_id": owner_id,
        "namespace": namespace,
    },
    "dialogue": {
        "occurred_at": "2026-05-24T09:00:00+08:00",
        "messages": [
            {
                "role": "user",
                "speaker_id": owner_id,
                "content": "I prefer concise Chinese answers for coding discussions.",
                "timestamp": "2026-05-24T09:00:00+08:00",
            }
        ],
        "metadata": {
            "host": "codex-sidecar-smoke-seed",
        },
    },
    "capture_time": "2026-05-24T09:00:01+08:00",
}
request = urllib.request.Request(
    f"{base_url}/v1/capture",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=5) as response:
    response.read()
PY
}

run_hook() {
  local action="$1"
  local fixture="$2"
  local output="$3"
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    NANOMEM_BASE_URL="$BASE_URL" \
    NANOMEM_OWNER_ID="$OWNER_ID" \
    NANOMEM_NAMESPACE="$NAMESPACE" \
    NANOMEM_TURN_DIR="$TURN_DIR" \
    NANOMEM_HOOK_DEBUG_DIR="$DEBUG_DIR" \
    NANOMEM_CAPTURE_ASSISTANT=1 \
    python -m nanomem.integrations.hooks "$action" --host codex \
      < "$fixture" > "$output"
}

validate_hook_outputs() {
  python - "$READ_OUTPUT" "$CAPTURE_OUTPUT" "$DEBUG_DIR" <<'PY'
import json
import sys
from pathlib import Path

read_output = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
capture_output = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
debug_dir = Path(sys.argv[3])

context = read_output.get("hookSpecificOutput", {}).get("additionalContext", "")
if "concise Chinese answers" not in context:
    raise SystemExit("read hook did not inject the seeded memory context")
if capture_output.get("continue") is not True:
    raise SystemExit("capture hook did not return a successful hook response")
if not list(debug_dir.glob("*-codex-read-*.json")):
    raise SystemExit("missing read hook debug payload")
if not list(debug_dir.glob("*-codex-spool-*.json")):
    raise SystemExit("missing spool hook debug payload")
if not list(debug_dir.glob("*-codex-capture-*.json")):
    raise SystemExit("missing capture hook debug payload")
PY
}

validate_restart_read() {
  local base_url="$1"
  python - "$base_url" "$OWNER_ID" "$NAMESPACE" "$DB_FILE" <<'PY'
import json
import sqlite3
import sys
import urllib.request

base_url, owner_id, namespace, db_file = sys.argv[1:5]
payload = {
    "owner_id": owner_id,
    "namespaces": [namespace],
    "query": "sidecar flow concise Chinese answer preference",
    "query_time": "2026-05-24T09:05:00+08:00",
    "max_units": 5,
}
request = urllib.request.Request(
    f"{base_url}/v1/read",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=5) as response:
    read_payload = json.loads(response.read().decode("utf-8"))

context = read_payload.get("context", {}).get("text", "")
if "sidecar flow" not in context:
    raise SystemExit("restart read did not retrieve the captured Codex turn")
if "concise Chinese answers" not in context:
    raise SystemExit("restart read did not retrieve the seeded preference")

connection = sqlite3.connect(db_file)
try:
    unit_count = connection.execute("SELECT COUNT(*) FROM memory_units").fetchone()[0]
    dialogue_count = connection.execute(
        "SELECT COUNT(*) FROM dialogue_records"
    ).fetchone()[0]
finally:
    connection.close()

if unit_count < 2:
    raise SystemExit(f"expected at least 2 memory units, found {unit_count}")
if dialogue_count < 2:
    raise SystemExit(f"expected at least 2 dialogue records, found {dialogue_count}")

print(f"memory_units={unit_count}")
print(f"dialogue_records={dialogue_count}")
PY
}

main() {
  require_command python
  mkdir -p "$SMOKE_DIR" "$DEBUG_DIR" "$TURN_DIR"
  write_config

  PORT="${NANOMEM_SMOKE_PORT:-$(free_port)}"
  BASE_URL="http://127.0.0.1:$PORT"

  echo "NanoMem Codex sidecar smoke test"
  echo "repo: $ROOT_DIR"
  echo "work dir: $SMOKE_DIR"
  echo "base url: $BASE_URL"
  echo ""

  start_server "$BASE_URL"
  seed_memory "$BASE_URL"
  run_hook spool "$FIXTURE_DIR/user_prompt_submit.json" "$SMOKE_DIR/hook-spool.json"
  run_hook read "$FIXTURE_DIR/user_prompt_submit.json" "$READ_OUTPUT"
  run_hook capture "$FIXTURE_DIR/stop.json" "$CAPTURE_OUTPUT"
  validate_hook_outputs

  stop_server
  start_server "$BASE_URL"
  validate_restart_read "$BASE_URL"

  echo ""
  echo "Smoke test passed. Artifacts are in $SMOKE_DIR"
}

main "$@"
