import time
import random

def is_retryable(error: Exception) -> bool:
    status = getattr(error, "status_code", None) or getattr(error, "status", None)
    if status in (429, 503, 529):
        return True
    # OpenAI SDK 常见异常属性
    code = getattr(error, "code", None)
    if code in ("rate_limit_exceeded", "overloaded_error"):
        return True
    msg = str(error).lower()
    if any(k in msg for k in ("overloaded", "econnreset", "etimedout", "timeout", "rate limit")):
        return True
    return False

def with_retry(fn, max_retries: int = 3, on_retry=None):
    """同步重试包装。fn 是无参可调用对象。"""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as error:
            if attempt >= max_retries or not is_retryable(error):
                raise
            delay = min(2 ** attempt, 30) + random.random()  # 秒
            reason = str(getattr(error, "status_code", "") or error)[:60]
            if on_retry:
                on_retry(attempt + 1, max_retries, reason)
            time.sleep(delay)
    raise RuntimeError("Unreachable: with_retry loop exhausted")