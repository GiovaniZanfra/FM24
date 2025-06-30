import logging
from functools import wraps


def suppress_logs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        lvl = logging.getLogger().getEffectiveLevel()
        logging.getLogger().setLevel(logging.CRITICAL)
        try:
            return func(*args, **kwargs)
        finally:
            logging.getLogger().setLevel(lvl)
    return wrapper