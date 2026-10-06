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
- disposable rollback, idempotency and failure proofs.

Remaining release gates:

- #2 — enforce the intended GitHub `main` change controls and prove blocked/allowed merge behavior;
- #3 — run the complete transaction against a genuinely separate SSH target;
- run the final clean-checkout proof set after both gates are complete.

## After v1

Implemented:

- #4 — synthetic SQLite stateful recovery reference with application-aware export, isolated restore and representative functional recovery.

Next:

- stability evaluation window before widening the public interface.

Possible later work only when a concrete need appears:

- richer versioned deployment records;
- JSON output for inspection;
- additional generic stack examples;
- carefully bounded multi-host semantics.

A dashboard, scheduler, drift daemon, backup framework or cluster control plane is not on the roadmap.
