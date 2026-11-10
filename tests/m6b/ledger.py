"""Standalone stdlib prospective accounting. No product imports or execution."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path


def utc():
    return datetime.now(timezone.utc).isoformat()


def scan(scan_root):
    """Count every historical attempt and refuse orphaned runs/cases."""
    totals = {"author": 0, "supervisor": 0}
    for path in sorted(Path(scan_root).rglob("CASE_LEDGER.jsonl")):
        runs, pending = set(), set()
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            event, run = row["event"], row["run_id"]
            if event == "RUN_STARTED":
                if run in runs:
                    raise RuntimeError("Repeated active run in " + str(path))
                runs.add(run)
            elif event == "ATTEMPT_STARTED":
                key = (run, row["attempt"])
                if run not in runs or key in pending:
                    raise RuntimeError("Invalid prospective attempt in " + str(path))
                pending.add(key)
                totals[row["role"]] += 1
            elif event == "ATTEMPT_FINISHED":
                pending.remove((run, row["attempt"]))
            elif event == "RUN_FINALIZED":
                if any(key[0] == run for key in pending):
                    raise RuntimeError("Finalized run retains pending attempt")
                runs.remove(run)
            else:
                raise RuntimeError("Unknown accounting event")
        if runs or pending:
            raise RuntimeError("Unfinalized campaign blocks target work: " + str(path))
    return totals


class Journal:
    def __init__(self, evidence_root, run_id, role, scan_root):
        if role not in ("author", "supervisor"):
            raise ValueError("Unknown verification role")
        self.evidence_root = Path(evidence_root)
        self.path = self.evidence_root / "CASE_LEDGER.jsonl"
        self.scan_root = Path(scan_root)
        self.run_id, self.role = run_id, role
        self.attempted = self.completed = 0
        self.pending = None
        self.started = self.finalized = False
        self.prior_counts = scan(self.scan_root)
        self.prior_role = self.prior_counts[role]

    def _append(self, event, **fields):
        row = {"event": event, "run_id": self.run_id, "role": self.role, "UTC": utc(), **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def begin(self, **details):
        if self.started or scan(self.scan_root) != self.prior_counts:
            raise RuntimeError("Campaign state changed before begin")
        self._append("RUN_STARTED", prior_counts=self.prior_counts, **details)
        self.started = True

    def start_case(self, case_id, **details):
        if not self.started or self.finalized or self.pending is not None:
            raise RuntimeError("Cannot start a case in current campaign state")
        if self.prior_role + self.attempted >= 1024:
            raise RuntimeError("Role cumulative verification budget exhausted")
        number = self.attempted + 1
        self._append("ATTEMPT_STARTED", attempt=number, case_id=case_id,
                     cumulative_role=self.prior_role + number, **details)
        self.attempted = number
        self.pending = number
        return number

    def finish_case(self, attempt, *, completed, **details):
        if self.pending != attempt:
            raise RuntimeError("Mismatched pending case")
        self._append("ATTEMPT_FINISHED", attempt=attempt, completed=bool(completed), **details)
        self.pending = None
        if completed:
            self.completed += 1

    def finalize(self, status, **details):
        if not self.started or self.finalized or self.pending is not None:
            raise RuntimeError("Cannot finalize an orphaned or closed campaign")
        self._append("RUN_FINALIZED", status=status, attempted=self.attempted,
                     completed=self.completed, cumulative_role=self.prior_role + self.attempted, **details)
        self.finalized = True
