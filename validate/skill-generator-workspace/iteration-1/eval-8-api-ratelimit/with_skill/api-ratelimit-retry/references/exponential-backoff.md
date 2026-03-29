# Exponential Backoff — Deep Reference

## Algorithm

```
delay = min(base_delay * 2^attempt, max_delay) + jitter
```

Where `jitter` is a random value in `[0, delay * jitter_factor]`.

## Jitter Strategies

| Strategy | Formula | Use when |
|----------|---------|----------|
| **Full jitter** | `random(0, delay)` | Default choice; best spread |
| **Equal jitter** | `delay/2 + random(0, delay/2)` | Need guaranteed minimum wait |
| **Decorrelated** | `min(max_delay, random(base, prev_delay * 3))` | Long retry chains |

Full jitter is almost always the right choice. It provides the widest spread of retry times, minimizing collision probability.

## Respecting Retry-After

The `Retry-After` response header can be either:
- A number of seconds: `Retry-After: 120`
- An HTTP date: `Retry-After: Fri, 31 Dec 2025 23:59:59 GMT`

Always check for this header before computing your own delay. The server knows its own rate-limit windows.

### Python — Full Implementation

```python
import asyncio
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx


def parse_retry_after(header_value: str) -> Optional[float]:
    """Parse Retry-After header into seconds to wait."""
    try:
        return float(header_value)
    except ValueError:
        pass
    try:
        retry_date = parsedate_to_datetime(header_value)
        delta = (retry_date - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delta)
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
    jitter_factor: float = 0.5,
    retryable_statuses: tuple[int, ...] = (429, 502, 503, 504),
    **kwargs,
) -> httpx.Response:
    """
    Send an HTTP request with exponential backoff on retryable status codes.

    Args:
        client: httpx async client instance.
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        jitter_factor: Random jitter as a fraction of delay (0.0 to 1.0).
        retryable_statuses: HTTP status codes that trigger a retry.
        **kwargs: Additional arguments passed to client.request().

    Returns:
        The HTTP response.

    Raises:
        httpx.HTTPStatusError: If retries are exhausted and last response is an error.
    """
    last_response: Optional[httpx.Response] = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
            last_response = response

            if response.status_code not in retryable_statuses:
                return response

            if attempt == max_retries:
                response.raise_for_status()

            # Compute delay
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                delay = parse_retry_after(retry_after) or base_delay
            else:
                delay = min(base_delay * (2 ** attempt), max_delay)

            # Add jitter
            delay += random.uniform(0, delay * jitter_factor)

            print(
                f"[backoff] {method} {url} -> {response.status_code} "
                f"(attempt {attempt + 1}/{max_retries}, wait {delay:.1f}s)"
            )
            await asyncio.sleep(delay)

        except httpx.ConnectError:
            # Network-level failure — also retryable
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, delay * jitter_factor)
            await asyncio.sleep(delay)

    # Should not reach here, but satisfy type checker
    assert last_response is not None
    last_response.raise_for_status()
    return last_response  # unreachable
```

### Node.js — Full Implementation

```typescript
/**
 * Parse Retry-After header value into milliseconds.
 */
function parseRetryAfter(value: string): number | null {
  const seconds = Number(value);
  if (!isNaN(seconds)) return seconds * 1000;

  const date = Date.parse(value);
  if (!isNaN(date)) return Math.max(0, date - Date.now());

  return null;
}

interface BackoffOptions {
  maxRetries?: number;
  baseDelay?: number;       // ms
  maxDelay?: number;        // ms
  jitterFactor?: number;    // 0.0 to 1.0
  retryableStatuses?: number[];
}

const DEFAULT_RETRYABLE = [429, 502, 503, 504];

/**
 * Fetch with exponential backoff on retryable HTTP status codes.
 *
 * @param url - Request URL
 * @param init - Standard fetch RequestInit options
 * @param options - Backoff configuration
 * @returns The Response object
 * @throws Error if retries are exhausted
 */
async function fetchWithBackoff(
  url: string,
  init: RequestInit = {},
  options: BackoffOptions = {}
): Promise<Response> {
  const {
    maxRetries = 5,
    baseDelay = 1000,
    maxDelay = 60_000,
    jitterFactor = 0.5,
    retryableStatuses = DEFAULT_RETRYABLE,
  } = options;

  let lastResponse: Response | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, init);
      lastResponse = response;

      if (!retryableStatuses.includes(response.status)) {
        return response;
      }

      if (attempt === maxRetries) {
        throw new Error(
          `Request failed with status ${response.status} after ${maxRetries} retries`
        );
      }

      // Compute delay
      const retryAfter = response.headers.get("Retry-After");
      let delay: number;
      if (retryAfter) {
        delay = parseRetryAfter(retryAfter) ?? baseDelay;
      } else {
        delay = Math.min(baseDelay * 2 ** attempt, maxDelay);
      }

      // Add jitter
      delay += Math.random() * delay * jitterFactor;

      console.log(
        `[backoff] ${init.method ?? "GET"} ${url} -> ${response.status} ` +
        `(attempt ${attempt + 1}/${maxRetries}, wait ${(delay / 1000).toFixed(1)}s)`
      );

      await new Promise((r) => setTimeout(r, delay));

    } catch (err) {
      if (err instanceof TypeError) {
        // Network error from fetch — retryable
        if (attempt === maxRetries) throw err;
        const delay = Math.min(baseDelay * 2 ** attempt, maxDelay)
          + Math.random() * baseDelay;
        await new Promise((r) => setTimeout(r, delay));
      } else {
        throw err;
      }
    }
  }

  throw new Error("Unreachable");
}

export { fetchWithBackoff, parseRetryAfter, type BackoffOptions };
```

## Testing Backoff Logic

To test without hitting real APIs, inject a fake clock and a mock transport:

### Python

```python
import pytest
import httpx
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_backoff_retries_on_429():
    responses = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json={"ok": True}),
    ]
    transport = httpx.MockTransport(
        lambda req: responses.pop(0)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with patch("asyncio.sleep", new_callable=AsyncMock):
            resp = await request_with_backoff(client, "GET", "https://api.example.com/data")
            assert resp.status_code == 200
```

### Node.js

```typescript
import { describe, it, expect, vi } from "vitest";

describe("fetchWithBackoff", () => {
  it("retries on 429 then succeeds", async () => {
    let callCount = 0;
    global.fetch = vi.fn(async () => {
      callCount++;
      if (callCount < 3) {
        return new Response(null, {
          status: 429,
          headers: { "Retry-After": "0" },
        });
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    const resp = await fetchWithBackoff("https://api.example.com/data");
    expect(resp.status).toBe(200);
    expect(callCount).toBe(3);
  });
});
```
