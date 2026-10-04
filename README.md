# DeployInvariant

Deployment safety as explicit, testable invariants.

I built DeployInvariant for Docker Compose environments where a deployment needs more discipline than `compose up`, but a permanent orchestration platform would be unnecessary. Git provides the candidate, Ansible carries out the bounded transaction, and the change is not accepted until the target has passed functional verification and the acceptance record is durable.

[![Validate DeployInvariant](https://github.com/d-prost/deploy-invariant/actions/workflows/validate.yml/badge.svg)](https://github.com/d-prost/deploy-invariant/actions/workflows/validate.yml)
[![CodeQL](https://github.com/d-prost/deploy-invariant/actions/workflows/codeql.yml/badge.svg)](https://github.com/d-prost/deploy-invariant/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/d-prost/deploy-invariant/badge)](https://securityscorecards.dev/viewer/?uri=github.com/d-prost/deploy-invariant)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## The invariants

A deployment is allowed to change the target only when the transaction can keep these statements true:

1. the intended target is verified before mutation;
2. candidate inputs are frozen and container images are immutable;
3. the previous accepted state has usable rollback material;
4. functional checks decide candidate success, not container existence alone;
5. runtime verification is not acceptance until the acceptance record is durable;
6. an interrupted mutation is reconciled before another candidate starts;
7. rollback is complete only after the previous accepted configuration passes its checks again;
8. configuration rollback never claims to recover application data.

Stateful workloads can add one more gate: matching recovery-readiness evidence must exist before mutation.

## Transaction

```text
candidate
   |
   v
preflight + target identity
   |
   v
contract + immutable inputs
   |
   v
prepare rollback material
   |
   v
managed mutation
   |
   v
functional verification
   |
   +--> PASS -> durable acceptance -> ACCEPTED
   |
   +--> FAIL -> restore previous accepted config -> reverify
                                                   |
                                                   +--> PASS -> REJECTED_ROLLBACK_VERIFIED
                                                   |
                                                   +--> FAIL -> REJECTED_ROLLBACK_FAILED
```

The exact semantics are in [`docs/TRANSACTION_MODEL.md`](docs/TRANSACTION_MODEL.md).

## What it is not

DeployInvariant is deliberately not a PaaS, scheduler, service mesh, secrets manager, backup engine, deployment database or continuous reconciliation controller.

Compose remains the application payload. The project adds a transaction boundary around changing it.

## Quick start

On Debian or Ubuntu:

```bash
git clone https://github.com/d-prost/deploy-invariant.git
cd deploy-invariant
bash scripts/setup.sh --install-only
make validate
```

Run the disposable rollback proof:

```bash
make lab-proof
```

The reference stacks live under `stacks/` and use the same transaction path as a real target.

## Production path

Create a private inventory from the example and keep real target details outside this repository:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Preflight:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

Deploy:

```bash
bash scripts/deploy-stack.sh dozzle
```

Production uses strict SSH host-key verification and a clean `main` matching `origin/main`.

## Proof suite

```bash
make validate
make lab-proof
make idempotency-proof
make acceptance-proof
make interruption-proof
make stale-marker-proof
make ssh-interruption-proof
make failure-matrix-proof
```

CI runs the matching repository and disposable proofs. CI has no Production deployment authority.

## Status

The single-target stateless transaction path is implemented and covered by disposable proofs.

Two external gates remain before `v1.0.0`:

- #2 — effective `main` change controls with blocked-merge proof;
- #3 — one real transaction and verified rollback against a separate SSH target.

The first stateful recovery reference is tracked separately in #4 and does not block the initial stateless release.

## Origin

DeployInvariant was extracted from the transaction work that started in [HomeLab Ops Blueprint](https://github.com/d-prost/homelab-ops-blueprint). The implementation starts here with a clean repository history; the predecessor remains useful as development history rather than product history.

Broader system design notes live in [HomeLab Engineering](https://github.com/d-prost/homelab-engineering).

## License

MIT. See [`LICENSE`](LICENSE).
