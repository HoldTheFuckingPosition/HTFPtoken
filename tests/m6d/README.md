# M6D finite actual CLI verification

The runner imports no product. It authenticates the sealed two-component
159-case oracle, the union's final design pins, exact request bytes and full
expected stdout/stderr/exit. Historical draft pins remain historical. The
85 C obligations are aliases; all 16 G cases are separate invocations, including
repeated inputs. The remaining 58 cases are explicit additional comparisons.
This is finite deterministic coverage with no shrinking or exhaustive claim.

From `/home/jerem/htfp`, after the explicit S127 handoff:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/m6d/run.py author-001
```

Every invocation is an actual fresh `python3 -B -m htfp_recover` child. No
helper, import, help or smoke call supplements the 159-case campaign. The
runner preserves exact raw input files, raw stdout/stderr/exit in a lossless
gzip capture, source snapshots, isolated profile copies and actual IO/argv
associations. Missing paths are retained as absent; the FIFO case uses a new
anonymous pipe with its writer closed before the child's invocation, not a
persistent special file. Every copied Python source equals the original;
only the explicitly described copied PROFILE fixture differs.

`ledger.py` is standalone stdlib accounting. `scan(root)` checks all retained
M6D `CASE_LEDGER.jsonl` files and returns author/supervisor cumulative totals.
Malformed, unfinished or overlapping campaigns block further calls. A
`Journal(folder,run_id,role,prior)` provides `start(**metadata)`,
`finish(**metadata)` and `finalize(**metadata)`, with append/flush/fsync for
each standard RUN_STARTED/ATTEMPT_STARTED/ATTEMPT_FINISHED/RUN_FINALIZED event.
The durable START precedes each target child, including failures and retries.
Independent recorders may use the same minimal journal fields without
importing this runner. All generations and counters are retained.

S127 assigns at most 1,024 cumulative calls per role, 1.5 MiB combined author
code/tests/evidence, 4 MiB all M6D and a 2 GiB free-space floor. These are the
verification campaign's resource limits, not restrictions on future product
use. No parallel campaign is permitted. ROOT performs its distinct replay
only after the author's final source/evidence seal and stop.

This suite proves only exact offline descriptor/parser/profile behavior for
the selected cases. It adds zero HTTP, native or public blockchain operations.
It does not prove source account eligibility, an actual receipt, packet fit,
signature validity, production identity, deployment or execution success.
