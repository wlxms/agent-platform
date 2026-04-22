"""Circuit breaker to prevent cascading failures on upstream services."""
from __future__ import annotations

import time


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: dict[str, int] = {}
        self._last_failure: dict[str, float] = {}

    def is_available(self, service: str) -> bool:
        failures = self._failures.get(service, 0)
        if failures < self.failure_threshold:
            return True
        last_fail = self._last_failure.get(service, 0)
        return time.time() - last_fail > self.recovery_timeout

    def record_success(self, service: str) -> None:
        self._failures[service] = 0

    def record_failure(self, service: str) -> None:
        self._failures[service] = self._failures.get(service, 0) + 1
        self._last_failure[service] = time.time()
