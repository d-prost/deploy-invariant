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
ansible --version | head -n1 | sed -E 's/\[[^]]*\]//g'

printf 'Target OS: '
ansible all -i "$inventory" -b -m ansible.builtin.shell   -a ". /etc/os-release && printf '%s %s' \"\$NAME\" \"\$VERSION_ID\""   -o | sed -E 's/^[^|]+\|[^>]+>>[[:space:]]*//' | tail -n1

printf 'Docker Engine: '
ansible all -i "$inventory" -b -m ansible.builtin.command \
  -a '/usr/bin/docker version --format json' -o \
  | sed -E 's/^[^|]+\|[^>]+>>[[:space:]]*//' | tail -n1 \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["Server"]["Version"])'

printf 'Docker Compose: '
ansible all -i "$inventory" -b -m ansible.builtin.command   -a '/usr/bin/docker compose version --short'   -o | sed -E 's/^[^|]+\|[^>]+>>[[:space:]]*//' | tail -n1

printf 'Repository commit: %s\n' "$(git rev-parse HEAD)"
printf 'Readiness collection complete. This is not the transaction proof; execute docs/REMOTE_SSH_PROOF.md before closing issue #3.\n'
