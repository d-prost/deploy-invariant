# Changelog

All notable changes to this project will be documented here.

## Unreleased

### Added

- Synthetic SQLite stateful recovery reference with application-aware JSON export, isolated restore, representative HTTP recovery verification and source-state isolation proof.

## v1.0.0 - 2026-10-05

### Added

- Clean DeployInvariant project baseline.
- Single-target deployment transaction with target identity, immutable inputs, functional verification and durable acceptance.
- Verified configuration rollback and interruption recovery.
- Recovery-readiness gate for stateful changes.
- Disposable proof suite and two reference stacks.
- Private external inventory support for a separate SSH lab target, with strict
  transport and target identity guards.

### Verified

- Active main change controls require the full CI proof set with zero human
  approvals; a failed required check blocks merging.
- Real separate-target SSH deployment accepted a healthy Dozzle baseline and
  verified rollback after a deliberately failing candidate.
- Final acceptance evidence is recorded under `docs/evidence/`.
