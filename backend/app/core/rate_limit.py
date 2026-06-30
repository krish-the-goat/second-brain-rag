from slowapi import Limiter
from slowapi.util import get_remote_address

# 60/minute global ceiling — individual endpoints add stricter per-route limits.
# The DocumentList component polls /documents every 10 s (6/min) and chat stream
# is capped at 5/min per route, so 60/min gives plenty of headroom for all
# endpoints combined without self-rate-limiting the app.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
