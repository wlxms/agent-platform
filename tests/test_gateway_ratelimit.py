"""Tests for rate limiting middleware (T6.1)."""


def test_rate_limiter_allows_under_limit():
    from agentp_gateway.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    assert limiter.is_allowed("client-1") is True  # 1st
    assert limiter.is_allowed("client-1") is True  # 2nd
    assert limiter.is_allowed("client-1") is True  # 3rd
    assert limiter.is_allowed("client-1") is True  # 4th
    assert limiter.is_allowed("client-1") is True  # 5th


def test_rate_limiter_blocks_over_limit():
    from agentp_gateway.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.is_allowed("client-1")
    limiter.is_allowed("client-1")
    assert limiter.is_allowed("client-1") is False  # 3rd blocked


def test_rate_limiter_remaining():
    from agentp_gateway.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    limiter.is_allowed("client-1")
    assert limiter.get_remaining("client-1") == 4
    limiter.is_allowed("client-1")
    assert limiter.get_remaining("client-1") == 3


def test_rate_limiter_independent_clients():
    from agentp_gateway.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.is_allowed("client-a") is True
    assert limiter.is_allowed("client-a") is False
    assert limiter.is_allowed("client-b") is True
