# v1 final acceptance: 2026-10-05

The final proof set ran from clean main commit
`d961e914986348d3f2a18b5b6c30d9cac2641061` on a disposable Ubuntu 26.04.1 LTS
VM with Docker Engine 29.1.3, Docker Compose 2.40.3 and Ansible Core 2.20.1.
The successful proof durations below total 348 seconds.

## Main change controls

The active main ruleset requires nine checks, strict branch freshness and a
pull request, with zero human approvals and no bypass actors. Deletion and
force-push are blocked.

The temporary [protection proof PR #6](https://github.com/d-prost/deploy-invariant/pull/6)
was observed in both states, then closed without merging:

- A deliberately failed required Static validation check produced `BLOCKED`.
- Restoring the policy produced nine successful required checks, `CLEAN`,
  `MERGEABLE` and zero submitted reviews.

PR #7 subsequently passed all required checks and merged through that ruleset.
Issue #2 is complete.

## Separate SSH target

The completed [remote proof](REMOTE_SSH_PROOF_2026-10-05.md) used a separate
control host, trusted SSH transport and a private single-target lab inventory.
A healthy baseline reached `ACCEPTED`; a failing candidate reached
`REJECTED_ROLLBACK_VERIFIED`, preserved the accepted record and passed an
independent HTTP check after restoration. The disposable stack and proof
records were removed.

## Final local proof set

| Command | Result | Seconds |
|---|---|---:|
| `make validate` | PASS | 23 |
| `make lab-proof` | PASS | 32 |
| `make idempotency-proof` | PASS | 37 |
| `make acceptance-proof` | PASS | 40 |
| `make interruption-proof` | PASS | 63 |
| `make stale-marker-proof` | PASS | 39 |
| `make ssh-interruption-proof` | PASS | 34 |
| `make failure-matrix-proof` | PASS | 80 |

The last target covers retired-file convergence and rollback re-verification
failure. A failed previous functional check remained a rollback failure rather
than being reported as verified recovery.

Private operator setup used a non-writable fixture policy. An initial SSH
interruption attempt under restrictive `umask=077` could not read its
root-owned temporary daemon PID file. That temporary daemon was identified and
stopped, and the affected proof was rerun successfully under `umask=022`.
No previously successful proof was counted twice. Raw logs remain private.

Final target inspection found retained recovery directories, a disposable
Compose container and the temporary SSH proof account after the test scripts'
best-effort cleanup. Their evidence was preserved, then explicit privileged
cleanup removed them. The final target had no proof containers, Dozzle managed
files, acceptance records, unresolved marker or candidate/recovery directories.
On a reusable lab, successful assertions require a separate cleanup inspection;
this run does not claim that every proof script cleans up autonomously.

## Release boundary

The changelog promotes the implemented baseline to v1.0.0. The final evidence
and changelog still require the protected main CI checks before release.
Issue #4, the first stateful recovery reference, remains post-v1 work.
Configuration rollback never claims to restore application data.
