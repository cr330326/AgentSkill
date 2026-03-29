---
name: api-rate-limit
description: "Implement API rate limiting, retry strategies, and resilience patterns. Covers exponential backoff, circuit breaker, retry queues, and rate limit header parsing for Python and Node.js. Use when: handling 429 Too Many Requests, designing retry logic, implementing circuit breakers, building resilient API clients, rate limit errors, backoff strategies, retry queues, or bulk API call orchestration."
---

# API Rate Limit & Retry Strategy Skill

Guide for implementing resilient API clients that gracefully handle rate limiting (HTTP 429), transient failures, and service degradation. Covers three core patterns: **Exponential Backoff**, **Circuit Breaker**, and **Retry Queue**.

## Decision Flow

When the user needs rate-limit/retry handling, follow this sequence:

1. **Identify the scenario** — which pattern(s) are needed:
   - Single request retries → Exponential Backoff
   - Protecting a degraded downstream service → Circuit Breaker
   - Bulk/batch API calls with throughput control → Retry Queue
   - Production-grade resilience → combine all three

2. **Identify the language** — Python or Node.js (ask if unclear)

3. **Check for existing rate limit info** — does the API return `Retry-After`, `X-RateLimit-Remaining`, or similar headers?

4. **Implement** using the patterns and reference code below

---

## Pattern 1: Exponential Backoff with Jitter

### When to Use
- Any retryable API call (HTTP 429, 500, 502, 503, 504)
- Default strategy for all transient failures

### Design Rules

1. **Retryable status codes**: `429`, `500`, `502`, `503`, `504`. Do NOT retry `400`, `401`, `403`, `404`, `422`.
2. **Respect `Retry-After` header** — if present, use it as the minimum wait time. It may be seconds (integer) or an HTTP-date.
3. **Base formula**: `delay = min(base_delay * 2^attempt + jitter, max_delay)`
4. **Jitter**: add random value in `[0, base_delay)` to prevent thundering herd.
5. **Defaults**: `base_delay=1s`, `max_delay=60s`, `max_retries=5`.
6. **Logging**: log every retry with attempt number, status code, delay, and endpoint.

### Python Implementation

```python
import asyncio
import random
import logging
from typing import Set
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx  # preferred; aiohttp also works

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}


def parse_retry_after(response: httpx.Response) -> float | None:
    """Extract wait time in seconds from Retry-After header."""
    value = response.headers.get("Retry-After") or response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            retry_date = parsedate_to_datetime(value)
            delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
            return max(delta, 0)
        except Exception:
            return None


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
    """Make an HTTP request with exponential backoff and jitter."""
    for attempt in range(max_retries + 1):
        response = await client.request(method, url, **kwargs)

        if response.status_code not in RETRYABLE_STATUS_CODES:
            return response  # success or non-retryable error

        if attempt == max_retries:
            logger.error("Max retries reached for %s %s (status=%d)", method, url, response.status_code)
            return response  # return last failed response

        # Calculate delay
        retry_after = parse_retry_after(response)
        backoff = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, base_delay)
        delay = max(backoff + jitter, retry_after or 0)

        logger.warning(
            "Retrying %s %s: attempt=%d/%d status=%d delay=%.2fs",
            method, url, attempt + 1, max_retries, response.status_code, delay,
        )
        await asyncio.sleep(delay)

    return response  # unreachable but satisfies type checker
```

### Node.js Implementation

```typescript
import { setTimeout } from "timers/promises";

const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

interface BackoffOptions {
  maxRetries?: number;
  baseDelay?: number;   // ms
  maxDelay?: number;    // ms
}

function parseRetryAfter(response: Response): number | null {
  const value = response.headers.get("Retry-After") ?? response.headers.get("retry-after");
  if (!value) return null;
  const seconds = Number(value);
  if (!Number.isNaN(seconds)) return seconds * 1000; // convert to ms
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return Math.max(date.getTime() - Date.now(), 0);
  }
  return null;
}

async function fetchWithBackoff(
  url: string,
  init?: RequestInit,
  options: BackoffOptions = {},
): Promise<Response> {
  const { maxRetries = 5, baseDelay = 1000, maxDelay = 60_000 } = options;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, init);

    if (!RETRYABLE_STATUS_CODES.has(response.status)) {
      return response;
    }

    if (attempt === maxRetries) {
      console.error(`Max retries reached for ${url} (status=${response.status})`);
      return response;
    }

    const retryAfterMs = parseRetryAfter(response);
    const backoff = Math.min(baseDelay * 2 ** attempt, maxDelay);
    const jitter = Math.random() * baseDelay;
    const delay = Math.max(backoff + jitter, retryAfterMs ?? 0);

    console.warn(
      `Retrying ${url}: attempt=${attempt + 1}/${maxRetries} status=${response.status} delay=${delay.toFixed(0)}ms`,
    );
    await setTimeout(delay);
  }

  throw new Error("Unreachable");
}
```

---

## Pattern 2: Circuit Breaker

### When to Use
- Protecting against cascading failures when a downstream API is degraded
- Preventing wasted retries on a service that is clearly down
- Combined with backoff for defense-in-depth

### Design Rules

1. **Three states**: `CLOSED` (normal) → `OPEN` (tripped) → `HALF_OPEN` (testing recovery)
2. **Failure threshold**: trip to OPEN after N consecutive failures (default: 5)
3. **Recovery timeout**: stay OPEN for a cooldown period (default: 30s), then transition to HALF_OPEN
4. **Half-open probe**: allow 1 request through. On success → CLOSED. On failure → back to OPEN (reset timer).
5. **What counts as failure**: same retryable status codes (429, 5xx) plus connection errors/timeouts
6. **Raise a specific exception** (`CircuitOpenError` / `CircuitOpenError`) when the circuit is open so callers can handle it distinctly.

### Python Implementation

```python
import time
import threading
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open and rejecting calls."""
    def __init__(self, recovery_time: float):
        remaining = max(0, recovery_time - time.monotonic())
        super().__init__(f"Circuit is OPEN. Retry after {remaining:.1f}s")
        self.retry_after = remaining


class CircuitBreaker:
    """Thread-safe circuit breaker for API calls."""

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
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._recovery_time = time.monotonic() + self.recovery_timeout
                logger.warning("Circuit '%s' OPENED after %d failures", self.name, self._failure_count)

    def check(self) -> None:
        """Raise CircuitOpenError if the circuit is open."""
        current = self.state
        if current == CircuitState.OPEN:
            raise CircuitOpenError(self._recovery_time)
        # HALF_OPEN and CLOSED both allow requests through
```

### Node.js Implementation

```typescript
enum CircuitState {
  CLOSED = "closed",
  OPEN = "open",
  HALF_OPEN = "half_open",
}

class CircuitOpenError extends Error {
  retryAfterMs: number;
  constructor(retryAfterMs: number) {
    super(`Circuit is OPEN. Retry after ${(retryAfterMs / 1000).toFixed(1)}s`);
    this.name = "CircuitOpenError";
    this.retryAfterMs = retryAfterMs;
  }
}

class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount = 0;
  private recoveryTime = 0;

  constructor(
    private readonly failureThreshold: number = 5,
    private readonly recoveryTimeoutMs: number = 30_000,
    private readonly name: string = "default",
  ) {}

  getState(): CircuitState {
    if (this.state === CircuitState.OPEN && Date.now() >= this.recoveryTime) {
      this.state = CircuitState.HALF_OPEN;
    }
    return this.state;
  }

  recordSuccess(): void {
    this.failureCount = 0;
    this.state = CircuitState.CLOSED;
  }

  recordFailure(): void {
    this.failureCount++;
    if (this.failureCount >= this.failureThreshold) {
      this.state = CircuitState.OPEN;
      this.recoveryTime = Date.now() + this.recoveryTimeoutMs;
      console.warn(`Circuit '${this.name}' OPENED after ${this.failureCount} failures`);
    }
  }

  check(): void {
    const current = this.getState();
    if (current === CircuitState.OPEN) {
      const remaining = Math.max(0, this.recoveryTime - Date.now());
      throw new CircuitOpenError(remaining);
    }
  }
}
```

---

## Pattern 3: Retry Queue

### When to Use
- Bulk/batch API operations (e.g., syncing 10,000 records)
- Need to respect global rate limits across concurrent requests
- Want persistent retries that survive process restarts (advanced)

### Design Rules

1. **Concurrency limit**: cap concurrent in-flight requests (default: 10)
2. **Rate limiter**: token bucket or sliding window to enforce requests-per-second
3. **Queue priority**: failed retries go back into the queue with exponential delay metadata
4. **Dead letter**: after max retries, move to a dead-letter list for manual inspection
5. **Progress tracking**: emit/log progress (completed, failed, pending counts)

### Python Implementation

```python
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass(order=True)
class RetryTask:
    priority: float  # lower = run sooner; use scheduled time as priority
    item: Any = field(compare=False)
    attempt: int = field(default=0, compare=False)


class RetryQueue:
    """Async retry queue with concurrency control and dead-letter handling."""

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

        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._queue: asyncio.PriorityQueue[RetryTask] = asyncio.PriorityQueue()
        self.dead_letter: list[Any] = []
        self._completed = 0
        self._failed = 0

    async def submit(self, item: Any) -> None:
        """Add an item to the queue."""
        await self._queue.put(RetryTask(priority=0, item=item, attempt=0))

    async def submit_many(self, items: list[Any]) -> None:
        """Add multiple items to the queue."""
        for item in items:
            await self.submit(item)

    async def _process_one(self, task: RetryTask) -> None:
        """Process a single task with semaphore-controlled concurrency."""
        async with self._semaphore:
            try:
                success = await self.worker_fn(task.item)
            except Exception as exc:
                logger.error("Worker exception for %s: %s", task.item, exc)
                success = False

            if success:
                self._completed += 1
                return

            task.attempt += 1
            if task.attempt > self.max_retries:
                logger.error("Dead-lettered: %s after %d attempts", task.item, task.attempt)
                self.dead_letter.append(task.item)
                self._failed += 1
                return

            delay = min(self.base_delay * (2 ** (task.attempt - 1)), self.max_delay)
            logger.warning("Re-queuing %s: attempt=%d delay=%.1fs", task.item, task.attempt, delay)
            await asyncio.sleep(delay)
            task.priority = asyncio.get_event_loop().time() + delay
            await self._queue.put(task)

    async def run(self) -> dict:
        """Drain the queue until all items are processed or dead-lettered."""
        workers: list[asyncio.Task] = []

        while not self._queue.empty() or any(not w.done() for w in workers):
            # Launch workers up to concurrency limit
            while not self._queue.empty():
                task = await self._queue.get()
                worker = asyncio.create_task(self._process_one(task))
                workers.append(worker)

            # Wait for at least one to finish before checking again
            if workers:
                done, _ = await asyncio.wait(workers, return_when=asyncio.FIRST_COMPLETED)
                workers = [w for w in workers if not w.done()]

        return {
            "completed": self._completed,
            "failed": self._failed,
            "dead_letter_count": len(self.dead_letter),
        }
```

### Node.js Implementation

```typescript
import { setTimeout } from "timers/promises";

interface RetryTask<T> {
  item: T;
  attempt: number;
}

interface QueueStats {
  completed: number;
  failed: number;
  deadLetterCount: number;
}

class RetryQueue<T> {
  private queue: RetryTask<T>[] = [];
  private inFlight = 0;
  private completed = 0;
  private failed = 0;
  readonly deadLetter: T[] = [];

  constructor(
    private readonly workerFn: (item: T) => Promise<boolean>,
    private readonly maxConcurrency: number = 10,
    private readonly maxRetries: number = 5,
    private readonly baseDelay: number = 1000,
    private readonly maxDelay: number = 60_000,
  ) {}

  submit(item: T): void {
    this.queue.push({ item, attempt: 0 });
  }

  submitMany(items: T[]): void {
    items.forEach((item) => this.submit(item));
  }

  async run(): Promise<QueueStats> {
    const running: Promise<void>[] = [];

    const processNext = async (): Promise<void> => {
      while (this.queue.length > 0) {
        const task = this.queue.shift()!;
        this.inFlight++;

        let success = false;
        try {
          success = await this.workerFn(task.item);
        } catch (err) {
          console.error(`Worker error for ${task.item}:`, err);
        }
        this.inFlight--;

        if (success) {
          this.completed++;
          continue;
        }

        task.attempt++;
        if (task.attempt > this.maxRetries) {
          console.error(`Dead-lettered: ${task.item} after ${task.attempt} attempts`);
          this.deadLetter.push(task.item);
          this.failed++;
          continue;
        }

        const delay = Math.min(this.baseDelay * 2 ** (task.attempt - 1), this.maxDelay);
        console.warn(`Re-queuing ${task.item}: attempt=${task.attempt} delay=${delay}ms`);
        await setTimeout(delay);
        this.queue.push(task);
      }
    };

    // Launch concurrent workers
    for (let i = 0; i < this.maxConcurrency; i++) {
      running.push(processNext());
    }

    await Promise.all(running);

    return {
      completed: this.completed,
      failed: this.failed,
      deadLetterCount: this.deadLetter.length,
    };
  }
}
```

---

## Combining All Three Patterns

For production-grade resilient API clients, layer the patterns together:

```
Request → Circuit Breaker Check → Rate Limiter → HTTP Call with Backoff
                                                         ↓ (if retryable failure)
                                                   Retry Queue (re-enqueue)
                                                         ↓ (if max retries exceeded)
                                                   Dead Letter
```

### Python — Integrated Client

```python
class ResilientApiClient:
    """Combines circuit breaker, backoff, and retry queue."""

    def __init__(
        self,
        base_url: str,
        max_concurrency: int = 10,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.circuit = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout,
            name=base_url,
        )
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Single request with circuit breaker + backoff."""
        self.circuit.check()  # raises CircuitOpenError if open

        async with self.semaphore:
            response = await request_with_backoff(
                self.client, method, f"{path}", **kwargs
            )

        if response.status_code in RETRYABLE_STATUS_CODES:
            self.circuit.record_failure()
        else:
            self.circuit.record_success()

        return response

    async def close(self) -> None:
        await self.client.aclose()
```

### Node.js — Integrated Client

```typescript
class ResilientApiClient {
  private circuit: CircuitBreaker;
  private inFlight = 0;

  constructor(
    private readonly baseUrl: string,
    private readonly maxConcurrency: number = 10,
    circuitFailureThreshold: number = 5,
    circuitRecoveryTimeoutMs: number = 30_000,
  ) {
    this.circuit = new CircuitBreaker(
      circuitFailureThreshold,
      circuitRecoveryTimeoutMs,
      baseUrl,
    );
  }

  async request(path: string, init?: RequestInit): Promise<Response> {
    this.circuit.check(); // throws CircuitOpenError if open

    // Concurrency wait
    while (this.inFlight >= this.maxConcurrency) {
      await setTimeout(50);
    }
    this.inFlight++;

    try {
      const response = await fetchWithBackoff(`${this.baseUrl}${path}`, init);

      if (RETRYABLE_STATUS_CODES.has(response.status)) {
        this.circuit.recordFailure();
      } else {
        this.circuit.recordSuccess();
      }

      return response;
    } finally {
      this.inFlight--;
    }
  }
}
```

---

## Configuration Recommendations

| Parameter | Default | Tune When |
|---|---|---|
| `base_delay` | 1s | API docs specify minimum wait |
| `max_delay` | 60s | API has known recovery patterns |
| `max_retries` | 5 | Higher for critical batch jobs, lower for user-facing |
| `circuit failure_threshold` | 5 | Lower (3) for fast failure detection, higher (10) for noisy APIs |
| `circuit recovery_timeout` | 30s | Match API's typical recovery time |
| `max_concurrency` | 10 | Match API's rate limit (e.g., 100 req/min → ~2 concurrent) |

## Common API Rate Limit Headers

Parse these from responses to auto-tune behavior:

| Header | Meaning | Example |
|---|---|---|
| `Retry-After` | Seconds (or date) to wait | `30` or `Thu, 01 Dec 2025 16:00:00 GMT` |
| `X-RateLimit-Limit` | Max requests in window | `1000` |
| `X-RateLimit-Remaining` | Requests left in window | `42` |
| `X-RateLimit-Reset` | Unix timestamp when window resets | `1701446400` |
| `RateLimit-Policy` | IETF draft rate limit policy | `100;w=60` (100 per 60s) |

### Proactive Throttling (Pre-emptive Backoff)

When `X-RateLimit-Remaining` is available, slow down **before** hitting 429:

```python
remaining = int(response.headers.get("X-RateLimit-Remaining", "999"))
reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))

if remaining < 10 and reset_at > 0:
    wait = max(0, reset_at - time.time())
    spread = wait / max(remaining, 1)  # spread remaining calls across window
    await asyncio.sleep(spread)
```

## Testing Strategies

1. **Unit test backoff math**: verify delay calculation for each attempt
2. **Mock 429 responses**: simulate `Retry-After` header parsing
3. **Circuit breaker state transitions**: assert CLOSED → OPEN → HALF_OPEN → CLOSED
4. **Integration test with httpbin**: `https://httpbin.org/status/429` returns 429
5. **Chaos testing**: randomly inject failures to verify end-to-end resilience

## Anti-Patterns to Avoid

- **Fixed-delay retry without jitter** — causes thundering herd when multiple clients retry simultaneously
- **Retrying non-idempotent requests** (POST creating resources) without deduplication keys
- **Ignoring `Retry-After`** — some APIs will escalate to longer bans
- **No circuit breaker** — burning through all retries on a completely down service wastes time and resources
- **Infinite retries** — always cap with `max_retries`; use dead-letter for inspection
- **Retrying 401/403** — these are auth errors, not transient failures
