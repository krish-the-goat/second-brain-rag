import os
import re
import logging
import structlog

def setup_logging():
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    
    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "console":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
        
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)

def get_logger(name: str = None):
    return structlog.get_logger(name)


def sanitize_error_msg(text: str) -> str:
    """Removes API keys from URLs or text before logging."""
    if not text:
        return ""
    # Strip ?key=XXXXX or &key=XXXXX
    return re.sub(r'([?&]key=)[^&]*', r'\1[REDACTED]', text)
