import pytest

from app.core.rate_limit import RateLimiter


def test_allows_requests_up_to_the_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    assert limiter.is_allowed("client-a") is True
    assert limiter.is_allowed("client-a") is True
    assert limiter.is_allowed("client-a") is True


def test_rejects_requests_beyond_the_limit() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.is_allowed("client-a")
    limiter.is_allowed("client-a")

    assert limiter.is_allowed("client-a") is False


def test_tracks_each_key_independently() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.is_allowed("client-a")

    assert limiter.is_allowed("client-a") is False
    assert limiter.is_allowed("client-b") is True


def test_allows_requests_again_once_the_window_has_passed() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    limiter.is_allowed("client-a", now=0.0)

    assert limiter.is_allowed("client-a", now=5.0) is False
    assert limiter.is_allowed("client-a", now=11.0) is True


def test_raises_on_non_positive_max_requests() -> None:
    with pytest.raises(ValueError):
        RateLimiter(max_requests=0, window_seconds=60)


def test_raises_on_non_positive_window() -> None:
    with pytest.raises(ValueError):
        RateLimiter(max_requests=5, window_seconds=0)
