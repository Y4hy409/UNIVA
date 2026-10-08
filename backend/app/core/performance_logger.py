"""
CLARIUS Backend - High-Resolution Performance Timing & Logging System

Provides request-level monotonic timing, stage measurement, safe logging,
and stage breakdown summaries for backend requests (ADR-004 / Performance Instrumentation).
"""

import time
import sys
import contextvars
from typing import Dict, Any, List, Optional


class RequestTimer:
    """Request-level monotonic timer tracking elapsed time from request ingress."""

    def __init__(self, request_id: Optional[str] = None):
        self.t0 = time.perf_counter()
        self.request_id = request_id
        # Ordered dictionary of stage durations for summary
        self.stage_durations: Dict[str, float] = {}
        self.logs: List[str] = []
        self._phase_starts: Dict[str, float] = {}

    def elapsed(self) -> float:
        """Total elapsed seconds since request entered backend."""
        return time.perf_counter() - self.t0

    def log(self, description: str) -> None:
        """Log a stage description with current elapsed time [XX.XXs]."""
        elapsed_sec = self.elapsed()
        msg = f"[{elapsed_sec:05.2f}s] {description}"
        print(msg, flush=True)
        self.logs.append(msg)

    def log_skipped(self, stage_name: str, reason: str = "") -> None:
        """Log an explicitly skipped stage."""
        desc = f"{stage_name} skipped" + (f" - {reason}" if reason else "")
        self.log(desc)

    def start_phase(self, phase_name: str) -> float:
        """Start measuring a phase duration."""
        start = time.perf_counter()
        self._phase_starts[phase_name] = start
        return start

    def end_phase(
        self,
        phase_name: str,
        stage_description: Optional[str] = None,
        record_summary: bool = True,
        summary_key: Optional[str] = None
    ) -> float:
        """End measuring a phase and log its completion with elapsed request time."""
        start = self._phase_starts.pop(phase_name, self.t0)
        duration = time.perf_counter() - start
        
        key = summary_key or phase_name
        if record_summary:
            if key in self.stage_durations:
                self.stage_durations[key] += duration
            else:
                self.stage_durations[key] = duration

        if stage_description:
            self.log(stage_description)
            
        return duration

    def record_stage_duration(self, stage_name: str, duration: float) -> None:
        """Record a measured duration directly for summary."""
        if stage_name in self.stage_durations:
            self.stage_durations[stage_name] += duration
        else:
            self.stage_durations[stage_name] = duration

    def print_summary(self) -> None:
        """Print the performance summary block based on actual measured timings."""
        total_time = self.elapsed()
        print("\n========== REQUEST PERFORMANCE ==========", flush=True)
        print(f"Total request time: {total_time:.2f}s", flush=True)
        for stage, dur in self.stage_durations.items():
            print(f"{stage}: {dur:.2f}s", flush=True)
        print("==========================================\n", flush=True)


_current_timer: contextvars.ContextVar[Optional[RequestTimer]] = contextvars.ContextVar("current_request_timer", default=None)


def get_current_timer() -> Optional[RequestTimer]:
    """Retrieve active RequestTimer from async context."""
    return _current_timer.get()


def set_current_timer(timer: Optional[RequestTimer]) -> None:
    """Set or clear active RequestTimer in async context."""
    _current_timer.set(timer)
