.PHONY: validate ci lab-proof idempotency-proof acceptance-proof interruption-proof stale-marker-proof ssh-interruption-proof failure-matrix-proof stateful-recovery-proof public-safety syntax

validate:
	bash scripts/validate-repository.sh

ci:
	DEPLOY_INVARIANT_STRICT_VALIDATION=1 bash scripts/validate-repository.sh

lab-proof:
	DEPLOY_INVARIANT_LAB_ROLLBACK_TEST=1 bash tests/test-lab-rollback.sh

idempotency-proof:
	DEPLOY_INVARIANT_LAB_IDEMPOTENCY_TEST=1 bash tests/test-lab-idempotency.sh

acceptance-proof:
	DEPLOY_INVARIANT_LAB_ACCEPTANCE_FAILURE_TEST=1 bash tests/test-lab-acceptance-persistence.sh

failure-matrix-proof:
	DEPLOY_INVARIANT_LAB_FAILURE_MATRIX_TEST=1 bash tests/test-lab-retired-file-convergence.sh
	DEPLOY_INVARIANT_LAB_FAILURE_MATRIX_TEST=1 bash tests/test-lab-rollback-reverify-failure.sh

interruption-proof:
	DEPLOY_INVARIANT_LAB_INTERRUPTION_TEST=1 bash tests/test-lab-interruption-recovery.sh

stale-marker-proof:
	DEPLOY_INVARIANT_LAB_STALE_MARKER_PROOF=1 bash tests/test-lab-stale-accepted-marker.sh

ssh-interruption-proof:
	DEPLOY_INVARIANT_SSH_INTERRUPTION_TEST=1 bash tests/test-ssh-session-interruption.sh

stateful-recovery-proof:
	DEPLOY_INVARIANT_STATEFUL_RECOVERY_TEST=1 bash tests/test-stateful-recovery-reference.sh

public-safety:
	python3 scripts/check-public-safety.py

syntax:
	bash -n scripts/*.sh tests/*.sh
	python3 -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in sorted(Path('scripts').glob('*.py'))]; print('Python syntax validation passed.')"
