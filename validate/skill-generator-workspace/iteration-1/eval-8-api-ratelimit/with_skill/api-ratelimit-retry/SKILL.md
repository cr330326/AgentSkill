---
name: api-ratelimit-retry
description: >
  Implement robust API rate-limit handling with exponential backoff, circuit breaker,
  and retry queue patterns in Python and Node.js. Use when the user asks to "handle
  rate limiting", "implement backoff", "add retry logic", "circuit breaker", "retry
  queue", "429 handling", "API throttling", or needs resilient third-party API
  integration. Also triggers for "rate limit strategy", "backoff strategy",
  "resilient HTTP client", or "fault-tolerant API calls".
  Do NOT use for authentication/OAuth flows, API design (server-side rate limiting),
  or load balancing across multiple API providers.
---

# API Rate-Limit & Retry Strategy Guide

## Overview

When calling third-party APIs, rate limiting (HTTP 429) is inevitable at scale. This skill provides battle-tested patterns for handling it gracefully: exponential backoff for individual retries, circuit breakers to avoid hammering a down service, and retry queues for deferring work under sustained pressure.

## Decision: Pick the Right Pattern

| Situation | Pattern | Why |
|-----------|---------|-----|
| Occasional 429s from a single endpoint | **Exponential backoff** | Simple, self-contained, handles transient spikes |
| Sustained failures or degraded upstream | **Circuit breaker** | Stops wasting resources on a known-bad dependency |
| High-throughput pipeline with bursty traffic | **Retry queue** | Decouples failed calls from the hot path, retries async |
| Mission-critical calls with mixed failure modes | **All three combined** | Backoff inside the circuit breaker, overflow to queue |

Read the references for full implementations:
- `references/exponential-backoff.md` — core backoff algorithm + jitter
- `references/circuit-breaker.md` — state machine and threshold tuning
- `references/retry-queue.md` — queue-based deferred retry architecture

## Quick Start

### 1. Exponential Backoff with Jitter

The simplest and most common pattern. Always add jitter to prevent thundering herd.

**Formula**: `delay = min(base * 2^attempt + random_jitter, max_delay)`

#### Python

```python
import asyncio
import random
import httpx

async def fetch_with_backoff(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> httpx.Response:
    for attempt in range(max_retries + 1):
        response = await client.get(url)
        if response.status_code != 429:
            return response

        if attempt == max_retries:
            response.raise_for_status()

        # Respect Retry-After header when present
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            delay = float(retry_after)
        else:
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, delay * 0.5)  # jitter

        print(f"Rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1})")
        await asyncio.sleep(delay)
```

#### Node.js

```typescript
async function fetchWithBackoff(
  url: string,
  options: {
    maxRetries?: number;
    baseDelay?: number;
    maxDelay?: number;
  } = {}
): Promise<Response> {
  const { maxRetries = 5, baseDelay = 1000, maxDelay = 60_000 } = options;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url);
    if (response.status !== 429) return response;

    if (attempt === maxRetries) {
      throw new Error(`Rate limited after ${maxRetries} retries`);
    }

    // Respect Retry-After header when present
    const retryAfter = response.headers.get("Retry-After");
    let delay: number;
    if (retryAfter) {
      delay = parseFloat(retryAfter) * 1000;
    } else {
      delay = Math.min(baseDelay * 2 ** attempt, maxDelay);
      delay += Math.random() * delay * 0.5; // jitter
    }

    console.log(`Rate limited. Retrying in ${(delay / 1000).toFixed(1)}s (attempt ${attempt + 1})`);
    await new Promise((r) => setTimeout(r, delay));
  }

  throw new Error("Unreachable");
}
```

### 2. Circuit Breaker

Use when an upstream service is consistently failing. The circuit breaker prevents your system from sending requests it knows will fail, giving the upstream time to recover.

**States**: CLOSED (normal) -> OPEN (blocking) -> HALF_OPEN (probing)

#### Python

```python
import time
from enum import Enum
from typing import Callable, Awaitable

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0

    async def call(self, func: Callable[..., Awaitable], *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitOpenError(
                    f"Circuit open. Retry after {self.recovery_timeout}s"
                )

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError("Half-open call limit reached")
            self.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

class CircuitOpenError(Exception):
    pass
```

#### Node.js

```typescript
enum CircuitState {
  CLOSED = "closed",
  OPEN = "open",
  HALF_OPEN = "half_open",
}

class CircuitBreaker {
  private state = CircuitState.CLOSED;
  private failureCount = 0;
  private lastFailureTime = 0;
  private halfOpenCalls = 0;

  constructor(
    private failureThreshold = 5,
    private recoveryTimeout = 30_000,
    private halfOpenMaxCalls = 1
  ) {}

  async call<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() - this.lastFailureTime >= this.recoveryTimeout) {
        this.state = CircuitState.HALF_OPEN;
        this.halfOpenCalls = 0;
      } else {
        throw new Error("Circuit open. Upstream is unavailable.");
      }
    }

    if (this.state === CircuitState.HALF_OPEN) {
      if (this.halfOpenCalls >= this.halfOpenMaxCalls) {
        throw new Error("Half-open call limit reached");
      }
      this.halfOpenCalls++;
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (err) {
      this.onFailure();
      throw err;
    }
  }

  private onSuccess() {
    this.failureCount = 0;
    this.state = CircuitState.CLOSED;
  }

  private onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    if (this.failureCount >= this.failureThreshold) {
      this.state = CircuitState.OPEN;
    }
  }
}
```

### 3. Retry Queue

Use when you have high-throughput workloads and cannot block the caller on retries. Failed requests go into a queue and are retried asynchronously with backoff.

See `references/retry-queue.md` for full implementations in both languages.

#### Python (minimal)

```python
import asyncio
from dataclasses import dataclass, field

@dataclass
class RetryItem:
    url: str
    attempt: int = 0
    max_retries: int = 5

class RetryQueue:
    def __init__(self, concurrency: int = 3):
        self._queue: asyncio.Queue[RetryItem] = asyncio.Queue()
        self._concurrency = concurrency

    async def enqueue(self, item: RetryItem):
        await self._queue.put(item)

    async def start(self, handler):
        workers = [
            asyncio.create_task(self._worker(handler))
            for _ in range(self._concurrency)
        ]
        await asyncio.gather(*workers)

    async def _worker(self, handler):
        while True:
            item = await self._queue.get()
            try:
                await handler(item)
            except Exception:
                item.attempt += 1
                if item.attempt < item.max_retries:
                    delay = min(2 ** item.attempt, 60)
                    await asyncio.sleep(delay)
                    await self._queue.put(item)
                else:
                    print(f"Permanently failed: {item.url}")
            finally:
                self._queue.task_done()
```

#### Node.js (minimal)

```typescript
interface RetryItem {
  url: string;
  attempt: number;
  maxRetries: number;
}

class RetryQueue {
  private queue: RetryItem[] = [];
  private processing = false;

  enqueue(item: RetryItem) {
    this.queue.push(item);
    if (!this.processing) this.process();
  }

  private async process() {
    this.processing = true;
    while (this.queue.length > 0) {
      const item = this.queue.shift()!;
      try {
        await this.handle(item);
      } catch {
        item.attempt++;
        if (item.attempt < item.maxRetries) {
          const delay = Math.min(2 ** item.attempt * 1000, 60_000);
          await new Promise((r) => setTimeout(r, delay));
          this.queue.push(item);
        } else {
          console.error(`Permanently failed: ${item.url}`);
        }
      }
    }
    this.processing = false;
  }

  private async handle(item: RetryItem): Promise<void> {
    const res = await fetch(item.url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  }
}
```

## Combining All Three Patterns

For production systems, layer the patterns:

```
Request
  -> Circuit Breaker (gate: is upstream healthy?)
    -> Exponential Backoff (retry transient failures inline)
      -> on exhausted retries: enqueue to Retry Queue (async deferred retry)
```

See `references/combined-example.md` for a full wired-up example.

## Tuning Guidelines

| Parameter | Recommended Start | Adjust When |
|-----------|------------------|-------------|
| `base_delay` | 1s | API docs specify different minimum |
| `max_delay` | 60s | Upstream has known recovery patterns |
| `max_retries` | 3-5 | Higher for idempotent ops, lower for user-facing |
| `jitter` | 0-50% of delay | Increase under high concurrency |
| `failure_threshold` (CB) | 5 | Lower for critical paths, higher for noisy APIs |
| `recovery_timeout` (CB) | 30s | Match to upstream's typical recovery time |
| `queue_concurrency` | 3-5 | Match to API's rate limit window |

## Common Mistakes

1. **No jitter** — All clients retry at the same instant, causing thundering herd
2. **Ignoring `Retry-After`** — The server tells you exactly when to retry; use it
3. **Retrying non-idempotent requests** — POST that creates a resource may duplicate; add idempotency keys
4. **Infinite retries** — Always cap retries; use a dead-letter mechanism for permanent failures
5. **Circuit breaker per-instance, not per-upstream** — Share state across calls to the same dependency
6. **Logging retries silently** — Always surface retry metrics for observability
