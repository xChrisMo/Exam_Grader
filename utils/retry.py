import time
from functools import wraps
from typing import Callable, Any
from utils.logger import Logger

logger = Logger().get_logger()

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt == max_attempts:
                        logger.error(f"Max retries ({max_attempts}) exceeded: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt} failed: {str(e)}")
                    time.sleep(delay * (backoff ** (attempt - 1)))
            return None
        return wrapper
    return decorator 