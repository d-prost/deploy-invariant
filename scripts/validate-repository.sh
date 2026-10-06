#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"; cd "$repo_root"
while IFS= read -r -d '' script; do bash -n "$script"; done < <(find scripts tests -type f -name '*.sh' -print0)
python3 - <<'PYCODE'
from pathlib import Path
for path in sorted(Path('scripts').glob('*.py')):
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print('Python syntax validation passed.')
PYCODE
python3 scripts/check-public-safety.py
python3 scripts/check-branding.py
python3 scripts/validate-advisory-rules.py
python3 scripts/validate-stack-contracts.py
python3 tests/test-advisory-rules.py
python3 tests/test-stack-contracts.py
python3 tests/test-functional-check-parsing.py
python3 tests/test-operational-coverage.py
python3 tests/test-recovery-readiness.py
python3 tests/test-stateful-recovery-reference.py
python3 tests/test-rollback-material-preflight.py
python3 tests/test-target-inventory.py
python3 tests/test-target-lock-key.py
python3 tests/test-durable-state-file.py
python3 tests/test-transaction-state-classification.py
python3 tests/test-main-ruleset-policy.py
bash tests/test-failure-matrix-preflight.sh
bash tests/test-integrity-guards.sh
bash tests/test-production-mutation-path.sh
bash tests/test-transaction-freeze.sh
bash tests/test-target-identity.sh
bash tests/test-ssh-host-key.sh
bash tests/test-global-lock.sh
if command -v yamllint >/dev/null 2>&1; then yamllint -d '{extends: default, rules: {line-length: disable, truthy: disable}}' .github ansible stacks advisory; fi
if command -v shellcheck >/dev/null 2>&1; then find scripts tests -type f -name '*.sh' -print0 | xargs -0 shellcheck; fi
if command -v ansible-playbook >/dev/null 2>&1; then
  export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/preflight.yml -e stack_name=dozzle -e deploy_invariant_repo_root="$repo_root" -e deploy_invariant_release_root="$repo_root" --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/read-accepted-record.yml -e stack_name=dozzle -e deploy_invariant_transaction_root=/tmp/deploy-invariant-transaction-syntax --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/inspect-transaction-state.yml -e stack_name=dozzle -e deploy_invariant_transaction_root=/tmp/deploy-invariant-transaction-syntax --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/cleanup-prepared-interruption.yml -e stack_name=dozzle -e deploy_invariant_interrupted_transaction_id=syntax-check -e deploy_invariant_repo_root="$repo_root" --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/reconcile-interrupted.yml -e stack_name=dozzle -e deploy_invariant_interrupted_transaction_id=syntax-check -e deploy_invariant_interrupted_candidate_commit=1111111111111111111111111111111111111111 -e deploy_invariant_interrupted_previous_commit=2222222222222222222222222222222222222222 -e deploy_invariant_interrupted_previous_record_id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -e deploy_invariant_repo_root="$repo_root" -e deploy_invariant_release_root="$repo_root" --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/clear-stale-accepted-marker.yml -e stack_name=dozzle -e deploy_invariant_interrupted_transaction_id=syntax-check -e deploy_invariant_expected_record_hash=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -e deploy_invariant_repo_root="$repo_root" --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/preflight-images.yml -e stack_name=dozzle -e deploy_invariant_repo_root="$repo_root" -e deploy_invariant_candidate_images_b64=W119 -e deploy_invariant_rollback_images_b64='' --syntax-check
  DEPLOY_INVARIANT_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/deploy-stack.yml -e stack_name=dozzle -e deploy_invariant_release_commit=1111111111111111111111111111111111111111 -e deploy_invariant_tooling_commit=2222222222222222222222222222222222222222 -e deploy_invariant_transaction_id=syntax-check -e deploy_invariant_contract_hash=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -e deploy_invariant_manifest_hash=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -e deploy_invariant_previous_accepted_commit='' -e deploy_invariant_previous_record_id='' -e deploy_invariant_previous_record_source='' -e deploy_invariant_previous_release_root='' -e deploy_invariant_repo_root="$repo_root" -e deploy_invariant_release_root="$repo_root" --syntax-check
fi
if [[ "${DEPLOY_INVARIANT_STRICT_VALIDATION:-0}" == "1" ]]; then command -v gitleaks >/dev/null || { echo 'ERROR: gitleaks required in strict mode' >&2; exit 1; }; gitleaks dir . --redact --no-banner --config .gitleaks.toml; fi
printf 'Validation passed.\n'
