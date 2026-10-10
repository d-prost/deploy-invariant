# Roadmap

The roadmap is intentionally narrow. DeployInvariant preserves bounded
configuration transactions and does not implement a data-backup platform.

## v1.0.0 baseline

The implementation and release gates were completed:

- target identity and SSH transport checks;
- immutable image and contract preflight;
- frozen rollback material;
- functional verification, durable acceptance and verified configuration rollback;
- interruption reconciliation and target/stack locking;
- disposable rollback, idempotency and failure proofs;
- #2: enforced strict main checks with blocked/allowed merge proof;
- #3: completed end-to-end recovery proof on a separate disposable SSH target;
- final clean-checkout acceptance proof recorded.

See [v1 acceptance](docs/V1_FINAL_ACCEPTANCE.md).

## Post-v1 roadmap (ordered)

1. **#4 — first stateful recovery reference:** runnable synthetic SQLite
   application-aware export, isolated restore and functional verification in
   [examples/stateful-sqlite](examples/stateful-sqlite/). This demonstrates
   application-data recovery independently of configuration rollback.
2. **Stability evaluation window:** track required CI and repeatable proof
   outcomes over a defined observation window before expanding the product.
3. **Stable terminal JSON result schema:** deterministic, backward-compatible
   machine-readable final transaction results.
4. **Durable append-only transaction history:** bounded, audit-friendly records,
   without an external database or daemon.
5. **Richer declarative HTTP checks:** bounded JSON extraction/comparisons,
   without a custom DSL.
6. **JUnit output** for existing verification results.
7. **Reusable GitHub Action** packaging the existing guarded invocation.
8. **Generic outbound webhook** with bounded delivery and no vendor coupling.

Prometheus is deferred unless an identified repository use case justifies it.

Out of scope: dashboard, scheduler, daemon, deployment database, Kubernetes
control plane, vendor-specific alert integration and custom policy DSL.
