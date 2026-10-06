# Roadmap

The roadmap is intentionally narrow.

## v1.0.0

The first stable release is defined by the transaction contract, not by feature count.

Implemented:

- target identity and SSH transport checks;
- immutable image and contract preflight;
- frozen rollback material;
- functional verification;
- durable acceptance;
- verified configuration rollback;
- interruption reconciliation;
- target/stack locking;
- disposable rollback, idempotency and failure proofs;
- #2 — enforced GitHub `main` change controls with blocked/allowed merge evidence;
- #3 — complete transaction proof against a genuinely separate SSH target;
- final clean-checkout proof set and public-safe v1 acceptance evidence.

## After v1

Implemented:

- #4 — first public stateful recovery reference with synthetic SQLite data,
  database-aware export, isolated restore, representative functional recovery,
  source immutability verification and explicit separation from configuration
  rollback.

Ordered next work:

1. stability evaluation window;
2. stable JSON terminal result schema;
3. durable append-only transaction history;
4. richer declarative HTTP checks with bounded JSON extraction/comparisons;
5. JUnit output;
6. reusable GitHub Action;
7. generic outbound webhook.

A Prometheus check is considered only after the ordered work above is complete
and only when a concrete repository use case justifies it.

A custom DSL, dashboard, scheduler, drift daemon, deployment database, cluster
control plane or vendor-specific alert integration is not on the roadmap.
