# Combined Example — All Three Patterns Together

## Architecture

Layer the patterns so each addresses a different failure mode:

```
Caller
  │
  ▼
Circuit Breaker ── Is the upstream healthy?
  │                  OPEN → fast fail or enqueue
  │                  CLOSED/HALF_OPEN → proceed
  ▼
Exponential Backoff ── Retry transient 429/5xx inline
  │                      Success → return to caller
  │                      Exhausted → overflow to queue
  ▼
Retry Queue ── Deferred async retry with backoff
                 Success → log + notify
                 Exhausted → dead letter
```

## Python — Full Combined Implementation

```python
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

# Import from the other reference modules (or inline them)
# from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError
# from .backoff import request_with_backoff
# from .retry_queue import RetryQueue, RetryItem

logger = logging.getLogger(__name__)


@dataclass
class ResilientClientConfig:
    # Backoff settings
    max_inline_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0

    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: float = 30.0

    # Queue settings
    queue_concurrency: int = 3
    max_queue_retries: int = 5


class ResilientApiClient:
    """
    Wraps an HTTP client with circuit breaker, exponential backoff,
    and retry queue for comprehensive rate-limit handling.
    """

    def __init__(self, config: Optional[ResilientClientConfig] = None):
        self.config = config or ResilientClientConfig()
        self.circuit = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=self.config.failure_threshold,
            recovery_timeout=self.config.recovery_timeout,
        ))
        self.retry_queue = RetryQueue(concurrency=self.config.queue_concurrency)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        *,
        queue_on_failure: bool = True,
        **kwargs,
    ) -> httpx.Response:
        """
        Make a resilient API request.

        1. Check circuit breaker — fail fast if upstream is down.
        2. Try inline with exponential backoff.
        3. If inline retries exhausted, optionally enqueue for async retry.
        """
        assert self._client is not None, "Use async context manager"

        try:
            # Step 1: Circuit breaker gate
            response = await self.circuit.call(
                self._request_with_backoff,
                method, url, **kwargs,
            )
            return response

        except CircuitOpenError:
            logger.warning(f"Circuit open for {url}")
            if queue_on_failure:
                self._enqueue(method, url, kwargs)
                raise  # Caller handles the error; item queued for later
            raise

        except httpx.HTTPStatusError as exc:
            # Inline retries exhausted
            if queue_on_failure and exc.response.status_code in (429, 502, 503, 504):
                logger.warning(f"Inline retries exhausted for {url}, enqueueing")
                self._enqueue(method, url, kwargs)
            raise

    async def _request_with_backoff(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response:
        return await request_with_backoff(
            self._client,
            method,
            url,
            max_retries=self.config.max_inline_retries,
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay,
            **kwargs,
        )

    def _enqueue(self, method: str, url: str, kwargs: dict):
        item = RetryItem(
            id=f"{method}:{url}:{id(kwargs)}",
            payload={"method": method, "url": url, "kwargs": kwargs},
            max_retries=self.config.max_queue_retries,
        )
        self.retry_queue.enqueue(item)

    async def process_queue(self):
        """Process all queued retry items. Call periodically or on shutdown."""
        async def handler(item: RetryItem):
            p = item.payload
            await self._request_with_backoff(p["method"], p["url"], **p["kwargs"])

        await self.retry_queue.run(handler)


# --- Usage ---

async def main():
    config = ResilientClientConfig(
        max_inline_retries=3,
        failure_threshold=5,
        recovery_timeout=30.0,
        queue_concurrency=2,
    )

    async with ResilientApiClient(config) as client:
        try:
            resp = await client.request("GET", "https://api.example.com/data")
            print(f"Success: {resp.status_code}")
        except CircuitOpenError:
            print("Service unavailable — request queued for retry")
        except httpx.HTTPStatusError as e:
            print(f"Failed: {e.response.status_code} — request queued")

        # Process queued items (could be on a timer or shutdown hook)
        await client.process_queue()

        # Check dead letter
        for item in client.retry_queue.dead_letter:
            print(f"Permanently failed: {item.id}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Node.js — Full Combined Implementation

```typescript
interface ResilientClientConfig {
  // Backoff
  maxInlineRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
  // Circuit breaker
  failureThreshold?: number;
  recoveryTimeout?: number;
  // Queue
  queueConcurrency?: number;
  maxQueueRetries?: number;
}

class ResilientApiClient {
  private circuit: CircuitBreaker;
  private retryQueue: RetryQueue;
  private config: Required<ResilientClientConfig>;

  constructor(config: ResilientClientConfig = {}) {
    this.config = {
      maxInlineRetries: config.maxInlineRetries ?? 3,
      baseDelay: config.baseDelay ?? 1000,
      maxDelay: config.maxDelay ?? 30_000,
      failureThreshold: config.failureThreshold ?? 5,
      recoveryTimeout: config.recoveryTimeout ?? 30_000,
      queueConcurrency: config.queueConcurrency ?? 3,
      maxQueueRetries: config.maxQueueRetries ?? 5,
    };

    this.circuit = new CircuitBreaker({
      failureThreshold: this.config.failureThreshold,
      recoveryTimeout: this.config.recoveryTimeout,
      isFailure: (err) => {
        // Only count server errors and rate limits as circuit failures
        if (err instanceof HttpError) {
          return [429, 502, 503, 504].includes(err.status);
        }
        return true;
      },
    });

    this.retryQueue = new RetryQueue(this.config.queueConcurrency);

    // Wire up queue events for observability
    this.retryQueue.on("dead-letter", (item: RetryItem) => {
      console.error(`[dead-letter] Permanently failed: ${item.id}`);
    });

    this.retryQueue.on("retry", (item: RetryItem, delay: number) => {
      console.log(
        `[queue-retry] ${item.id} attempt ${item.attempt}, ` +
        `next in ${(delay / 1000).toFixed(1)}s`
      );
    });
  }

  /**
   * Make a resilient HTTP request.
   *
   * 1. Circuit breaker gate
   * 2. Inline exponential backoff
   * 3. Overflow to retry queue on exhaustion
   */
  async request(
    url: string,
    init: RequestInit = {},
    options: { queueOnFailure?: boolean } = {}
  ): Promise<Response> {
    const { queueOnFailure = true } = options;

    try {
      return await this.circuit.call(() =>
        this.fetchWithInlineBackoff(url, init)
      );
    } catch (err) {
      if (err instanceof CircuitOpenError && queueOnFailure) {
        console.warn(`Circuit open for ${url} — enqueueing`);
        this.enqueue(url, init);
      } else if (err instanceof HttpError && queueOnFailure) {
        console.warn(`Inline retries exhausted for ${url} — enqueueing`);
        this.enqueue(url, init);
      }
      throw err;
    }
  }

  private async fetchWithInlineBackoff(
    url: string,
    init: RequestInit
  ): Promise<Response> {
    return fetchWithBackoff(url, init, {
      maxRetries: this.config.maxInlineRetries,
      baseDelay: this.config.baseDelay,
      maxDelay: this.config.maxDelay,
    });
  }

  private enqueue(url: string, init: RequestInit): void {
    this.retryQueue.enqueue(
      new RetryItem({
        id: `${init.method ?? "GET"}:${url}:${Date.now()}`,
        payload: { url, init },
        maxRetries: this.config.maxQueueRetries,
      })
    );
  }

  /**
   * Process queued retry items. Call periodically or before shutdown.
   */
  async processQueue(): Promise<void> {
    const handler: ItemHandler = async (item) => {
      const { url, init } = item.payload as { url: string; init: RequestInit };
      const resp = await fetch(url, init);
      if (!resp.ok) throw new HttpError(resp.status, resp.statusText);
    };

    const stats = await this.retryQueue.run(handler);
    console.log("Queue processing complete:", stats);
  }

  getCircuitState() {
    return this.circuit.getState();
  }

  getQueueStats() {
    return this.retryQueue.getStats();
  }
}

class HttpError extends Error {
  constructor(
    public readonly status: number,
    statusText: string
  ) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = "HttpError";
  }
}

// --- Usage ---

async function main() {
  const client = new ResilientApiClient({
    maxInlineRetries: 3,
    failureThreshold: 5,
    recoveryTimeout: 30_000,
    queueConcurrency: 2,
  });

  try {
    const resp = await client.request("https://api.example.com/data");
    const data = await resp.json();
    console.log("Success:", data);
  } catch (err) {
    if (err instanceof CircuitOpenError) {
      console.log("Service unavailable — request queued for retry");
    } else {
      console.error("Request failed:", err);
    }
  }

  // Process queued items
  await client.processQueue();
}

export { ResilientApiClient, type ResilientClientConfig, HttpError };
```

## Integration Checklist

- [ ] Circuit breaker wraps the backoff function, not the raw HTTP call
- [ ] Backoff respects `Retry-After` headers from the upstream API
- [ ] Queue items include enough context to reconstruct the request
- [ ] Dead letter items are logged with the final error and all attempt metadata
- [ ] Metrics are emitted for: circuit state changes, retry counts, queue depth, dead letters
- [ ] Non-idempotent requests (POST) include idempotency keys to prevent duplicates
- [ ] Shutdown hook drains the queue gracefully before exit
