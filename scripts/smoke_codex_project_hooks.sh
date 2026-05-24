#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_DIR="${NANOMEM_SMOKE_DIR:-"$ROOT_DIR/.nanomem/smoke-codex-project-hooks"}"
DEBUG_DIR="$SMOKE_DIR/hook-debug"
TURN_DIR="$SMOKE_DIR/turns"
BIN_DIR="$SMOKE_DIR/bin"
CONFIG_FILE="$SMOKE_DIR/config.json"
SERVER_LOG="$SMOKE_DIR/server.log"
CODEX_LOG="$SMOKE_DIR/codex-exec.jsonl"
DB_FILE="$SMOKE_DIR/nanomem.db"
HOOK_FILE="$ROOT_DIR/.codex/hooks.json"
HOOK_BACKUP="$SMOKE_DIR/original-hooks.json"
OWNER_ID="${NANOMEM_SMOKE_OWNER_ID:-smoke-codex-user}"
NAMESPACE="${NANOMEM_SMOKE_NAMESPACE:-personal}"
PROMPT="${NANOMEM_SMOKE_PROMPT:-I prefer concise Chinese answers for NanoMem project-hook smoke tests. Reply exactly OK and do not run tools.}"

SERVER_PID=""
HOOK_EXISTED=0
HOOK_TOUCHED=0

restore_hooks() {
  if [[ "$HOOK_TOUCHED" != "1" ]]; then
    return
  fi
  if [[ "$HOOK_EXISTED" == "1" ]]; then
    mkdir -p "$(dirname "$HOOK_FILE")"
    cp "$HOOK_BACKUP" "$HOOK_FILE"
  else
    rm -f "$HOOK_FILE"
    rmdir "$(dirname "$HOOK_FILE")" 2>/dev/null || true
  fi
}

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  restore_hooks
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
  python - "$CONFIG_FILE" "$SMOKE_DIR" <<'PY'
import json
import sys
from pathlib import Path

config_file = Path(sys.argv[1])
data_dir = Path(sys.argv[2])
config_file.write_text(
    json.dumps(
        {
            "data_dir": str(data_dir),
            "store": {"backend": "sqlite"},
            "index": {"backend": "dense"},
            "extraction": {"backend": "heuristic"},
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

write_hook_shim() {
  mkdir -p "$BIN_DIR"
  cat > "$BIN_DIR/nanomem-agent-hook" <<EOF
#!/usr/bin/env bash
PYTHONPATH="$ROOT_DIR/src\${PYTHONPATH:+:\$PYTHONPATH}" exec python -m nanomem.integrations.hooks "\$@"
EOF
  chmod +x "$BIN_DIR/nanomem-agent-hook"
}

install_project_hooks() {
  mkdir -p "$SMOKE_DIR"
  HOOK_TOUCHED=1
  if [[ -f "$HOOK_FILE" ]]; then
    HOOK_EXISTED=1
    cp "$HOOK_FILE" "$HOOK_BACKUP"
  fi
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m nanomem.cli.main install-codex-hooks \
      --project-dir "$ROOT_DIR" \
      --force >/dev/null
}

validate_results() {
  python - "$DB_FILE" "$DEBUG_DIR" <<'PY'
import json
import sqlite3
import sys
from pathlib import Path

db_file = Path(sys.argv[1])
debug_dir = Path(sys.argv[2])
errors: list[str] = []

spool_payloads = sorted(debug_dir.glob("*-codex-spool-*.json"))
read_payloads = sorted(debug_dir.glob("*-codex-read-*.json"))
capture_payloads = sorted(debug_dir.glob("*-codex-capture-*.json"))
if not spool_payloads:
    errors.append("missing codex spool hook debug payload")
if not read_payloads:
    errors.append("missing codex read hook debug payload")
if not capture_payloads:
    errors.append("missing codex capture hook debug payload")

if not db_file.exists():
    errors.append(f"missing NanoMem database: {db_file}")
else:
    connection = sqlite3.connect(db_file)
    try:
        unit_count = connection.execute("SELECT COUNT(*) FROM memory_units").fetchone()[0]
        dialogue_count = connection.execute(
            "SELECT COUNT(*) FROM dialogue_records"
        ).fetchone()[0]
        latest_row = connection.execute(
            "SELECT messages_json FROM dialogue_records ORDER BY occurred_at DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()

    if unit_count < 1:
        errors.append("expected at least one MemoryUnit")
    if dialogue_count < 1:
        errors.append("expected at least one DialogueRecord")
    if latest_row is None:
        errors.append("missing latest DialogueRecord")
    else:
        messages = json.loads(latest_row[0])
        roles = [message.get("role") for message in messages]
        if "user" not in roles:
            errors.append("latest DialogueRecord has no user message")
        if "assistant" not in roles:
            errors.append("latest DialogueRecord has no assistant message")

if errors:
    print("Codex project-hook smoke validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Likely causes:", file=sys.stderr)
    print("- this Codex non-interactive exec mode does not execute hooks", file=sys.stderr)
    print("- Codex did not load project-level .codex/hooks.json", file=sys.stderr)
    print("- NanoMem hooks are not trusted or bypassed for this run", file=sys.stderr)
    print("- nanomem-agent-hook is not reachable from Codex PATH", file=sys.stderr)
    sys.exit(1)

print(f"spool_debug_payloads={len(spool_payloads)}")
print(f"read_debug_payloads={len(read_payloads)}")
print(f"capture_debug_payloads={len(capture_payloads)}")
print(f"memory_units={unit_count}")
print(f"dialogue_records={dialogue_count}")
PY
}

main() {
  require_command python
  require_command codex

  mkdir -p "$SMOKE_DIR" "$DEBUG_DIR" "$TURN_DIR"
  write_config
  write_hook_shim
  install_project_hooks

  local port="${NANOMEM_SMOKE_PORT:-$(free_port)}"
  local base_url="http://127.0.0.1:$port"

  echo "NanoMem Codex project-hook smoke test"
  echo "repo: $ROOT_DIR"
  echo "work dir: $SMOKE_DIR"
  echo "base url: $base_url"
  echo "hook file: $HOOK_FILE"
  echo ""
  echo "This script temporarily writes project-level Codex hooks and restores them."
  echo "It is diagnostic: some Codex exec builds do not execute hooks."
  echo ""

  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m nanomem.server.main \
      --config "$CONFIG_FILE" \
      --host 127.0.0.1 \
      --port "$port" \
      > "$SERVER_LOG" 2>&1 &
  SERVER_PID="$!"
  wait_for_server "$base_url"

  echo "Running codex exec with project hooks enabled..."
  PATH="$BIN_DIR:$PATH" \
    PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    NANOMEM_BASE_URL="$base_url" \
    NANOMEM_OWNER_ID="$OWNER_ID" \
    NANOMEM_NAMESPACE="$NAMESPACE" \
    NANOMEM_TURN_DIR="$TURN_DIR" \
    NANOMEM_HOOK_DEBUG_DIR="$DEBUG_DIR" \
    NANOMEM_CAPTURE_ASSISTANT=1 \
    codex exec \
      --enable hooks \
      --dangerously-bypass-hook-trust \
      --json "$PROMPT" | tee "$CODEX_LOG"

  echo ""
  validate_results
  echo ""
  echo "Smoke test passed. Artifacts are in $SMOKE_DIR"
}

main "$@"
