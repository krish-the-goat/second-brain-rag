import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limits configurable via environment variables
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "60/minute")
CHAT_RATE_LIMIT = os.getenv("CHAT_RATE_LIMIT", "5/minute")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "3/minute")
URL_RATE_LIMIT = os.getenv("URL_RATE_LIMIT", "2/minute")

# 60/minute global ceiling — individual endpoints add stricter per-route limits.
# The DocumentList component polls /documents every 10 s (6/min) and chat stream
# is capped at 5/min per route, so 60/min gives plenty of headroom for all
# endpoints combined without self-rate-limiting the app.
limiter = Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATE_LIMIT])
