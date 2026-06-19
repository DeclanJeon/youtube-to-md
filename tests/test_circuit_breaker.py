import time
from app.services.circuit_breaker import CircuitBreaker, CircuitState


def test_initial_state():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
    assert cb.state == CircuitState.CLOSED
    assert not cb.is_open()


def test_failure_counting():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_open()


def test_success_resets_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

def test_recovery_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
    cb.record_failure()
    cb.record_failure()
    # recovery_timeout=0이므로 즉시 half_open
    assert cb.state == CircuitState.HALF_OPEN

def test_reset():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open()
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert not cb.is_open()
