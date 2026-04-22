"""Tests for circuit breaker pattern (T6.4)."""
import time


def test_circuit_breaker_opens_after_failures():
    from agentp_gateway.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    assert cb.is_available("auth") is True
    cb.record_failure("auth")
    cb.record_failure("auth")
    cb.record_failure("auth")
    assert cb.is_available("auth") is False  # Circuit open


def test_circuit_breaker_resets_after_timeout():
    from agentp_gateway.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
    cb.record_failure("auth")
    assert cb.is_available("auth") is False
    time.sleep(1.1)
    assert cb.is_available("auth") is True  # recovery timeout elapsed


def test_circuit_breaker_records_success():
    from agentp_gateway.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_success("auth")
    assert cb.is_available("auth") is True


def test_circuit_breaker_resets_on_success():
    from agentp_gateway.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
    cb.record_failure("auth")
    assert cb.is_available("auth") is True  # 1 < 2 threshold
    cb.record_failure("auth")
    assert cb.is_available("auth") is False  # open
    cb.record_success("auth")
    assert cb.is_available("auth") is True  # reset
