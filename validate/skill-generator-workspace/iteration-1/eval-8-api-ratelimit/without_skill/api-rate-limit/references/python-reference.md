# Python Reference — Resilient API Client

Complete, production-ready module combining all three patterns.

## Dependencies

```
pip install httpx
```

## Full Module: `resilient_client.py`

```python
"""
Resilient API client with exponential backoff, circuit breaker, and retry queue.

Usage:
    from resilient_client import ResilientApiClient, RetryQueue

    # Single requests
    async with ResilientApiClient("https://api.example.com") as client:
        resp = await client.request("GET", "/users/123")

    # Bulk operations
    async def sync_user(user_id: str) -> bool:
        resp = await client.request("PUT", f"/users/{user_id}", json={"active": True})
        return resp.status_code < 400

    queue = RetryQueue(sync_user, max_concurrency=5)
    queue.submit_many(user_ids)
    stats = await queue.run()
    print(f"Done: {stats}")
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Set

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}

# ---------------------------------------------------------------------------
# Retry-After Parsing
# ---------------------------------------------------------------------------

def parse_retry_after(response: httpx.Response) -> float | None:
    """Parse Retry-After header. Returns wait time in seconds or None."""
    value = response.headers.get("Retry-After") or response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        retry_date = parsedate_to_datetime(value)
        delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
        return max(delta, 0)
    except Exception:
        return None


def parse_rate_limit_headers(response: httpx.Response) -> dict:
    """Extract common rate-limit headers into a dict."""
    return {
        "limit": response.headers.get("X-RateLimit-Limit"),
        "remaining": response.headers.get("X-RateLimit-Remaining"),
        "reset": response.headers.get("X-RateLimit-Reset"),
        "retry_after": parse_retry_after(response),
    }

# ---------------------------------------------------------------------------
# Exponential Backoff
# ---------------------------------------------------------------------------

async def request_with_backoff(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs,
) -> httpx.Response:
    """Make an HTTP request with exponential backoff and jitter.

    Args:
        client: httpx async client instance.
        method: HTTP method (GET, POST, etc.).
        url: Request URL (can be relative if client has base_url).
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Cap on delay in seconds.
        **kwargs: Passed through to client.request().

    Returns:
        The httpx.Response (either success or last failed attempt).
    """
    last_response: httpx.Response | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            if attempt == max_retries:
                raise
            logger.warning("Connection error on %s %s (attempt %d): %s", method, url, attempt + 1, exc)
            await asyncio.sleep(min(base_delay * (2 ** attempt), max_delay))
            continue

        last_response = response

        if response.status_code not in RETRYABLE_STATUS_CODES:
            return response

        if attempt == max_retries:
            break

        retry_after = parse_retry_after(response)
        backoff = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, base_delay)
        delay = max(backoff + jitter, retry_after or 0)

        logger.warning(
            "Retry %s %s: attempt=%d/%d status=%d delay=%.2fs",
            method, url, attempt + 1, max_retries,
            response.status_code, delay,
        )
        await asyncio.sleep(delay)

    assert last_response is not None
    logger.error("Max retries (%d) exhausted for %s %s", max_retries, method, url)
    return last_response

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open."""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Circuit OPEN — retry after {retry_after:.1f}s")


class CircuitBreaker:
    """Thread-safe circuit breaker.

    Args:
        failure_threshold: Consecutive failures before opening.
        recovery_timeout: Seconds to stay open before testing recovery.
        name: Identifier for logging.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._recovery_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN and time.monotonic() >= self._recovery_time:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit '%s' → HALF_OPEN (testing recovery)", self.name)
            return self._state

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit '%s' → CLOSED (recovered)", self.name)
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._recovery_time = time.monotonic() + self.recovery_timeout
                logger.warning(
                    "Circuit '%s' → OPEN after %d failures (recovery in %.0fs)",
                    self.name, self._failure_count, self.recovery_timeout,
                )

    def check(self) -> None:
        """Raise CircuitOpenError if circuit is open."""
        s = self.state
        if s == CircuitState.OPEN:
            remaining = max(0, self._recovery_time - time.monotonic())
            raise CircuitOpenError(remaining)

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            logger.info("Circuit '%s' manually reset → CLOSED", self.name)

# ---------------------------------------------------------------------------
# Retry Queue
# ---------------------------------------------------------------------------

@dataclass(order=True)
class _RetryTask:
    priority: float
    item: Any = field(compare=False)
    attempt: int = field(default=0, compare=False)


class RetryQueue:
    """Async priority queue with concurrency control and dead-letter.

    Args:
        worker_fn: Async callable that processes one item. Must return True on success.
        max_concurrency: Max simultaneous in-flight worker calls.
        max_retries: Retries per item before dead-lettering.
        base_delay: Base delay for retry backoff.
        max_delay: Max delay cap.
    """

    def __init__(
        self,
        worker_fn: Callable[[Any], Awaitable[bool]],
        max_concurrency: int = 10,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        self.worker_fn = worker_fn
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        self._sem = asyncio.Semaphore(max_concurrency)
        self._queue: asyncio.PriorityQueue[_RetryTask] = asyncio.PriorityQueue()
        self.dead_letter: list[Any] = []
        self._completed = 0
        self._failed = 0
        self._total = 0

    def submit(self, item: Any) -> None:
        self._queue.put_nowait(_RetryTask(priority=0, item=item))
        self._total += 1

    def submit_many(self, items: list[Any]) -> None:
        for item in items:
            self.submit(item)

    async def _process(self, task: _RetryTask) -> None:
        async with self._sem:
            try:
                ok = await self.worker_fn(task.item)
            except Exception as exc:
                logger.error("Worker error for %r: %s", task.item, exc)
                ok = False

        if ok:
            self._completed += 1
            logger.debug("Completed: %r (%d/%d)", task.item, self._completed, self._total)
            return

        task.attempt += 1
        if task.attempt > self.max_retries:
            self.dead_letter.append(task.item)
            self._failed += 1
            logger.error("Dead-lettered: %r after %d attempts", task.item, task.attempt)
            return

        delay = min(self.base_delay * (2 ** (task.attempt - 1)), self.max_delay)
        jitter = random.uniform(0, self.base_delay)
        wait = delay + jitter
        logger.warning("Re-queue %r: attempt=%d wait=%.1fs", task.item, task.attempt, wait)
        await asyncio.sleep(wait)
        task.priority = time.monotonic()
        await self._queue.put(task)

    async def run(self) -> dict:
        """Process all queued items. Returns stats dict."""
        pending: list[asyncio.Task] = []

        while not self._queue.empty() or pending:
            while not self._queue.empty():
                task = await self._queue.get()
                pending.append(asyncio.create_task(self._process(task)))

            if pending:
                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                pending = [t for t in pending if t not in done]
                # Propagate exceptions
                for t in done:
                    if t.exception():
                        logger.error("Unhandled task error: %s", t.exception())

        return {
            "total": self._total,
            "completed": self._completed,
            "failed": self._failed,
            "dead_letter_count": len(self.dead_letter),
        }

# ---------------------------------------------------------------------------
# Integrated Client
# ---------------------------------------------------------------------------

class ResilientApiClient:
    """High-level client combining backoff + circuit breaker + concurrency.

    Usage:
        async with ResilientApiClient("https://api.example.com") as client:
            response = await client.request("GET", "/endpoint")
    """

    def __init__(
        self,
        base_url: str,
        *,
        max_concurrency: int = 10,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 30.0,
        timeout: float = 30.0,
    ):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self.circuit = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout,
            name=base_url,
        )
        self._sem = asyncio.Semaphore(max_concurrency)
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make a resilient request."""
        self.circuit.check()

        async with self._sem:
            response = await request_with_backoff(
                self.client, method, path,
                max_retries=self._max_retries,
                base_delay=self._base_delay,
                max_delay=self._max_delay,
                **kwargs,
            )

        if response.status_code in RETRYABLE_STATUS_CODES:
            self.circuit.record_failure()
        else:
            self.circuit.record_success()

        return response

    async def close(self) -> None:
        await self.client.aclose()
```

## Quick Start

```python
import asyncio
from resilient_client import ResilientApiClient

async def main():
    async with ResilientApiClient("https://api.example.com", max_concurrency=5) as client:
        response = await client.request("GET", "/data")
        print(response.status_code, response.json())

asyncio.run(main())
```

## Bulk Processing

```python
import asyncio
from resilient_client import ResilientApiClient, RetryQueue

async def main():
    client = ResilientApiClient("https://api.example.com", max_concurrency=5)

    async def process_item(item_id: str) -> bool:
        resp = await client.request("POST", f"/process/{item_id}")
        return resp.status_code == 200

    queue = RetryQueue(process_item, max_concurrency=5, max_retries=3)
    queue.submit_many([f"item-{i}" for i in range(100)])

    stats = await queue.run()
    print(f"Results: {stats}")

    if queue.dead_letter:
        print(f"Failed items: {queue.dead_letter}")

    await client.close()

asyncio.run(main())
```
