"""Shared rate limiter for the sensitive authentication endpoints.

Keyed on the client IP via slowapi. Storage is in-memory (per process), which
is fine for a single instance; point slowapi at Redis for a multi-instance
deployment.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Per-IP limits for the endpoints an attacker would hammer.
LOGIN_LIMIT = "10/minute"
SIGNUP_LIMIT = "5/minute"
EMAIL_LIMIT = "5/minute"
# /refresh mints credentials from a bearer secret, so it is worth throttling
# too; the ceiling is higher because a legitimate browser may refresh often.
REFRESH_LIMIT = "30/minute"
