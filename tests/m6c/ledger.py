"""Standalone stdlib prospective journal; no product/runner imports or calls.

Compatible independent ROOT journals share only the four event names and
event/run_id/role/attempt fields. Extra metadata is retained and accepted.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path


def utc():
    return datetime.now(timezone.utc).isoformat()


def scan(root):
    """Count all starts; malformed, pending or unfinished campaigns block work."""
    totals = {"author": 0, "supervisor": 0}
    for path in sorted(Path(root).rglob("CASE_LEDGER.jsonl")):
        active, pending, seen = {}, set(), set()
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            event, run, role = row["event"], row["run_id"], row["role"]
            if role not in totals or not isinstance(run, str) or not run:
                raise RuntimeError("Invalid journal identity: " + str(path))
            if event == "RUN_STARTED":
                if run in active:
                    raise RuntimeError("Repeated active run: " + str(path))
                active[run] = role
            elif event == "ATTEMPT_STARTED":
                number = row["attempt"]
                if type(number) is not int or number < 1:
                    raise RuntimeError("Invalid journal attempt: " + str(path))
                key = (run, number)
                if active.get(run) != role or key in seen:
                    raise RuntimeError("Invalid prospective attempt: " + str(path))
                pending.add(key)
                seen.add(key)
                totals[role] += 1
            elif event == "ATTEMPT_FINISHED":
                key = (run, row["attempt"])
                if active.get(run) != role or key not in pending:
                    raise RuntimeError("Unknown pending attempt: " + str(path))
                pending.remove(key)
            elif event == "RUN_FINALIZED":
                if active.get(run) != role or any(key[0] == run for key in pending):
                    raise RuntimeError("Invalid finalization: " + str(path))
                del active[run]
            else:
                raise RuntimeError("Unknown journal event: " + str(path))
        if active or pending:
            raise RuntimeError("Unfinished campaign blocks target work: " + str(path))
    return totals


class Journal:
    def __init__(self, folder, run_id, role, scan_root):
        if role not in ("author", "supervisor"):
            raise ValueError("Invalid role")
        self.path = Path(folder) / "CASE_LEDGER.jsonl"
        if self.path.exists():
            raise RuntimeError("Never overwrite/reuse a journal")
        self.run_id, self.role, self.scan_root = run_id, role, Path(scan_root)
        self.prior = scan(self.scan_root)
        self.attempted = self.completed = 0
        self.pending = None
        self.begun = self.finalized = False

    def _append(self, event, **fields):
        row = dict(event=event, run_id=self.run_id, role=self.role, UTC=utc(), **fields)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def begin(self, **details):
        if self.begun or scan(self.scan_root) != self.prior:
            raise RuntimeError("Campaign changed before begin")
        self._append("RUN_STARTED", prior_counts=self.prior, **details)
        self.begun = True

    def start(self, case_id, **details):
        if not self.begun or self.finalized or self.pending is not None:
            raise RuntimeError("Campaign is not ready for an attempt")
        if self.prior[self.role] + self.attempted >= 1024:
            raise RuntimeError("Cumulative role budget exhausted")
        number = self.attempted + 1
        self._append("ATTEMPT_STARTED", attempt=number, case_id=case_id,
                     cumulative_role=self.prior[self.role] + number,
                     cumulative_global=sum(self.prior.values()) + number, **details)
        self.attempted, self.pending = number, number
        return number

    def finish(self, number, *, completed, **details):
        if self.pending != number:
            raise RuntimeError("Mismatched pending attempt")
        self._append("ATTEMPT_FINISHED", attempt=number, completed=bool(completed), **details)
        self.pending = None
        self.completed += int(bool(completed))

    def finalize(self, status, **details):
        if not self.begun or self.finalized or self.pending is not None:
            raise RuntimeError("Cannot finalize orphaned/closed campaign")
        self._append("RUN_FINALIZED", status=status, attempted=self.attempted,
                     completed=self.completed,
                     cumulative_role=self.prior[self.role] + self.attempted,
                     cumulative_global=sum(self.prior.values()) + self.attempted, **details)
        self.finalized = True
