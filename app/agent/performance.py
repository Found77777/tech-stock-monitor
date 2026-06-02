"""Lightweight performance monitoring utilities for agent operations."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentPerformanceMonitor:
    """Collects elapsed time measurements for debug metadata and logs."""

    spans: dict[str, float] = field(default_factory=dict)

    def measure(self, name: str):
        monitor = self

        class _Span:
            def __enter__(self):
                self.start = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc, tb):
                elapsed_ms = (time.perf_counter() - self.start) * 1000
                monitor.spans[name] = round(elapsed_ms, 2)
                logger.info("agent_perf span=%s elapsed_ms=%.2f", name, elapsed_ms)
                return False

        return _Span()

    def as_debug(self) -> dict[str, float]:
        return dict(self.spans)
