# Node.js / TypeScript Reference — Resilient API Client

Complete, production-ready module combining all three patterns.

## Dependencies

No external dependencies required — uses native `fetch` (Node 18+) and `timers/promises`.

For Node < 18, install `node-fetch`:
```
npm install node-fetch
```

## Full Module: `resilient-client.ts`

```typescript
/**
 * Resilient API client with exponential backoff, circuit breaker, and retry queue.
 *
 * Usage:
 *   const client = new ResilientApiClient("https://api.example.com");
 *   const response = await client.request("/users/123");
 *
 *   // Bulk operations
 *   const queue = new RetryQueue(processItem, { maxConcurrency: 5 });
 *   queue.submitMany(items);
 *   const stats = await queue.run();
 */

import { setTimeout } from "timers/promises";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

// ---------------------------------------------------------------------------
// Retry-After Parsing
// ---------------------------------------------------------------------------

function parseRetryAfter(response: Response): number | null {
  const value =
    response.headers.get("Retry-After") ??
    response.headers.get("retry-after");
  if (!value) return null;

  const seconds = Number(value);
  if (!Number.isNaN(seconds)) return seconds * 1000;

  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return Math.max(date.getTime() - Date.now(), 0);
  }
  return null;
}

interface RateLimitInfo {
  limit: string | null;
  remaining: string | null;
  reset: string | null;
  retryAfterMs: number | null;
}

function parseRateLimitHeaders(response: Response): RateLimitInfo {
  return {
    limit: response.headers.get("X-RateLimit-Limit"),
    remaining: response.headers.get("X-RateLimit-Remaining"),
    reset: response.headers.get("X-RateLimit-Reset"),
    retryAfterMs: parseRetryAfter(response),
  };
}

// ---------------------------------------------------------------------------
// Exponential Backoff
// ---------------------------------------------------------------------------

interface BackoffOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

async function fetchWithBackoff(
  url: string,
  init?: RequestInit,
  options: BackoffOptions = {},
): Promise<Response> {
  const {
    maxRetries = 5,
    baseDelayMs = 1000,
    maxDelayMs = 60_000,
  } = options;

  let lastResponse: Response | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, init);
      lastResponse = response;

      if (!RETRYABLE_STATUS_CODES.has(response.status)) {
        return response;
      }

      if (attempt === maxRetries) break;

      const retryAfterMs = parseRetryAfter(response);
      const backoff = Math.min(baseDelayMs * 2 ** attempt, maxDelayMs);
      const jitter = Math.random() * baseDelayMs;
      const delay = Math.max(backoff + jitter, retryAfterMs ?? 0);

      console.warn(
        `[backoff] Retry ${url}: attempt=${attempt + 1}/${maxRetries} status=${response.status} delay=${delay.toFixed(0)}ms`,
      );
      await setTimeout(delay);
    } catch (err) {
      if (attempt === maxRetries) throw err;

      const delay = Math.min(baseDelayMs * 2 ** attempt, maxDelayMs);
      console.warn(
        `[backoff] Connection error on ${url} (attempt ${attempt + 1}): ${err}`,
      );
      await setTimeout(delay);
    }
  }

  if (!lastResponse) {
    throw new Error(`All ${maxRetries} retries failed for ${url}`);
  }

  console.error(`[backoff] Max retries (${maxRetries}) exhausted for ${url}`);
  return lastResponse;
}

// ---------------------------------------------------------------------------
// Circuit Breaker
// ---------------------------------------------------------------------------

enum CircuitState {
  CLOSED = "closed",
  OPEN = "open",
  HALF_OPEN = "half_open",
}

class CircuitOpenError extends Error {
  retryAfterMs: number;
  constructor(retryAfterMs: number) {
    super(
      `Circuit OPEN — retry after ${(retryAfterMs / 1000).toFixed(1)}s`,
    );
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
    private readonly circuitName: string = "default",
  ) {}

  getState(): CircuitState {
    if (
      this.state === CircuitState.OPEN &&
      Date.now() >= this.recoveryTime
    ) {
      this.state = CircuitState.HALF_OPEN;
      console.info(`[circuit] '${this.circuitName}' → HALF_OPEN`);
    }
    return this.state;
  }

  recordSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      console.info(`[circuit] '${this.circuitName}' → CLOSED (recovered)`);
    }
    this.failureCount = 0;
    this.state = CircuitState.CLOSED;
  }

  recordFailure(): void {
    this.failureCount++;
    if (this.failureCount >= this.failureThreshold) {
      this.state = CircuitState.OPEN;
      this.recoveryTime = Date.now() + this.recoveryTimeoutMs;
      console.warn(
        `[circuit] '${this.circuitName}' → OPEN after ${this.failureCount} failures ` +
          `(recovery in ${this.recoveryTimeoutMs / 1000}s)`,
      );
    }
  }

  check(): void {
    const s = this.getState();
    if (s === CircuitState.OPEN) {
      const remaining = Math.max(0, this.recoveryTime - Date.now());
      throw new CircuitOpenError(remaining);
    }
  }

  reset(): void {
    this.failureCount = 0;
    this.state = CircuitState.CLOSED;
    console.info(`[circuit] '${this.circuitName}' manually reset → CLOSED`);
  }
}

// ---------------------------------------------------------------------------
// Retry Queue
// ---------------------------------------------------------------------------

interface RetryTask<T> {
  item: T;
  attempt: number;
}

interface QueueOptions {
  maxConcurrency?: number;
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

interface QueueStats {
  total: number;
  completed: number;
  failed: number;
  deadLetterCount: number;
}

class RetryQueue<T> {
  private queue: RetryTask<T>[] = [];
  private inFlight = 0;
  private completed = 0;
  private failed = 0;
  private total = 0;
  readonly deadLetter: T[] = [];

  private readonly maxConcurrency: number;
  private readonly maxRetries: number;
  private readonly baseDelayMs: number;
  private readonly maxDelayMs: number;

  constructor(
    private readonly workerFn: (item: T) => Promise<boolean>,
    options: QueueOptions = {},
  ) {
    this.maxConcurrency = options.maxConcurrency ?? 10;
    this.maxRetries = options.maxRetries ?? 5;
    this.baseDelayMs = options.baseDelayMs ?? 1000;
    this.maxDelayMs = options.maxDelayMs ?? 60_000;
  }

  submit(item: T): void {
    this.queue.push({ item, attempt: 0 });
    this.total++;
  }

  submitMany(items: T[]): void {
    for (const item of items) {
      this.submit(item);
    }
  }

  async run(): Promise<QueueStats> {
    const workers: Promise<void>[] = [];

    const processLoop = async (): Promise<void> => {
      while (this.queue.length > 0) {
        const task = this.queue.shift()!;
        this.inFlight++;

        let success = false;
        try {
          success = await this.workerFn(task.item);
        } catch (err) {
          console.error(`[queue] Worker error for ${task.item}:`, err);
        }
        this.inFlight--;

        if (success) {
          this.completed++;
          continue;
        }

        task.attempt++;
        if (task.attempt > this.maxRetries) {
          this.deadLetter.push(task.item);
          this.failed++;
          console.error(
            `[queue] Dead-lettered: ${task.item} after ${task.attempt} attempts`,
          );
          continue;
        }

        const delay = Math.min(
          this.baseDelayMs * 2 ** (task.attempt - 1),
          this.maxDelayMs,
        );
        const jitter = Math.random() * this.baseDelayMs;
        console.warn(
          `[queue] Re-queue ${task.item}: attempt=${task.attempt} delay=${(delay + jitter).toFixed(0)}ms`,
        );
        await setTimeout(delay + jitter);
        this.queue.push(task);
      }
    };

    for (let i = 0; i < this.maxConcurrency; i++) {
      workers.push(processLoop());
    }
    await Promise.all(workers);

    return {
      total: this.total,
      completed: this.completed,
      failed: this.failed,
      deadLetterCount: this.deadLetter.length,
    };
  }
}

// ---------------------------------------------------------------------------
// Integrated Client
// ---------------------------------------------------------------------------

interface ClientOptions {
  maxConcurrency?: number;
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  circuitFailureThreshold?: number;
  circuitRecoveryTimeoutMs?: number;
}

class ResilientApiClient {
  private circuit: CircuitBreaker;
  private inFlight = 0;
  private readonly maxConcurrency: number;
  private readonly backoffOptions: BackoffOptions;

  constructor(
    private readonly baseUrl: string,
    options: ClientOptions = {},
  ) {
    this.maxConcurrency = options.maxConcurrency ?? 10;
    this.backoffOptions = {
      maxRetries: options.maxRetries ?? 5,
      baseDelayMs: options.baseDelayMs ?? 1000,
      maxDelayMs: options.maxDelayMs ?? 60_000,
    };
    this.circuit = new CircuitBreaker(
      options.circuitFailureThreshold ?? 5,
      options.circuitRecoveryTimeoutMs ?? 30_000,
      baseUrl,
    );
  }

  async request(path: string, init?: RequestInit): Promise<Response> {
    this.circuit.check();

    // Concurrency control
    while (this.inFlight >= this.maxConcurrency) {
      await setTimeout(50);
    }
    this.inFlight++;

    try {
      const url = `${this.baseUrl}${path}`;
      const response = await fetchWithBackoff(url, init, this.backoffOptions);

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

  /** Get the current circuit breaker state */
  getCircuitState(): string {
    return this.circuit.getState();
  }

  /** Manually reset the circuit breaker */
  resetCircuit(): void {
    this.circuit.reset();
  }
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export {
  fetchWithBackoff,
  parseRetryAfter,
  parseRateLimitHeaders,
  CircuitBreaker,
  CircuitOpenError,
  CircuitState,
  RetryQueue,
  ResilientApiClient,
  RETRYABLE_STATUS_CODES,
};

export type {
  BackoffOptions,
  ClientOptions,
  QueueOptions,
  QueueStats,
  RateLimitInfo,
};
```

## Quick Start

```typescript
import { ResilientApiClient } from "./resilient-client";

const client = new ResilientApiClient("https://api.example.com", {
  maxConcurrency: 5,
  maxRetries: 3,
});

const response = await client.request("/data");
console.log(response.status, await response.json());
```

## Bulk Processing

```typescript
import { ResilientApiClient, RetryQueue } from "./resilient-client";

const client = new ResilientApiClient("https://api.example.com");

const queue = new RetryQueue<string>(
  async (itemId) => {
    const resp = await client.request(`/process/${itemId}`, { method: "POST" });
    return resp.ok;
  },
  { maxConcurrency: 5, maxRetries: 3 },
);

const items = Array.from({ length: 100 }, (_, i) => `item-${i}`);
queue.submitMany(items);

const stats = await queue.run();
console.log("Results:", stats);

if (queue.deadLetter.length > 0) {
  console.log("Failed items:", queue.deadLetter);
}
```

## CommonJS Usage (Node < 18)

```javascript
const { ResilientApiClient, RetryQueue } = require("./resilient-client");
// Usage is the same, just use require instead of import
```
