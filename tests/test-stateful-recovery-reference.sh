#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${DEPLOY_INVARIANT_STATEFUL_RECOVERY_TEST:-0}" != "1" ]]; then
  printf 'SKIP: set DEPLOY_INVARIANT_STATEFUL_RECOVERY_TEST=1 to run the synthetic stateful recovery proof.\n'
  exit 0
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
stack_dir="$repo_root/stacks/sqlite-notes"
work_dir="$(mktemp -d -t deploy-invariant-stateful-recovery.XXXXXX)"
source_project="di-stateful-source-$$"
restore_project="di-stateful-restore-$$"
export_file="$work_dir/notes-export.json"

compose() {
  local project="$1"
  shift
  docker compose \
    --env-file "$stack_dir/defaults.env" \
    -f "$stack_dir/compose.yaml" \
    -p "$project" \
    "$@"
}

cleanup() {
  compose "$restore_project" down -v --remove-orphans >/dev/null 2>&1 || true
  compose "$source_project" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -r -- "$work_dir" 2>/dev/null || true
}
trap cleanup EXIT

wait_health() {
  local project="$1"
  local attempt
  for attempt in $(seq 1 30); do
    if compose "$project" exec -T notes python - <<'PY' >/dev/null 2>&1
import json
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2) as response:
    assert response.status == 200
    assert json.load(response) == {"status": "ok"}
PY
    then
      return 0
    fi
    sleep 1
  done
  printf 'ERROR: %s did not become healthy\n' "$project" >&2
  return 1
}

assert_note() {
  local project="$1"
  local key="$2"
  local expected="$3"
  compose "$project" exec -T notes python - "$key" "$expected" <<'PY'
import json
import sys
import urllib.parse
import urllib.request
key, expected = sys.argv[1:3]
url = "http://127.0.0.1:8080/notes/" + urllib.parse.quote(key, safe="")
with urllib.request.urlopen(url, timeout=2) as response:
    assert response.status == 200
    payload = json.load(response)
assert payload == {"key": key, "value": expected}, payload
PY
}

printf 'Starting source stateful reference project...\n'
compose "$source_project" up -d
wait_health "$source_project"
compose "$source_project" exec -T notes \
  python /app/app.py seed \
  --database /data/notes.db \
  --key reference \
  --value synthetic-state-v1
assert_note "$source_project" reference synthetic-state-v1

printf 'Creating application-aware export...\n'
compose "$source_project" exec -T notes \
  python /app/app.py export --database /data/notes.db >"$export_file"

python3 - "$export_file" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload == {
    "schema_version": 1,
    "notes": [{"key": "reference", "value": "synthetic-state-v1"}],
}, payload
PY

printf 'Restoring into an isolated Compose project and volume...\n'
compose "$restore_project" run --rm --no-deps -T notes \
  python /app/app.py restore --database /data/notes.db <"$export_file"
compose "$restore_project" up -d
wait_health "$restore_project"
assert_note "$restore_project" reference synthetic-state-v1

printf 'Proving restore isolation from the source state...\n'
compose "$restore_project" exec -T notes \
  python /app/app.py seed \
  --database /data/notes.db \
  --key reference \
  --value synthetic-restored-only
assert_note "$restore_project" reference synthetic-restored-only
assert_note "$source_project" reference synthetic-state-v1

printf '%s\n' \
  'Stateful recovery reference proof passed: application-aware export, isolated restore,' \
  'representative functional recovery, and unchanged source state verified.'
