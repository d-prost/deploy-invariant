#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${DEPLOY_INVARIANT_LAB_FAILURE_MATRIX_TEST:-0}" == "1" ]] || {
  printf 'ERROR: set DEPLOY_INVARIANT_LAB_FAILURE_MATRIX_TEST=1.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"
export DEPLOY_INVARIANT_LAB_HOSTNAME
DEPLOY_INVARIANT_LAB_HOSTNAME="$(/bin/hostname)"
export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"

target_dir="/opt/deploy-invariant-ops/stacks/dozzle"
record_file="/etc/deploy-invariant-ops/deployments/dozzle.record"
receipt_file="/etc/deploy-invariant-ops/deployments/dozzle.receipt"
marker_file="/var/lib/deploy-invariant-ops/transactions/dozzle.unresolved"
tmp_root="$(mktemp -d)"
candidate_root="$tmp_root/candidate"
previous_root="$tmp_root/previous"
failure_log="$tmp_root/failure.log"

cleanup() {
  set +e
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose --env-file "$target_dir/defaults.env" -f "$target_dir/docker-compose.yml" down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir" /var/lib/deploy-invariant-ops/candidates/dozzle-*
  sudo rm -f -- "$record_file" "$receipt_file" "$marker_file"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || { printf 'ERROR: disposable target exists.\n' >&2; exit 1; }

bash scripts/deploy-stack.sh dozzle --inventory lab >/dev/null

mkdir -p "$candidate_root" "$previous_root"
git archive HEAD | tar -x -C "$candidate_root"
git archive HEAD | tar -x -C "$previous_root"

python3 - "$candidate_root/stacks/dozzle/compose.yaml" "$previous_root/stacks/dozzle/stack.yml" <<'PY'
from pathlib import Path
import sys, yaml
compose=Path(sys.argv[1]); model=yaml.safe_load(compose.read_text())
model["services"]["dozzle"]["entrypoint"]=["/bin/sh","-c","exit 42"]
compose.write_text(yaml.safe_dump(model,sort_keys=False))
contract=Path(sys.argv[2]); data=yaml.safe_load(contract.read_text())
data["stack_functional_checks"][0]["port"]=65534
contract.write_text(yaml.safe_dump(data,sort_keys=False))
PY

sudo cat "$record_file" | tee "$tmp_root/previous.record" >/dev/null
prev_id="$(sha256sum "$tmp_root/previous.record" | awk '{print $1}')"
commit="$(git rev-parse HEAD)"
contract_hash="$(sha256sum "$candidate_root/stacks/dozzle/stack.yml" | awk '{print $1}')"
manifest_hash="$(sha256sum "$candidate_root/stacks/dozzle/MANIFEST.tsv" | awk '{print $1}')"

set +e
ansible-playbook -i "$repo_root/ansible/inventory/lab/hosts.yml" "$repo_root/ansible/playbooks/deploy-stack.yml"   -e stack_name=dozzle   -e deploy_invariant_release_commit=1111111111111111111111111111111111111111   -e deploy_invariant_tooling_commit="$commit"   -e deploy_invariant_transaction_id=rollback-reverify-failure   -e deploy_invariant_contract_hash="$contract_hash"   -e deploy_invariant_manifest_hash="$manifest_hash"   -e deploy_invariant_previous_accepted_commit="$commit"   -e deploy_invariant_previous_record_id="$prev_id"   -e deploy_invariant_previous_record_source="$tmp_root/previous.record"   -e deploy_invariant_previous_release_root="$previous_root"   -e deploy_invariant_repo_root="$repo_root"   -e deploy_invariant_release_root="$candidate_root" >"$failure_log" 2>&1
rc=$?
set -e

((rc != 0)) || { printf 'FAIL: rollback re-verification failure unexpectedly succeeded.\n' >&2; exit 1; }
grep -Fq 'REJECTED_ROLLBACK_FAILED' "$failure_log" || {
  printf 'FAIL: rollback re-verification failure lacked explicit terminal result.\n' >&2
  cat "$failure_log" >&2
  exit 1
}
sudo grep -Fxq 'phase=RESTORING' "$marker_file" || {
  printf 'FAIL: failed rollback did not retain RESTORING marker.\n' >&2
  cat "$failure_log" >&2
  exit 1
}
sudo test -d /var/lib/deploy-invariant-ops/candidates/dozzle-rollback-reverify-failure-rollback || {
  printf 'FAIL: failed rollback discarded target-local recovery material.\n' >&2
  exit 1
}

printf 'Rollback re-verification failure proof passed: REJECTED_ROLLBACK_FAILED and recovery material retained.\n'
