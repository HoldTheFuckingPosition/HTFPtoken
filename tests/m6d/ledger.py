"""Standalone durable verification accounting; never imports a product."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path


def scan(root):
    """Validate every retained M6D journal; unfinished work blocks new calls.

    Only the four common events and role/run_id/attempt fields are required.
    Independent recorders may add their own metadata. Every START counts,
    including failed and superseded attempts.
    """
    totals = {"author": 0, "supervisor": 0}
    seen_runs = set()
    for path in sorted(Path(root).rglob("CASE_LEDGER.jsonl")):
        active, pending, seen = {}, set(), set()
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                event, run, role = row["event"], row["run_id"], row["role"]
                if role not in totals or not isinstance(run, str) or not run:
                    raise ValueError("Malformed journal identity")
                if event == "RUN_STARTED":
                    if run in seen_runs or run in active:
                        raise ValueError("Repeated run identity")
                    active[run] = role
                    seen_runs.add(run)
                else:
                    if active.get(run) != role:
                        raise ValueError("Event outside its active run")
                    if event == "ATTEMPT_STARTED":
                        attempt = row["attempt"]
                        if type(attempt) is not int or attempt <= 0:
                            raise ValueError("Invalid attempt number")
                        key = (run, attempt)
                        if key in seen or pending:
                            raise ValueError("Repeated or overlapping attempt")
                        pending.add(key)
                        seen.add(key)
                        totals[role] += 1
                    elif event == "ATTEMPT_FINISHED":
                        key = (run, row["attempt"])
                        if key not in pending:
                            raise ValueError("Finish without start")
                        pending.remove(key)
                    elif event == "RUN_FINALIZED":
                        if any(key[0] == run for key in pending):
                            raise ValueError("Finalized with pending attempt")
                        del active[run]
                    else:
                        raise ValueError("Unknown journal event")
        if active or pending:
            raise ValueError("Unfinalized campaign: " + str(path))
    if any(count > 1024 for count in totals.values()):
        raise ValueError("Retained role quota exceeded")
    return totals


class Journal:
    """One serial campaign, append/flush/fsync before every external call."""

    def __init__(self, folder, run_id, role, prior):
        if role not in ("author", "supervisor"):
            raise ValueError("Unknown verification role")
        self.path = Path(folder) / "CASE_LEDGER.jsonl"
        if self.path.exists():
            raise ValueError("Journal already exists")
        self.run_id, self.role, self.prior = run_id, role, dict(prior)
        self.attempts = 0
        self.pending = None
        self.finalized = False
        self._append("RUN_STARTED", prior_counts=prior,
                     prior_role_attempts=prior[role], prior_global_attempts=sum(prior.values()))

    def _append(self, event, **fields):
        row = dict(event=event, run_id=self.run_id, role=self.role,
                   UTC=datetime.now(timezone.utc).isoformat(), **fields)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def start(self, **fields):
        if self.finalized or self.pending is not None or self.prior[self.role] + self.attempts >= 1024:
            raise ValueError("Attempt cannot start")
        self.attempts += 1
        self.pending = self.attempts
        self._append("ATTEMPT_STARTED", attempt=self.attempts,
                     cumulative_role=self.prior[self.role] + self.attempts,
                     cumulative_global=sum(self.prior.values()) + self.attempts, **fields)
        return self.attempts

    def finish(self, **fields):
        if self.pending is None or self.finalized:
            raise ValueError("No pending attempt")
        self._append("ATTEMPT_FINISHED", attempt=self.pending, **fields)
        self.pending = None

    def finalize(self, **fields):
        if self.pending is not None or self.finalized:
            raise ValueError("Campaign cannot finalize")
        self._append("RUN_FINALIZED", attempts=self.attempts, **fields)
        self.finalized = True
