#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf 'Usage: DEPLOY_INVARIANT_REMOTE_PROOF=1 %s /absolute/path/to/private-hosts.yml\n' "$0" >&2
}

[[ "${DEPLOY_INVARIANT_REMOTE_PROOF:-0}" == "1" ]] || {
  printf 'ERROR: set DEPLOY_INVARIANT_REMOTE_PROOF=1 to authorize this read-only remote proof preparation.\n' >&2
  exit 1
}

(($# == 1)) || { usage; exit 2; }
inventory="$1"
[[ "$inventory" == /* && -f "$inventory" ]] || {
  printf 'ERROR: inventory must be an absolute readable file outside the repository workflow.\n' >&2
  exit 2
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
inventory_real="$(realpath -- "$inventory")"
case "$inventory_real" in
  "$repo_root"/*)
    printf 'ERROR: private remote-proof inventory must stay outside the repository tree.\n' >&2
    exit 2
    ;;
esac
inventory="$inventory_real"
cd "$repo_root"

for cmd in ansible ansible-inventory ansible-playbook python3 realpath; do
  command -v "$cmd" >/dev/null 2>&1 || {
    printf 'ERROR: required command not found: %s\n' "$cmd" >&2
    exit 1
  }
done

export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
export ANSIBLE_HOST_KEY_CHECKING=True

python3 "$repo_root/scripts/validate-target-inventory.py" "$inventory" \
  --environment lab --require-ssh --single-host --outside-repository "$repo_root" >/dev/null
printf 'Inventory policy: PASS (one separate SSH lab target)\n'

ansible-playbook -i "$inventory" "$repo_root/ansible/playbooks/preflight.yml"   -e stack_name=dozzle   -e "deploy_invariant_repo_root=$repo_root"   -e "deploy_invariant_release_root=$repo_root" >/dev/null

printf 'Target identity + Docker preflight: PASS\n'
printf 'Topology: separate SSH target\n'
printf 'Control Ansible: '
python3 -c 'from ansible import __version__; print(__version__)'

# Read module results rather than parsing a version-dependent console callback.
facts_root="$(mktemp -d /tmp/deploy-invariant-remote-facts.XXXXXXXX)"
trap 'rm -rf -- "$facts_root"' EXIT
remote_stdout() {
  ansible all -i "$inventory" -b -m "$1" -a "$2" --tree "$facts_root" >/dev/null
  python3 - "$facts_root" <<'PY'
import json
import sys
from pathlib import Path

files = list(Path(sys.argv[1]).iterdir())
if len(files) != 1:
    raise SystemExit("ERROR: expected one remote facts result")
result = json.loads(files[0].read_text())
if result.get("failed") or result.get("unreachable") or result.get("rc", 0):
    raise SystemExit("ERROR: remote facts command failed")
print(result["stdout"])
PY
}

printf 'Target OS: '
remote_stdout ansible.builtin.shell ". /etc/os-release && printf '%s %s' \"\$NAME\" \"\$VERSION_ID\""

printf 'Docker Engine: '
remote_stdout ansible.builtin.command '/usr/bin/docker version --format json' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["Server"]["Version"])'

printf 'Docker Compose: '
remote_stdout ansible.builtin.command '/usr/bin/docker compose version --short'

printf 'Repository commit: %s\n' "$(git rev-parse HEAD)"
printf 'Readiness collection complete. This is not the transaction proof; execute docs/REMOTE_SSH_PROOF.md before closing issue #3.\n'
