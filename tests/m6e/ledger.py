"""Standalone prospective accounting. No product or old-module imports."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path


def scan(root):
    """Count every retained start, rejecting malformed or unfinished runs."""
    totals = {"author": 0, "supervisor": 0}
    known_runs = set()
    for path in sorted(Path(root).rglob("CASE_LEDGER.jsonl")):
        active, pending, seen = {}, set(), set()
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            event, run, role = row["event"], row["run_id"], row["role"]
            if role not in totals or not isinstance(run, str) or not run:
                raise ValueError("Malformed journal identity")
            if event == "RUN_STARTED":
                if run in known_runs:
                    raise ValueError("Repeated run identity")
                known_runs.add(run)
                active[run] = role
            else:
                if active.get(run) != role:
                    raise ValueError("Journal event outside active run")
                if event == "ATTEMPT_STARTED":
                    number = row["attempt"]
                    key = (run, number)
                    if type(number) is not int or number <= 0 or key in seen or pending:
                        raise ValueError("Repeated, malformed or overlapping attempt")
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
    if any(value > 1024 for value in totals.values()):
        raise ValueError("Retained role cap exceeded")
    return totals


class Journal:
    """Append/flush/fsync START before a child; never reset prior counts."""

    def __init__(self, folder, run_id, role, prior):
        self.path = Path(folder) / "CASE_LEDGER.jsonl"
        if self.path.exists() or role not in ("author", "supervisor"):
            raise ValueError("Invalid new journal")
        self.run_id, self.role, self.prior = run_id, role, dict(prior)
        self.attempts = 0
        self.pending = None
        self.finalized = False
        self._append("RUN_STARTED", prior_counts=prior, prior_role_attempts=prior[role],
                     prior_global_attempts=sum(prior.values()))

    def _append(self, event, **details):
        row = dict(event=event, run_id=self.run_id, role=self.role,
                   UTC=datetime.now(timezone.utc).isoformat(), **details)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def start(self, **details):
        if self.finalized or self.pending is not None or self.prior[self.role] + self.attempts >= 1024:
            raise ValueError("Cannot start attempt")
        self.attempts += 1
        self.pending = self.attempts
        self._append("ATTEMPT_STARTED", attempt=self.attempts,
                     cumulative_role=self.prior[self.role] + self.attempts,
                     cumulative_global=sum(self.prior.values()) + self.attempts, **details)
        return self.attempts

    def finish(self, **details):
        if self.pending is None or self.finalized:
            raise ValueError("No pending attempt")
        self._append("ATTEMPT_FINISHED", attempt=self.pending, **details)
        self.pending = None

    def finalize(self, **details):
        if self.pending is not None or self.finalized:
            raise ValueError("Cannot finalize campaign")
        self._append("RUN_FINALIZED", attempted=self.attempts,
                     cumulative_role=self.prior[self.role] + self.attempts,
                     cumulative_global=sum(self.prior.values()) + self.attempts, **details)
        self.finalized = True
