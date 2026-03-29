# Retry Queue — Deep Reference

## Architecture

```
Producer (API caller)
    │
    │  on failure / rate limit
    ▼
┌──────────────┐      workers (bounded concurrency)
│  Retry Queue │ ──── Worker 1 ── attempt with backoff ── success/dead-letter
│  (in-memory  │ ──── Worker 2
│   or durable)│ ──── Worker 3
└──────────────┘
    │
    │  max retries exhausted
    ▼
Dead Letter Queue / Error Log
```

## When to Use

| Scenario | Use Retry Queue? |
|----------|-----------------|
| Background data sync | Yes — decouple and retry async |
| User-facing API call | No — use inline backoff; user is waiting |
| Webhook delivery | Yes — queued retries with exponential backoff |
| Bulk import pipeline | Yes — items can fail independently |

## Design Decisions

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Storage | In-memory queue | Persistent (Redis/DB) | In-memory for dev/small scale; persistent for production |
| Ordering | FIFO | Priority | FIFO unless you have urgent/normal lanes |
| Concurrency | Single worker | Worker pool | Pool (3-5 workers) to balance throughput and rate limits |
| Dead letter | Log and drop | Separate queue | Separate queue for auditability |

## Python — Full Implementation

```python
import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ItemStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RetryItem:
    """A unit of work to be retried."""
    id: str
    payload: Any
    attempt: int = 0
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    status: ItemStatus = ItemStatus.PENDING
    created_at: float = field(default_factory=time.time)
    last_error: Optional[str] = None

    @property
    def next_delay(self) -> float:
        """Compute the next backoff delay with jitter."""
        delay = min(self.base_delay * (2 ** self.attempt), self.max_delay)
        delay += random.uniform(0, delay * 0.5)
        return delay

    @property
    def is_exhausted(self) -> bool:
        return self.attempt >= self.max_retries


@dataclass
class QueueStats:
    enqueued: int = 0
    completed: int = 0
    failed_permanently: int = 0
    retries: int = 0


class RetryQueue:
    """
    Async retry queue with bounded concurrency and exponential backoff.

    Usage:
        queue = RetryQueue(concurrency=3)

        async def process(item: RetryItem):
            response = await call_api(item.payload)
            if response.status_code == 429:
                raise RateLimitError()

        queue.enqueue(RetryItem(id="1", payload={"url": "..."}))
        await queue.run(process)
    """

    def __init__(self, concurrency: int = 3):
        self._queue: asyncio.Queue[RetryItem] = asyncio.Queue()
        self._dead_letter: list[RetryItem] = []
        self._concurrency = concurrency
        self._stats = QueueStats()
        self._running = False

    @property
    def stats(self) -> QueueStats:
        return self._stats

    @property
    def dead_letter(self) -> list[RetryItem]:
        return list(self._dead_letter)

    def enqueue(self, item: RetryItem):
        self._queue.put_nowait(item)
        self._stats.enqueued += 1
        logger.debug(f"Enqueued item {item.id}")

    async def run(
        self,
        handler: Callable[[RetryItem], Awaitable[None]],
        *,
        shutdown_when_empty: bool = True,
    ):
        """
        Start workers and process the queue.

        Args:
            handler: Async function that processes an item. Raise on failure.
            shutdown_when_empty: If True, stop after the queue is drained.
        """
        self._running = True
        workers = [
            asyncio.create_task(self._worker(handler, worker_id=i))
            for i in range(self._concurrency)
        ]

        if shutdown_when_empty:
            await self._queue.join()
            self._running = False
            for w in workers:
                w.cancel()
        else:
            await asyncio.gather(*workers)

    async def _worker(
        self,
        handler: Callable[[RetryItem], Awaitable[None]],
        worker_id: int,
    ):
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            item.status = ItemStatus.PROCESSING
            try:
                await handler(item)
                item.status = ItemStatus.COMPLETED
                self._stats.completed += 1
                logger.info(f"[worker-{worker_id}] Completed {item.id}")
            except Exception as exc:
                item.last_error = str(exc)
                item.attempt += 1
                self._stats.retries += 1

                if item.is_exhausted:
                    item.status = ItemStatus.FAILED
                    self._dead_letter.append(item)
                    self._stats.failed_permanently += 1
                    logger.error(
                        f"[worker-{worker_id}] Permanently failed {item.id}: {exc}"
                    )
                else:
                    delay = item.next_delay
                    logger.warning(
                        f"[worker-{worker_id}] {item.id} failed (attempt {item.attempt}), "
                        f"retrying in {delay:.1f}s: {exc}"
                    )
                    await asyncio.sleep(delay)
                    item.status = ItemStatus.PENDING
                    await self._queue.put(item)
            finally:
                self._queue.task_done()


# --- Example usage ---

async def example():
    import httpx

    queue = RetryQueue(concurrency=3)

    async def call_api(item: RetryItem):
        async with httpx.AsyncClient() as client:
            resp = await client.get(item.payload["url"])
            if resp.status_code == 429:
                raise Exception(f"Rate limited: {resp.status_code}")
            resp.raise_for_status()

    # Enqueue work
    for i in range(10):
        queue.enqueue(RetryItem(
            id=f"req-{i}",
            payload={"url": f"https://api.example.com/items/{i}"},
            max_retries=3,
        ))

    await queue.run(call_api)

    print(f"Stats: {queue.stats}")
    if queue.dead_letter:
        print(f"Dead letter items: {[item.id for item in queue.dead_letter]}")
```

## Node.js — Full Implementation

```typescript
import { EventEmitter } from "events";

type ItemStatus = "pending" | "processing" | "completed" | "failed";

interface RetryItemConfig {
  id: string;
  payload: unknown;
  maxRetries?: number;
  baseDelay?: number;   // ms
  maxDelay?: number;    // ms
}

class RetryItem {
  readonly id: string;
  readonly payload: unknown;
  readonly maxRetries: number;
  readonly baseDelay: number;
  readonly maxDelay: number;

  attempt = 0;
  status: ItemStatus = "pending";
  lastError: string | null = null;
  readonly createdAt = Date.now();

  constructor(config: RetryItemConfig) {
    this.id = config.id;
    this.payload = config.payload;
    this.maxRetries = config.maxRetries ?? 5;
    this.baseDelay = config.baseDelay ?? 1000;
    this.maxDelay = config.maxDelay ?? 60_000;
  }

  get nextDelay(): number {
    const delay = Math.min(this.baseDelay * 2 ** this.attempt, this.maxDelay);
    return delay + Math.random() * delay * 0.5;
  }

  get isExhausted(): boolean {
    return this.attempt >= this.maxRetries;
  }
}

interface QueueStats {
  enqueued: number;
  completed: number;
  failedPermanently: number;
  retries: number;
}

type ItemHandler = (item: RetryItem) => Promise<void>;

class RetryQueue extends EventEmitter {
  private queue: RetryItem[] = [];
  private deadLetter: RetryItem[] = [];
  private activeWorkers = 0;
  private stats: QueueStats = {
    enqueued: 0,
    completed: 0,
    failedPermanently: 0,
    retries: 0,
  };

  constructor(private readonly concurrency = 3) {
    super();
  }

  getStats(): QueueStats {
    return { ...this.stats };
  }

  getDeadLetter(): RetryItem[] {
    return [...this.deadLetter];
  }

  enqueue(item: RetryItem): void {
    this.queue.push(item);
    this.stats.enqueued++;
    this.emit("enqueued", item);
  }

  /**
   * Process items in the queue with bounded concurrency.
   * Resolves when all items are processed (or permanently failed).
   */
  async run(handler: ItemHandler): Promise<QueueStats> {
    return new Promise((resolve) => {
      const tick = async () => {
        while (this.queue.length > 0 && this.activeWorkers < this.concurrency) {
          const item = this.queue.shift()!;
          this.activeWorkers++;
          this.processItem(handler, item).then(() => {
            this.activeWorkers--;
            if (this.queue.length > 0) {
              tick();
            } else if (this.activeWorkers === 0) {
              resolve(this.getStats());
            }
          });
        }

        if (this.queue.length === 0 && this.activeWorkers === 0) {
          resolve(this.getStats());
        }
      };

      tick();
    });
  }

  private async processItem(handler: ItemHandler, item: RetryItem): Promise<void> {
    item.status = "processing";

    try {
      await handler(item);
      item.status = "completed";
      this.stats.completed++;
      this.emit("completed", item);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      item.lastError = errorMessage;
      item.attempt++;
      this.stats.retries++;

      if (item.isExhausted) {
        item.status = "failed";
        this.deadLetter.push(item);
        this.stats.failedPermanently++;
        this.emit("dead-letter", item);
      } else {
        const delay = item.nextDelay;
        this.emit("retry", item, delay);
        await new Promise((r) => setTimeout(r, delay));
        item.status = "pending";
        this.queue.push(item);
      }
    }
  }
}

// --- Example usage ---

async function example() {
  const queue = new RetryQueue(3);

  queue.on("completed", (item: RetryItem) => {
    console.log(`Completed: ${item.id}`);
  });

  queue.on("dead-letter", (item: RetryItem) => {
    console.error(`Permanently failed: ${item.id} — ${item.lastError}`);
  });

  queue.on("retry", (item: RetryItem, delay: number) => {
    console.log(`Retrying ${item.id} in ${(delay / 1000).toFixed(1)}s (attempt ${item.attempt})`);
  });

  // Enqueue work
  for (let i = 0; i < 10; i++) {
    queue.enqueue(new RetryItem({
      id: `req-${i}`,
      payload: { url: `https://api.example.com/items/${i}` },
      maxRetries: 3,
    }));
  }

  const handler: ItemHandler = async (item) => {
    const resp = await fetch((item.payload as any).url);
    if (resp.status === 429) throw new Error(`Rate limited: ${resp.status}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  };

  const stats = await queue.run(handler);
  console.log("Final stats:", stats);
}

export { RetryQueue, RetryItem, type RetryItemConfig, type ItemHandler };
```

## Persistent Queue with Redis

For production workloads that need durability across restarts, use Redis as the backing store. The key idea: use a sorted set with `score = next_retry_timestamp`.

```python
# Python sketch — Redis-backed retry queue
import redis.asyncio as redis

class RedisRetryQueue:
    def __init__(self, client: redis.Redis, key: str = "retry_queue"):
        self.client = client
        self.key = key

    async def enqueue(self, item_id: str, retry_at: float):
        await self.client.zadd(self.key, {item_id: retry_at})

    async def dequeue_ready(self, now: float, count: int = 10) -> list[str]:
        items = await self.client.zrangebyscore(
            self.key, "-inf", now, start=0, num=count
        )
        if items:
            await self.client.zrem(self.key, *items)
        return [i.decode() for i in items]
```

```typescript
// Node.js sketch — Redis-backed retry queue
import { Redis } from "ioredis";

class RedisRetryQueue {
  constructor(
    private redis: Redis,
    private key = "retry_queue"
  ) {}

  async enqueue(itemId: string, retryAt: number): Promise<void> {
    await this.redis.zadd(this.key, retryAt, itemId);
  }

  async dequeueReady(now: number, count = 10): Promise<string[]> {
    const items = await this.redis.zrangebyscore(
      this.key, "-inf", now, "LIMIT", 0, count
    );
    if (items.length > 0) {
      await this.redis.zrem(this.key, ...items);
    }
    return items;
  }
}
```
