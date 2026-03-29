# Skill Eval Writer — 为 log-analyzer 编写测试用例

## 信息完整性评估

> **注意**：该 skill 没有正式的 SKILL.md，以下分析完全基于用户的口头描述。这意味着部分行为是推测性的，可能与实际期望存在偏差。

### 信息不完整的地方

以下关键信息**缺失或未明确**，建议用户在正式编写 SKILL.md 时补充：

1. **输出格式未定义** — 摘要报告是 Markdown 表格？纯文本列表？JSON？没有明确模板，grade.py 只能做宽松的关键词匹配。
2. **时间段判定规则未明确** — "最近1小时、1-6小时、6小时以上"是基于日志本身的时间戳还是相对于当前时间？如果日志没有时间戳怎么处理？
3. **"异常类型"的定义缺失** — 什么算"最频繁的异常类型"？是按 Exception 类名分组？按 ERROR 后面的关键词分组？还是按自定义规则？
4. **"建议关注的日志行"的选取标准未定义** — 是选最近的？最频繁的？还是最严重的？
5. **边界行为未描述** — 如果日志全是 INFO 没有 ERROR/WARN 怎么办？如果日志格式不标准怎么办？如果日志非常大怎么办？
6. **触发词未定义** — 用户说什么会触发这个 skill？"分析日志"？"查看异常"？"log analysis"？
7. **输入来源未明确** — 是粘贴日志文本？还是提供文件路径？还是两者都支持？

**建议**：在正式编写 SKILL.md 前，至少明确输出格式模板和时间段判定规则，否则 eval 的区分度会受限。

---

## 第一步：阅读目标 skill 分析

### 目标 skill 核心信息（基于口头描述推断）

| 属性 | 分析结果 |
|------|---------|
| **输入格式** | 多行日志文本（推测为标准格式：`时间戳 级别 消息`） |
| **输出格式** | 摘要报告（格式未定义，推测为结构化文本/Markdown） |
| **必须出现的输出元素** | 按时间段分组的统计、每个时间段的异常数量、最频繁的异常类型、建议关注的日志行 |
| **分支逻辑** | 根据时间段分组（最近1小时 / 1-6小时 / 6小时以上）；根据级别过滤（ERROR / WARN） |
| **边界** | 全是 INFO 无异常；日志格式不标准；空输入（未明确，需推测） |

### 核心规则清单（推断）

1. 识别 ERROR 级别的日志行
2. 识别 WARN/WARNING 级别的日志行
3. 按时间段分组：最近1小时、1-6小时、6小时以上
4. 每个时间段统计异常数量
5. 识别最频繁的异常类型
6. 输出建议关注的日志行
7. 输出整体摘要报告

---

## 第二步：设计 5 个 eval 用例

| 槽位 | 名称 | 设计意图 |
|------|------|---------|
| eval-1 | **基本路径：混合日志分析** | 包含 ERROR、WARN、INFO 的多行日志（跨越多个时间段），验证完整的分析和分组统计流程 |
| eval-2 | **领域变体：高频重复异常** | 大量重复的同类 ERROR（如 ConnectionTimeout 出现 11 次），验证频率统计和"最频繁异常类型"的识别 |
| eval-3 | **领域跨越：多服务混合日志** | 来自不同服务（auth-service、payment-service、api-gateway）的混合日志，验证能否按服务维度交叉分析 |
| eval-4 | **模糊/自动检测：用户不说"分析日志"** | 用户说"帮我看看这些报错是怎么回事"，直接粘贴日志，不使用"日志分析"触发词 |
| eval-5 | **边界/降级：全是 INFO 无异常** | 日志全部是 INFO 级别，没有 ERROR 也没有 WARN，验证 skill 是否正确报告"无异常" |

---

## 第三步 & 第四步：evals.json

```json
{
  "skill_name": "log-analyzer",
  "version": "1.0",
  "description": "验证 log-analyzer skill 能否正确识别日志中的 ERROR/WARN、按时间段分组统计异常、识别高频异常类型并给出建议关注的日志行",
  "scoring": {
    "total_points": 100,
    "dimensions": {
      "error_detection": {
        "weight": 25,
        "description": "能否正确识别 ERROR 和 WARN 级别的日志条目"
      },
      "time_grouping": {
        "weight": 25,
        "description": "是否按时间段（最近1小时、1-6小时、6小时以上）正确分组"
      },
      "frequency_analysis": {
        "weight": 20,
        "description": "是否统计异常数量并识别最频繁的异常类型"
      },
      "report_structure": {
        "weight": 15,
        "description": "输出报告是否结构清晰、包含必要的摘要元素"
      },
      "boundary_handling": {
        "weight": 15,
        "description": "对无异常日志、模糊输入等边界场景的处理质量"
      }
    }
  },
  "evals": [
    {
      "id": 1,
      "name": "basic-mixed-log-analysis",
      "prompt": "帮我分析一下这段服务器日志：\n\n```\n2024-01-15 14:30:00 INFO  [main] Application started successfully\n2024-01-15 14:30:05 INFO  [http] Listening on port 8080\n2024-01-15 14:35:12 WARN  [db] Connection pool utilization at 85%\n2024-01-15 14:42:33 ERROR [auth] Failed to validate token: TokenExpiredException\n2024-01-15 14:43:01 ERROR [auth] Failed to validate token: TokenExpiredException\n2024-01-15 14:45:00 INFO  [http] GET /api/users 200 45ms\n2024-01-15 14:50:22 WARN  [db] Slow query detected: SELECT * FROM orders WHERE status='pending' (3200ms)\n2024-01-15 14:55:10 ERROR [payment] Payment gateway timeout: ConnectionTimeoutException\n2024-01-15 14:58:00 INFO  [http] GET /api/products 200 12ms\n2024-01-15 11:00:00 ERROR [scheduler] Cron job 'cleanup' failed: DiskFullException\n2024-01-15 11:15:30 WARN  [scheduler] Retry attempt 1 for job 'cleanup'\n2024-01-15 11:16:00 WARN  [scheduler] Retry attempt 2 for job 'cleanup'\n2024-01-15 11:16:30 ERROR [scheduler] Cron job 'cleanup' failed after 3 retries: DiskFullException\n2024-01-15 06:00:00 ERROR [backup] Backup to S3 failed: AccessDeniedException\n2024-01-15 06:00:05 WARN  [backup] Falling back to local backup\n```\n\n请输出异常摘要报告。",
      "expected_output": "按时间段分组统计：最近1小时（约14:00-15:00）有 3 个 ERROR 和 2 个 WARN；1-6小时前（约11:00-14:00）有 2 个 ERROR 和 2 个 WARN；6小时以上（约06:00）有 1 个 ERROR 和 1 个 WARN。最频繁的异常类型是 TokenExpiredException（2次）和 DiskFullException（2次）。建议关注的日志行包括 payment gateway timeout 和 disk full 异常。",
      "assertions": [
        {
          "id": "A1-01",
          "text": "识别出日志中的 ERROR 级别条目（至少提到 3 种不同的 ERROR）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-02",
          "text": "识别出日志中的 WARN 级别条目",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-03",
          "text": "按时间段分组输出（包含最近1小时、1-6小时、6小时以上的分类）",
          "type": "structural",
          "points": 10
        },
        {
          "id": "A1-04",
          "text": "每个时间段有异常数量统计",
          "type": "structural",
          "points": 8
        },
        {
          "id": "A1-05",
          "text": "识别出最频繁的异常类型（TokenExpiredException 或 DiskFullException）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-06",
          "text": "输出包含建议关注的日志行",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A1-07",
          "text": "报告包含整体摘要（如总 ERROR 数、总 WARN 数）",
          "type": "structural",
          "points": 5
        }
      ]
    },
    {
      "id": 2,
      "name": "high-frequency-repeated-errors",
      "prompt": "分析这段日志的异常情况：\n\n```\n2024-01-15 14:00:01 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:03 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:05 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:07 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:09 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:11 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:13 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:15 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:17 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:00:19 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:01:00 WARN  [api] Circuit breaker opened for 'user-service'\n2024-01-15 14:05:00 INFO  [api] Circuit breaker half-open, testing 'user-service'\n2024-01-15 14:05:01 ERROR [api] ConnectionTimeout: upstream service 'user-service' at 10.0.1.5:8080\n2024-01-15 14:05:02 WARN  [api] Circuit breaker re-opened for 'user-service'\n2024-01-15 14:10:00 WARN  [monitor] High error rate detected: 92% failure in last 10 minutes\n2024-01-15 14:20:00 ERROR [db] Deadlock detected in table 'sessions'\n2024-01-15 14:20:01 WARN  [db] Auto-retry after deadlock resolution\n```\n\n告诉我哪些异常最需要关注。",
      "expected_output": "摘要应重点突出 ConnectionTimeout 是最频繁的异常（11次），远超其他异常类型。应识别出 circuit breaker 模式（开启→半开→重新开启）暗示 user-service 持续不可用。deadlock 是独立事件。建议优先排查 user-service 连接问题。",
      "assertions": [
        {
          "id": "A2-01",
          "text": "识别 ConnectionTimeout 为最频繁的异常类型",
          "type": "content",
          "points": 10
        },
        {
          "id": "A2-02",
          "text": "给出 ConnectionTimeout 的出现次数或频率（约 11 次）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A2-03",
          "text": "识别出 deadlock 异常",
          "type": "content",
          "points": 5
        },
        {
          "id": "A2-04",
          "text": "包含时间段分组或时间线分析",
          "type": "structural",
          "points": 7
        },
        {
          "id": "A2-05",
          "text": "给出建议关注的重点（如优先排查 user-service）",
          "type": "content",
          "points": 7
        },
        {
          "id": "A2-06",
          "text": "区分了不同严重程度的异常（ConnectionTimeout 比 deadlock 更紧急）",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 3,
      "name": "multi-service-mixed-logs",
      "prompt": "这是从 3 个服务收集来的日志，帮我整理一下异常情况：\n\n```\n2024-01-15 14:30:00 ERROR [auth-service] OAuth token refresh failed: InvalidGrantException\n2024-01-15 14:30:05 WARN  [auth-service] Falling back to cached token\n2024-01-15 14:31:00 ERROR [payment-service] Stripe API error: CardDeclinedException for order #12345\n2024-01-15 14:31:30 WARN  [payment-service] Retry payment for order #12345\n2024-01-15 14:32:00 ERROR [payment-service] Stripe API error: CardDeclinedException for order #12345\n2024-01-15 14:33:00 WARN  [payment-service] Order #12345 marked as payment_failed\n2024-01-15 14:35:00 ERROR [api-gateway] Rate limit exceeded for client IP 192.168.1.100\n2024-01-15 14:35:01 ERROR [api-gateway] Rate limit exceeded for client IP 192.168.1.100\n2024-01-15 14:35:02 ERROR [api-gateway] Rate limit exceeded for client IP 192.168.1.100\n2024-01-15 14:40:00 WARN  [api-gateway] Suspicious traffic pattern from 192.168.1.100\n2024-01-15 10:00:00 ERROR [auth-service] LDAP connection refused\n2024-01-15 10:05:00 WARN  [auth-service] LDAP reconnection attempt 1\n2024-01-15 10:10:00 ERROR [auth-service] LDAP connection refused\n2024-01-15 05:00:00 WARN  [payment-service] Daily settlement batch delayed by 15 minutes\n```\n\n输出异常分析报告。",
      "expected_output": "按服务和时间段交叉分析：auth-service 有 OAuth 和 LDAP 两类异常，payment-service 有支付失败和批处理延迟，api-gateway 有限流和可疑流量。按时间段分组输出，识别 rate limit 是最频繁的 ERROR 类型。",
      "assertions": [
        {
          "id": "A3-01",
          "text": "识别出至少 3 个不同服务（auth-service、payment-service、api-gateway）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A3-02",
          "text": "按时间段分组输出",
          "type": "structural",
          "points": 7
        },
        {
          "id": "A3-03",
          "text": "识别 rate limit 为高频 ERROR",
          "type": "content",
          "points": 7
        },
        {
          "id": "A3-04",
          "text": "提到 LDAP 连接问题",
          "type": "content",
          "points": 5
        },
        {
          "id": "A3-05",
          "text": "提到支付失败（CardDeclinedException 或 order #12345）",
          "type": "content",
          "points": 5
        },
        {
          "id": "A3-06",
          "text": "包含每个时间段的异常数量统计",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A3-07",
          "text": "包含建议关注的日志行或改进建议",
          "type": "structural",
          "points": 5
        }
      ]
    },
    {
      "id": 4,
      "name": "fuzzy-input-no-trigger-words",
      "prompt": "帮我看看这些报错是怎么回事，最近系统老是出问题：\n\n```\n2024-01-15 14:50:00 ERROR [web] NullPointerException at UserController.java:142\n2024-01-15 14:50:30 ERROR [web] NullPointerException at UserController.java:142\n2024-01-15 14:51:00 WARN  [web] Request timeout for /api/user/profile (>5000ms)\n2024-01-15 14:52:00 ERROR [web] NullPointerException at UserController.java:142\n2024-01-15 14:55:00 WARN  [cache] Redis connection unstable, latency > 200ms\n2024-01-15 14:56:00 ERROR [cache] Redis cluster node down: 10.0.2.3:6379\n2024-01-15 13:00:00 WARN  [web] High memory usage: 87% of heap\n2024-01-15 13:30:00 WARN  [web] GC pause > 500ms\n```\n\n这些问题严重吗？要怎么处理？",
      "expected_output": "即使用户没有说'分析日志'或'异常摘要'，skill 应识别出这是日志分析场景。输出按时间段分组的异常摘要：最近1小时有 NullPointerException（3次，最频繁）、Redis 问题、timeout；1-6小时前有内存和 GC 警告。建议优先修复 UserController.java:142 的空指针。",
      "assertions": [
        {
          "id": "A4-01",
          "text": "识别出这是日志分析场景并输出结构化分析（即使用户未使用触发关键词）",
          "type": "content",
          "points": 7
        },
        {
          "id": "A4-02",
          "text": "识别 NullPointerException 为最频繁的异常",
          "type": "content",
          "points": 8
        },
        {
          "id": "A4-03",
          "text": "包含时间段分组",
          "type": "structural",
          "points": 7
        },
        {
          "id": "A4-04",
          "text": "提到 Redis 相关问题",
          "type": "content",
          "points": 5
        },
        {
          "id": "A4-05",
          "text": "包含异常数量统计",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A4-06",
          "text": "给出处理建议或优先级建议",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 5,
      "name": "boundary-no-errors-all-info",
      "prompt": "分析这段日志有没有异常：\n\n```\n2024-01-15 14:00:00 INFO  [main] Application started on port 8080\n2024-01-15 14:00:01 INFO  [db] Database connection established\n2024-01-15 14:00:02 INFO  [cache] Redis connection established\n2024-01-15 14:01:00 INFO  [http] GET /api/health 200 2ms\n2024-01-15 14:05:00 INFO  [http] GET /api/users 200 35ms\n2024-01-15 14:10:00 INFO  [http] POST /api/orders 201 120ms\n2024-01-15 14:15:00 INFO  [scheduler] Cron job 'cleanup' completed successfully\n2024-01-15 14:20:00 INFO  [http] GET /api/products 200 18ms\n```\n\n请输出异常摘要。",
      "expected_output": "应明确告知用户日志中没有 ERROR 或 WARN 级别的条目，系统运行正常。不应凭空编造异常。可以附带一些正面指标（如所有请求响应时间正常）。",
      "assertions": [
        {
          "id": "A5-01",
          "text": "明确指出日志中没有 ERROR 或 WARN 级别条目",
          "type": "content",
          "points": 12
        },
        {
          "id": "A5-02",
          "text": "没有凭空编造不存在的异常",
          "type": "content",
          "points": 10
        },
        {
          "id": "A5-03",
          "text": "告知系统运行正常或无异常需要关注",
          "type": "content",
          "points": 8
        },
        {
          "id": "A5-04",
          "text": "仍然保持报告结构（有摘要或结论段落）",
          "type": "structural",
          "points": 5
        }
      ]
    }
  ]
}
```

---

## 第五步：grade.py

```python
#!/usr/bin/env python3
from __future__ import annotations

"""
log-analyzer skill 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出）。

也可以传入单个 eval 目录:
    python grade.py output_dir/eval-1

脚本自动检测输出，执行可程序化验证的断言。
最终输出 grading.json 到 output_dir/ 下。

注意：本 skill 没有正式的 SKILL.md，eval 基于口头描述设计，
部分断言可能需要在 SKILL.md 完善后调整。
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────
# 加载 evals.json
# ─────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
EVALS_PATH = SCRIPT_DIR / "evals.json"


def load_evals() -> dict:
    with open(EVALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ═════════════════════════════════════════════
# 文件收集工具 — 文本输出型
# ═════════════════════════════════════════════


def collect_output(eval_dir: Path) -> str:
    """收集 eval 目录下的所有文本内容，拼接为一个字符串。"""
    texts = []
    for fpath in sorted(eval_dir.rglob("*")):
        if fpath.is_file():
            try:
                texts.append(fpath.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, PermissionError):
                pass
    return "\n".join(texts)


# ═════════════════════════════════════════════
# 通用检查函数
# ═════════════════════════════════════════════


def check_keywords(
    content: str, keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    """检查内容是否包含足够数量的关键词（不区分大小写）。"""
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"命中 {len(found)}/{len(keywords)} 个关键词: {found}"
    return passed, evidence


def check_proximity(
    content: str, word_a: str, word_b: str, max_distance: int = 50
) -> tuple[bool, str]:
    """检查两个关键词是否在指定字符距离内共现。"""
    pattern = rf"({re.escape(word_a)}).{{0,{max_distance}}}({re.escape(word_b)})"
    m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if m:
        return True, f"找到近邻匹配: '{m.group()[:80]}'"
    pattern = rf"({re.escape(word_b)}).{{0,{max_distance}}}({re.escape(word_a)})"
    m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if m:
        return True, f"找到近邻匹配（反向）: '{m.group()[:80]}'"
    return False, f"'{word_a}' 和 '{word_b}' 未在 {max_distance} 字符内共现"


# ── 日志分析 skill 专用检查函数 ──


def check_time_period_grouping(content: str) -> tuple[bool, str]:
    """检查是否按时间段分组输出（最近1小时、1-6小时、6小时以上）。"""
    time_patterns = [
        r"(最近|近)\s*1\s*小时",
        r"1\s*[-~到至]\s*6\s*小时",
        r"6\s*小时\s*(以[上前]|之[前外])",
        r"(last|recent|past)\s*(1|one)\s*hour",
        r"1\s*[-~to]\s*6\s*hours?",
        r"(more than|over|beyond|older than)\s*6\s*hours?",
        r"1h",
        r"6h",
        r"<\s*1\s*小时",
        r">\s*6\s*小时",
    ]
    found = []
    for pat in time_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.append(pat)
    passed = len(found) >= 2  # 至少匹配 2 个时间段表述
    evidence = f"时间段分组: 匹配了 {len(found)} 个模式" if found else "未找到时间段分组"
    return passed, evidence


def check_anomaly_count(content: str) -> tuple[bool, str]:
    """检查是否有异常数量统计（如"3 个 ERROR"或"ERROR: 5 次"）。"""
    count_patterns = [
        r"\d+\s*(个|条|次)\s*(ERROR|WARN|异常|错误|警告)",
        r"(ERROR|WARN|异常|错误|警告)\s*[：:]\s*\d+",
        r"(ERROR|WARN)\s*\*{0,2}\d+\*{0,2}",
        r"\*{0,2}\d+\*{0,2}\s*(errors?|warnings?)",
        r"(共|总计|合计)\s*\d+\s*(个|条|次)",
        r"\d+\s*(times?|occurrences?|instances?)",
        r"(count|total)\s*[：:]\s*\d+",
    ]
    found = []
    for pat in count_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend([str(m) for m in matches[:2]])
    passed = len(found) > 0
    evidence = f"异常统计: {found[:5]}" if found else "未找到异常数量统计"
    return passed, evidence


def check_frequency_analysis(content: str) -> tuple[bool, str]:
    """检查是否识别了最频繁的异常类型。"""
    freq_keywords = [
        "最频繁", "频率最高", "最多", "出现次数最多",
        "most frequent", "most common", "top", "highest frequency",
        "频繁", "高频", "重复", "集中",
    ]
    found = [kw for kw in freq_keywords if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"频率分析关键词: {found}" if found else "未找到频率分析"
    return passed, evidence


def check_log_level_detection(content: str, level: str) -> tuple[bool, str]:
    """检查是否识别了特定级别的日志（ERROR 或 WARN）。"""
    # 检查 level 本身是否在上下文中被讨论（而非仅在原始日志引用中出现）
    analysis_patterns = [
        rf"{level}\s*(级别|level|类型|日志)",
        rf"(识别|发现|检测|存在)\s*.*{level}",
        rf"{level}\s*(数量|次|个|条)",
        rf"\d+\s*(个|条|次)\s*{level}",
    ]
    found = []
    for pat in analysis_patterns:
        if re.search(pat, content, re.IGNORECASE):
            found.append(pat)
    # 宽松匹配：至少在非日志引用区域提到了这个级别
    if not found:
        # 检查 level 出现次数（原始日志中也会有，所以要求出现在分析段落中）
        level_mentions = len(re.findall(rf"\b{level}\b", content, re.IGNORECASE))
        if level_mentions >= 3:  # 原始日志 + 分析中至少各提到一次
            found.append(f"{level} mentioned {level_mentions} times")
    passed = len(found) > 0
    evidence = f"{level} 分析: {found}" if found else f"未在分析中提到 {level}"
    return passed, evidence


def check_exception_type_mentioned(content: str, exception_type: str) -> tuple[bool, str]:
    """检查是否提到了特定的异常类型名。"""
    found = exception_type.lower() in content.lower()
    # 也检查简写形式
    if not found:
        # 如 ConnectionTimeout → connection timeout
        simplified = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', exception_type).lower()
        found = simplified in content.lower()
    evidence = f"{'找到' if found else '未找到'} 异常类型 '{exception_type}'"
    return found, evidence


def check_suggestion_present(content: str) -> tuple[bool, str]:
    """检查是否包含建议关注的日志行或处理建议。"""
    suggestion_kw = [
        "建议", "关注", "建议关注", "优先", "需要注意",
        "recommend", "attention", "priority", "suggest",
        "排查", "检查", "处理", "修复", "解决",
    ]
    found = [kw for kw in suggestion_kw if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"建议关键词: {found}" if found else "未找到建议或关注项"
    return passed, evidence


def check_service_mentioned(content: str, service_name: str) -> tuple[bool, str]:
    """检查是否提到了特定服务名。"""
    found = service_name.lower() in content.lower()
    evidence = f"{'找到' if found else '未找到'} 服务 '{service_name}'"
    return found, evidence


def check_no_fabricated_errors(content: str) -> tuple[bool, str]:
    """检查是否没有编造不存在的 ERROR/WARN（用于全 INFO 场景）。"""
    # 如果明确说了无异常/无 ERROR，通过
    no_error_kw = [
        "无异常", "没有异常", "无 ERROR", "没有 ERROR",
        "无 WARN", "没有 WARN", "未发现异常", "未检测到",
        "no error", "no warning", "no anomal", "no exception",
        "正常", "healthy", "一切正常", "运行正常",
    ]
    has_no_error_statement = any(kw.lower() in content.lower() for kw in no_error_kw)
    if has_no_error_statement:
        return True, "明确指出无异常，未编造错误"

    # 如果出现了"发现 ERROR"或"存在异常"等表述，则可能编造了
    fabrication_kw = [
        "发现.*ERROR", "存在.*异常", "检测到.*错误",
        "identified.*error", "found.*error", "detected.*warning",
    ]
    has_fabrication = any(
        re.search(pat, content, re.IGNORECASE | re.DOTALL)
        for pat in fabrication_kw
    )
    if has_fabrication:
        return False, "可能编造了不存在的异常"

    return True, "未出现明确的异常编造"


def check_all_normal_confirmation(content: str) -> tuple[bool, str]:
    """检查是否确认系统运行正常（用于无异常场景）。"""
    normal_kw = [
        "正常", "健康", "无异常", "没有异常",
        "没有问题", "一切正常", "运行良好",
        "normal", "healthy", "no issue", "no problem",
        "无需关注", "系统正常",
    ]
    found = [kw for kw in normal_kw if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"正常确认: {found}" if found else "未确认系统正常"
    return passed, evidence


def check_report_structure(content: str) -> tuple[bool, str]:
    """检查输出是否有报告结构（标题、摘要、分组等）。"""
    structure_indicators = [
        r"##?\s*",              # Markdown 标题
        r"(摘要|总结|概览|summary|overview)",
        r"(时间段|时段|time period)",
        r"(统计|统计表|statistics)",
        r"\|.*\|.*\|",          # Markdown 表格行
        r"[-*]\s+",             # 列表项
        r"(结论|conclusion|建议|recommendation)",
    ]
    found = []
    for pat in structure_indicators:
        if re.search(pat, content, re.IGNORECASE):
            found.append(pat)
    passed = len(found) >= 2
    evidence = f"报告结构指标: 匹配 {len(found)} 个" if found else "未发现报告结构"
    return passed, evidence


# ═════════════════════════════════════════════
# 每个 eval 的专属检查逻辑
# ═════════════════════════════════════════════


def grade_eval_1(content: str) -> list[dict]:
    """eval-1: 基本路径 -- 混合日志分析"""
    results = []

    # A1-01: 识别 ERROR 级别条目（至少 3 种不同 ERROR）
    error_types = ["TokenExpiredException", "ConnectionTimeoutException",
                   "DiskFullException", "AccessDeniedException"]
    found_errors = [et for et in error_types if et.lower() in content.lower()]
    # 也检查简化形式
    simple_errors = ["token", "timeout", "disk full", "access denied", "backup"]
    found_simple = [se for se in simple_errors if se.lower() in content.lower()]
    unique_errors = len(set(found_errors)) if found_errors else len(set(found_simple))
    passed = unique_errors >= 3 or (len(found_errors) >= 2 and len(found_simple) >= 3)
    evidence = f"识别的 ERROR 类型: {found_errors}; 简化: {found_simple}"
    results.append({
        "id": "A1-01",
        "text": "识别出 ERROR 级别条目（至少 3 种不同 ERROR）",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-02: 识别 WARN 级别条目
    passed, evidence = check_log_level_detection(content, "WARN")
    results.append({
        "id": "A1-02",
        "text": "识别出 WARN 级别条目",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-03: 按时间段分组
    passed, evidence = check_time_period_grouping(content)
    results.append({
        "id": "A1-03",
        "text": "按时间段分组输出",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-04: 每个时间段有异常数量统计
    passed, evidence = check_anomaly_count(content)
    results.append({
        "id": "A1-04",
        "text": "每个时间段有异常数量统计",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-05: 识别最频繁的异常类型
    # TokenExpiredException（2次）或 DiskFullException（2次）
    passed_freq, evidence_freq = check_frequency_analysis(content)
    passed_type, evidence_type = check_exception_type_mentioned(
        content, "TokenExpiredException"
    )
    passed_type2, _ = check_exception_type_mentioned(
        content, "DiskFullException"
    )
    passed = passed_freq and (passed_type or passed_type2)
    if not passed_freq and (passed_type or passed_type2):
        passed = True  # 提到了这些异常类型也算部分通过
    evidence = f"频率分析: {evidence_freq}; 类型: {evidence_type}"
    results.append({
        "id": "A1-05",
        "text": "识别出最频繁的异常类型",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-06: 包含建议关注的日志行
    passed, evidence = check_suggestion_present(content)
    results.append({
        "id": "A1-06",
        "text": "包含建议关注的日志行",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-07: 包含整体摘要
    summary_kw = ["总", "共", "摘要", "概览", "总计", "summary",
                  "overview", "total", "合计"]
    passed_kw, ev_kw = check_keywords(content, summary_kw, 1)
    passed_count, ev_count = check_anomaly_count(content)
    passed = passed_kw or passed_count
    evidence = f"摘要: {ev_kw}; 统计: {ev_count}"
    results.append({
        "id": "A1-07",
        "text": "报告包含整体摘要",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_2(content: str) -> list[dict]:
    """eval-2: 领域变体 -- 高频重复异常"""
    results = []

    # A2-01: 识别 ConnectionTimeout 为最频繁异常
    passed_type, ev_type = check_exception_type_mentioned(
        content, "ConnectionTimeout"
    )
    passed_freq, ev_freq = check_frequency_analysis(content)
    # ConnectionTimeout 和频繁/最多应在附近
    passed_prox, ev_prox = check_proximity(
        content, "ConnectionTimeout", "频繁", 100
    )
    passed_prox2, _ = check_proximity(
        content, "ConnectionTimeout", "最多", 100
    )
    passed_prox3, _ = check_proximity(
        content, "ConnectionTimeout", "most", 100
    )
    passed = passed_type and (passed_freq or passed_prox or passed_prox2 or passed_prox3)
    if passed_type and not passed:
        passed = passed_type  # 至少提到了这个类型
    evidence = f"类型: {ev_type}; 频率: {ev_freq}"
    results.append({
        "id": "A2-01",
        "text": "识别 ConnectionTimeout 为最频繁异常",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-02: 给出 ConnectionTimeout 次数或频率
    count_patterns = [
        r"(ConnectionTimeout|连接超时).{0,50}(\d+)\s*(次|个|条|times?|occurrences?)",
        r"(\d+)\s*(次|个|条|times?|occurrences?).{0,50}(ConnectionTimeout|连接超时)",
        r"(ConnectionTimeout|连接超时).{0,30}(\d+)",
    ]
    found_count = False
    for pat in count_patterns:
        m = re.search(pat, content, re.IGNORECASE | re.DOTALL)
        if m:
            found_count = True
            break
    # 宽松：只要有数量和 ConnectionTimeout 在同一段中
    if not found_count:
        found_count = bool(re.search(
            r"ConnectionTimeout", content, re.IGNORECASE
        )) and bool(re.search(r"\b1[01]\b", content))
    passed = found_count
    evidence = f"ConnectionTimeout 次数统计: {found_count}"
    results.append({
        "id": "A2-02",
        "text": "给出 ConnectionTimeout 出现次数",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-03: 识别 deadlock 异常
    passed, evidence = check_exception_type_mentioned(content, "deadlock")
    if not passed:
        passed, evidence = check_exception_type_mentioned(content, "Deadlock")
    results.append({
        "id": "A2-03",
        "text": "识别出 deadlock 异常",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-04: 包含时间段分组
    passed, evidence = check_time_period_grouping(content)
    if not passed:
        # 宽松：至少有时间线相关的分析
        time_kw = ["时间", "时段", "时间段", "时间线", "timeline",
                   "14:00", "14:", "时间范围"]
        passed, evidence = check_keywords(content, time_kw, 1)
    results.append({
        "id": "A2-04",
        "text": "包含时间段分组或时间线分析",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-05: 给出建议关注重点
    passed, evidence = check_suggestion_present(content)
    # 更具体：应提到 user-service
    passed_svc, ev_svc = check_service_mentioned(content, "user-service")
    if passed and passed_svc:
        evidence = f"{evidence}; 提到 user-service: {ev_svc}"
    elif passed_svc:
        passed = True
        evidence = f"提到 user-service: {ev_svc}"
    results.append({
        "id": "A2-05",
        "text": "给出建议关注的重点",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-06: 区分不同严重程度
    severity_kw = ["严重", "紧急", "优先", "critical", "urgent", "priority",
                   "更严重", "更紧急", "比", "相比"]
    passed, evidence = check_keywords(content, severity_kw, 1)
    if not passed:
        # 宽松：区分了 ConnectionTimeout 和 deadlock
        has_both = ("connectiontimeout" in content.lower() and
                    "deadlock" in content.lower())
        if has_both:
            passed = True
            evidence = "同时提到了 ConnectionTimeout 和 deadlock（隐含区分）"
    results.append({
        "id": "A2-06",
        "text": "区分了不同严重程度的异常",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_3(content: str) -> list[dict]:
    """eval-3: 领域跨越 -- 多服务混合日志"""
    results = []

    # A3-01: 识别出至少 3 个服务
    services = ["auth-service", "payment-service", "api-gateway"]
    found_services = [s for s in services if s.lower() in content.lower()]
    passed = len(found_services) >= 3
    if not passed:
        # 宽松：也接受去掉 -service 后缀的写法
        simple_services = ["auth", "payment", "api-gateway", "gateway"]
        found_simple = [s for s in simple_services if s.lower() in content.lower()]
        passed = len(found_simple) >= 3
        evidence = f"服务(宽松): {found_simple}"
    else:
        evidence = f"服务: {found_services}"
    results.append({
        "id": "A3-01",
        "text": "识别出至少 3 个不同服务",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-02: 按时间段分组
    passed, evidence = check_time_period_grouping(content)
    results.append({
        "id": "A3-02",
        "text": "按时间段分组输出",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-03: 识别 rate limit 为高频 ERROR
    rate_limit_kw = ["rate limit", "限流", "Rate limit", "频率限制"]
    passed, evidence = check_keywords(content, rate_limit_kw, 1)
    results.append({
        "id": "A3-03",
        "text": "识别 rate limit 为高频 ERROR",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-04: 提到 LDAP 连接问题
    passed, evidence = check_keywords(content, ["LDAP", "ldap"], 1)
    results.append({
        "id": "A3-04",
        "text": "提到 LDAP 连接问题",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-05: 提到支付失败
    payment_kw = ["CardDeclinedException", "支付失败", "payment_failed",
                  "card declined", "order #12345", "Stripe"]
    passed, evidence = check_keywords(content, payment_kw, 1)
    results.append({
        "id": "A3-05",
        "text": "提到支付失败",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-06: 每个时间段的异常数量统计
    passed, evidence = check_anomaly_count(content)
    results.append({
        "id": "A3-06",
        "text": "包含异常数量统计",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-07: 包含建议或改进
    passed, evidence = check_suggestion_present(content)
    results.append({
        "id": "A3-07",
        "text": "包含建议或改进",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_4(content: str) -> list[dict]:
    """eval-4: 模糊输入 -- 用户未使用触发关键词"""
    results = []

    # A4-01: 识别出日志分析场景
    analysis_kw = ["日志", "异常", "ERROR", "WARN", "分析", "log",
                   "摘要", "报告", "统计"]
    passed, evidence = check_keywords(content, analysis_kw, 2)
    results.append({
        "id": "A4-01",
        "text": "识别出日志分析场景",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-02: 识别 NullPointerException 为最频繁异常
    passed_type, ev_type = check_exception_type_mentioned(
        content, "NullPointerException"
    )
    if not passed_type:
        # 也接受 NPE 或 NullPointer
        passed_type, ev_type = check_keywords(
            content, ["NullPointer", "NPE", "空指针"], 1
        )
    passed_freq, ev_freq = check_frequency_analysis(content)
    passed = passed_type
    evidence = f"类型: {ev_type}; 频率: {ev_freq}"
    results.append({
        "id": "A4-02",
        "text": "识别 NullPointerException 为最频繁异常",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-03: 包含时间段分组
    passed, evidence = check_time_period_grouping(content)
    if not passed:
        time_kw = ["时间", "时段", "14:", "13:", "时间段"]
        passed, evidence = check_keywords(content, time_kw, 1)
    results.append({
        "id": "A4-03",
        "text": "包含时间段分组",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-04: 提到 Redis 问题
    passed, evidence = check_keywords(content, ["Redis", "redis", "缓存"], 1)
    results.append({
        "id": "A4-04",
        "text": "提到 Redis 相关问题",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-05: 包含异常数量统计
    passed, evidence = check_anomaly_count(content)
    results.append({
        "id": "A4-05",
        "text": "包含异常数量统计",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-06: 给出处理建议
    passed, evidence = check_suggestion_present(content)
    results.append({
        "id": "A4-06",
        "text": "给出处理建议",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_5(content: str) -> list[dict]:
    """eval-5: 边界 -- 全是 INFO 无异常"""
    results = []

    # A5-01: 明确指出无 ERROR/WARN
    no_error_kw = [
        "无异常", "没有异常", "无 ERROR", "没有 ERROR",
        "无 WARN", "没有 WARN", "未发现异常", "未检测到",
        "no error", "no warning", "no anomal", "no exception",
        "没有发现", "未发现", "不存在", "全部为 INFO",
        "均为 INFO", "只有 INFO", "都是 INFO",
    ]
    passed, evidence = check_keywords(content, no_error_kw, 1)
    results.append({
        "id": "A5-01",
        "text": "明确指出无 ERROR/WARN 条目",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-02: 没有编造异常
    passed, evidence = check_no_fabricated_errors(content)
    results.append({
        "id": "A5-02",
        "text": "没有编造不存在的异常",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-03: 确认系统正常
    passed, evidence = check_all_normal_confirmation(content)
    results.append({
        "id": "A5-03",
        "text": "确认系统运行正常",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-04: 仍然保持报告结构
    passed, evidence = check_report_structure(content)
    results.append({
        "id": "A5-04",
        "text": "保持报告结构",
        "passed": passed,
        "evidence": evidence,
    })

    return results


# ═════════════════════════════════════════════
# 主评分流程
# ═════════════════════════════════════════════

GRADERS = {
    1: grade_eval_1,
    2: grade_eval_2,
    3: grade_eval_3,
    4: grade_eval_4,
    5: grade_eval_5,
}


def compute_score(eval_id: int, grading_results: list[dict], evals_data: dict) -> dict:
    """根据 grading 结果和 evals.json 中的分值计算得分。"""
    eval_def = None
    for e in evals_data["evals"]:
        if e["id"] == eval_id:
            eval_def = e
            break
    if not eval_def:
        return {"earned": 0, "possible": 0, "percentage": 0}

    assertion_points = {a["id"]: a["points"] for a in eval_def["assertions"]}
    earned = 0
    possible = 0
    for result in grading_results:
        aid = result["id"]
        pts = assertion_points.get(aid, 0)
        possible += pts
        if result["passed"]:
            earned += pts

    return {
        "earned": earned,
        "possible": possible,
        "percentage": round(earned / possible * 100, 1) if possible > 0 else 0,
    }


def grade_single_eval(eval_dir: Path, eval_id: int, evals_data: dict) -> dict:
    """评分单个 eval 目录。"""
    content = collect_output(eval_dir)
    if not content.strip():
        return {
            "eval_id": eval_id,
            "status": "error",
            "message": f"目录为空或无可读文件: {eval_dir}",
            "results": [],
            "score": {"earned": 0, "possible": 0, "percentage": 0},
        }

    grader = GRADERS.get(eval_id)
    if not grader:
        return {
            "eval_id": eval_id,
            "status": "error",
            "message": f"未找到 eval_id={eval_id} 的评分函数",
            "results": [],
            "score": {"earned": 0, "possible": 0, "percentage": 0},
        }

    results = grader(content)
    score = compute_score(eval_id, results, evals_data)

    return {
        "eval_id": eval_id,
        "eval_name": next(
            (e["name"] for e in evals_data["evals"] if e["id"] == eval_id),
            f"eval-{eval_id}",
        ),
        "status": "graded",
        "results": results,
        "score": score,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])
    evals_data = load_evals()

    if not target.exists():
        print(f"错误: 路径不存在: {target}")
        sys.exit(1)

    all_gradings = []

    eval_dirs = []
    has_content = any(target.rglob("*.md")) or any(target.rglob("*.txt"))
    match = re.search(r"eval-?(\d+)", target.name)
    if match and has_content:
        eval_dirs = [(target, int(match.group(1)))]
    else:
        for subdir in sorted(target.iterdir()):
            if subdir.is_dir():
                match = re.search(r"eval-?(\d+)", subdir.name)
                if match:
                    eval_dirs.append((subdir, int(match.group(1))))

    if not eval_dirs:
        print(f"错误: 未在 {target} 下找到可评分的目录")
        print("目录结构应为 eval-1/, eval-2/, ... 包含 response.md 或其他输出文件")
        sys.exit(1)

    for eval_dir, eval_id in eval_dirs:
        print(f"\n{'=' * 60}")
        print(f"评分: eval-{eval_id} ({eval_dir.name})")
        print(f"{'=' * 60}")

        result = grade_single_eval(eval_dir, eval_id, evals_data)
        all_gradings.append(result)

        for r in result["results"]:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['id']}: {r['text']}")
            print(f"         {r['evidence']}")
        print(
            f"\n  得分: {result['score']['earned']}/{result['score']['possible']}"
            f" ({result['score']['percentage']}%)"
        )

    total_earned = sum(g["score"]["earned"] for g in all_gradings)
    total_possible = sum(g["score"]["possible"] for g in all_gradings)
    total_pct = (
        round(total_earned / total_possible * 100, 1) if total_possible > 0 else 0
    )

    summary = {
        "skill_name": "log-analyzer",
        "total_score": {
            "earned": total_earned,
            "possible": total_possible,
            "percentage": total_pct,
        },
        "per_eval": all_gradings,
    }

    print(f"\n{'=' * 60}")
    print(f"总分: {total_earned}/{total_possible} ({total_pct}%)")
    print(f"{'=' * 60}")

    output_path = target / "grading.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n评分结果已保存到: {output_path}")

    return summary


if __name__ == "__main__":
    main()
```

---

## 第六步：运行指南

### 目录结构

```
evals/
├── evals.json       # 5 个测试用例 + 断言定义（上方 JSON）
├── grade.py         # 自动评分脚本（上方 Python）
└── output/          # 运行 eval 后生成
    ├── eval-1/
    │   └── response.md
    ├── eval-2/
    │   └── response.md
    ├── eval-3/
    │   └── response.md
    ├── eval-4/
    │   └── response.md
    ├── eval-5/
    │   └── response.md
    └── grading.json  # 评分结果
```

### 运行步骤

1. **将 evals.json 和 grade.py 放入 `evals/` 目录**

2. **运行每个 eval**：对 eval-1 到 eval-5，启动一个 subagent：
   - 将 log-analyzer 的功能描述注入 subagent 的 system prompt（由于没有正式 SKILL.md，使用口头描述）
   - 将 eval 的 `prompt` 字段作为用户输入
   - 将输出保存到 `evals/output/eval-N/response.md`

3. **运行评分**：
   ```bash
   python3 evals/grade.py evals/output
   ```

4. **查看结果**：评分结果保存在 `evals/output/grading.json`

### 信息不完整性对 eval 质量的影响

由于 log-analyzer 没有正式的 SKILL.md，本 eval 套件存在以下**已知局限**：

1. **输出格式断言宽松** — 无法验证具体的报告模板格式（因为未定义），只能检查关键词和结构指标
2. **时间段判定可能有歧义** — "最近1小时"是相对于日志最新条目还是当前时间？eval 中故意在日志里包含了不同时间段的条目来绕过这个问题
3. **"最频繁异常类型"的分组粒度未定义** — eval-2 中 ConnectionTimeout 出现 11 次，足够明显，但在边界情况下（如两种异常各出现 3 次）结果可能不确定

**建议补充 SKILL.md 后改进**：
- 定义输出报告模板 → 添加更精确的 structural 断言
- 明确时间段判定规则 → 收窄 `check_time_period_grouping` 的匹配逻辑
- 定义异常类型分组规则 → 增加对分组粒度的验证

### 评分维度说明

| 维度 | 权重 | 衡量内容 |
|------|------|---------|
| error_detection | 25% | 能否正确识别 ERROR 和 WARN |
| time_grouping | 25% | 是否按时间段分组 |
| frequency_analysis | 20% | 是否统计数量并识别高频异常 |
| report_structure | 15% | 报告结构是否清晰 |
| boundary_handling | 15% | 无异常等边界场景的处理 |

### 5 个 eval 设计总结

| eval | 类型 | 核心验证点 | 断言数 | 总分 |
|------|------|---------|--------|------|
| eval-1 | 基本路径 | 混合日志的完整分析流程 | 7 | 51 |
| eval-2 | 领域变体 | 高频重复异常的统计和识别 | 6 | 42 |
| eval-3 | 领域跨越 | 多服务混合日志的交叉分析 | 7 | 43 |
| eval-4 | 模糊输入 | 无触发词时自动识别意图 | 6 | 38 |
| eval-5 | 边界降级 | 全 INFO 无异常的优雅处理 | 4 | 35 |
