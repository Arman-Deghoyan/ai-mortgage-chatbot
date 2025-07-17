from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings


def create_rate_limiter():
    """Create and configure rate limiter"""
    if settings.enable_rate_limiting:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{settings.max_requests_per_minute}/minute"],
        )
        return limiter
    return None


def get_rate_limiter():
    """Get rate limiter instance"""
    return create_rate_limiter()


def apply_rate_limiting(app):
    """Apply rate limiting to FastAPI app"""
    if settings.enable_rate_limiting:
        limiter = create_rate_limiter()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        return limiter
    return None
