# Contributing

Focused pull requests are preferred over changes that mix transaction behavior, documentation and unrelated cleanup.

## Validation

The baseline is:

```bash
make validate
```

Changes to deployment, verification or rollback behavior should run the relevant disposable proof, usually:

```bash
make lab-proof
```

Behavior changes should include matching tests.

## Pull requests

A useful pull request explains:

1. the problem;
2. the bounded change;
3. the evidence supporting it.

New background services, persistent control-plane components or broad dependencies need a clear reason that the existing Git + Ansible transaction cannot cover the requirement.

## Public boundary

Real hostnames, addresses, credentials, private URLs, backup identifiers and recovery evidence stay outside this repository. Reproduction material should use synthetic data and disposable targets.
