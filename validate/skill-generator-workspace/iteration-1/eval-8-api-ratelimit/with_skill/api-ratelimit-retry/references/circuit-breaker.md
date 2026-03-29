# Circuit Breaker — Deep Reference

## State Machine

```
         success                    failure >= threshold
CLOSED ───────── CLOSED      CLOSED ────────────────────── OPEN
                                                             │
                              recovery_timeout elapsed       │
OPEN ────────────────────────────────────────── HALF_OPEN    │
                                                  │          │
                              probe succeeds      │          │
HALF_OPEN ──────────────────── CLOSED              │         │
                              probe fails          │         │
HALF_OPEN ──────────────────── OPEN ◄──────────────┘         │
                                                             │
```

## When to Use

- **Use** when upstream failures are correlated (service down, not just occasional 429)
- **Use** when you want to fail fast instead of waiting for timeouts
- **Skip** for stateless/idempotent health checks — just retry directly

## Threshold Tuning

| Parameter | Conservative | Balanced | Aggressive |
|-----------|-------------|----------|------------|
| `failure_threshold` | 10 | 5 | 2 |
| `recovery_timeout` | 60s | 30s | 10s |
| `half_open_max_calls` | 3 | 1 | 1 |

- **Conservative**: Use for non-critical, high-volume APIs. Tolerates noise.
- **Balanced**: Default. Works for most REST APIs.
- **Aggressive**: Use for critical-path dependencies where fast failure matters.

## Python — Production Implementation

```python
import asyncio
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open and blocking calls."""
    def __init__(self, message: str, remaining_seconds: float):
        super().__init__(message)
        self.remaining_seconds = remaining_seconds


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1
    # Which exception types count as failures (empty = all exceptions)
    failure_exceptions: tuple[type[Exception], ...] = ()


class CircuitBreaker:
    """
    Thread-safe circuit breaker for async callables.

    Usage:
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        result = await cb.call(some_async_function, arg1, arg2)
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def call(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        async with self._lock:
            self._check_state()

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            if self._is_failure(exc):
                async with self._lock:
                    self._on_failure()
            raise
        else:
            async with self._lock:
                self._on_success()
            return result

    def _check_state(self):
        """Evaluate whether the call should proceed. Raises CircuitOpenError if not."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            remaining = self._config.recovery_timeout - elapsed
            if remaining <= 0:
                logger.info("Circuit transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            else:
                raise CircuitOpenError(
                    f"Circuit OPEN. Retry in {remaining:.1f}s",
                    remaining_seconds=remaining,
                )

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._config.half_open_max_calls:
                raise CircuitOpenError(
                    "Circuit HALF_OPEN: probe limit reached",
                    remaining_seconds=self._config.recovery_timeout,
                )
            self._half_open_calls += 1

    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Probe succeeded. Circuit transitioning to CLOSED")
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._config.failure_threshold:
            logger.warning(
                f"Failure threshold reached ({self._failure_count}). Circuit -> OPEN"
            )
            self._state = CircuitState.OPEN

    def _is_failure(self, exc: Exception) -> bool:
        if not self._config.failure_exceptions:
            return True
        return isinstance(exc, self._config.failure_exceptions)

    def reset(self):
        """Manually reset the circuit breaker to CLOSED."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
```

## Node.js — Production Implementation

```typescript
type CircuitState = "closed" | "open" | "half_open";

interface CircuitBreakerConfig {
  failureThreshold?: number;
  recoveryTimeout?: number;   // ms
  halfOpenMaxCalls?: number;
  /** Only count these error types as failures. Empty = all errors. */
  isFailure?: (error: unknown) => boolean;
}

class CircuitOpenError extends Error {
  constructor(
    message: string,
    public readonly remainingMs: number
  ) {
    super(message);
    this.name = "CircuitOpenError";
  }
}

class CircuitBreaker {
  private state: CircuitState = "closed";
  private failureCount = 0;
  private lastFailureTime = 0;
  private halfOpenCalls = 0;

  private readonly failureThreshold: number;
  private readonly recoveryTimeout: number;
  private readonly halfOpenMaxCalls: number;
  private readonly isFailure: (error: unknown) => boolean;

  constructor(config: CircuitBreakerConfig = {}) {
    this.failureThreshold = config.failureThreshold ?? 5;
    this.recoveryTimeout = config.recoveryTimeout ?? 30_000;
    this.halfOpenMaxCalls = config.halfOpenMaxCalls ?? 1;
    this.isFailure = config.isFailure ?? (() => true);
  }

  getState(): CircuitState {
    return this.state;
  }

  async call<T>(fn: () => Promise<T>): Promise<T> {
    this.checkState();

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (err) {
      if (this.isFailure(err)) {
        this.onFailure();
      }
      throw err;
    }
  }

  private checkState(): void {
    if (this.state === "open") {
      const elapsed = Date.now() - this.lastFailureTime;
      const remaining = this.recoveryTimeout - elapsed;
      if (remaining <= 0) {
        this.state = "half_open";
        this.halfOpenCalls = 0;
      } else {
        throw new CircuitOpenError(
          `Circuit OPEN. Retry in ${(remaining / 1000).toFixed(1)}s`,
          remaining
        );
      }
    }

    if (this.state === "half_open") {
      if (this.halfOpenCalls >= this.halfOpenMaxCalls) {
        throw new CircuitOpenError(
          "Circuit HALF_OPEN: probe limit reached",
          this.recoveryTimeout
        );
      }
      this.halfOpenCalls++;
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.state = "closed";
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    if (this.failureCount >= this.failureThreshold) {
      this.state = "open";
    }
  }

  /** Manually reset to closed state. */
  reset(): void {
    this.state = "closed";
    this.failureCount = 0;
    this.halfOpenCalls = 0;
  }
}

export { CircuitBreaker, CircuitOpenError, type CircuitBreakerConfig };
```

## Observability

Always instrument your circuit breaker with metrics:

```python
# Python — emit metrics on state transitions
from dataclasses import dataclass

@dataclass
class CircuitBreakerMetrics:
    total_calls: int = 0
    total_failures: int = 0
    total_rejections: int = 0    # blocked by open circuit
    state_transitions: int = 0

    def record_call(self): self.total_calls += 1
    def record_failure(self): self.total_failures += 1
    def record_rejection(self): self.total_rejections += 1
    def record_transition(self): self.state_transitions += 1
```

```typescript
// Node.js — emit events for monitoring
import { EventEmitter } from "events";

class ObservableCircuitBreaker extends CircuitBreaker {
  readonly events = new EventEmitter();

  // Override onSuccess/onFailure to emit events
  // events: "stateChange", "failure", "rejection", "success"
}
```
