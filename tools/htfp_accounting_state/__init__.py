"""Offline supplied-record accounting inspection; imports perform no IO."""

from .inspect import format_report, process_bytes, process_file

__all__ = ["format_report", "process_bytes", "process_file"]
