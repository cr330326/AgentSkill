# Skill Eval Writer — 为 api-spec-generator 编写测试用例

## 第一步：阅读目标 skill 分析

### 目标 skill 核心信息

| 属性 | 分析结果 |
|------|---------|
| **输入格式** | 自然语言描述的 API 需求（端点、参数、返回值） |
| **输出格式** | 文件 `api-spec.yaml`（OpenAPI 3.0 YAML）+ 对话简要说明 |
| **必须出现的输出元素** | openapi: 3.0.x, info, paths, components/schemas |
| **分支逻辑** | 不同 HTTP 方法（GET/POST/PUT/DELETE）；有无 schemas |
| **边界** | 无端点描述、冲突的端点、超大 API 需求 |

### 核心规则清单

1. 生成文件必须是 `api-spec.yaml`
2. 必须是合法的 OpenAPI 3.0 规范（openapi: 3.0.x）
3. 必须包含 info 块（title, version, description）
4. 必须包含 paths 块（每个端点对应 HTTP 方法）
5. 必须包含 components/schemas（数据模型定义）
6. 对话输出包含简要说明

### 关键特征：这是文件生成型 skill

- grade.py 必须使用 `collect_output_files()` 而非 `collect_output()`
- `grade_eval_N()` 参数是 `files: dict[str, str]`
- 需要 `find_file_by_name()` 查找 `api-spec.yaml`
- 需要检查 YAML 文件内容中的 OpenAPI 关键字段

---

## 第二步：设计 5 个 eval 用例

| 槽位 | 名称 | 设计意图 |
|------|------|---------|
| eval-1 | **基本路径：简单用户管理 API** | 描述 /users 端点的 CRUD，验证完整的 OpenAPI 生成流程 |
| eval-2 | **领域变体：电商多端点 API** | 包含 /products、/orders、/cart 多个资源，验证多端点和多 schema |
| eval-3 | **领域跨越：IoT 设备 API** | 跨出常规 Web API 领域，测试传感器数据、WebSocket 等非典型端点 |
| eval-4 | **模糊/自动检测：用户未明确说"生成 API 规范"** | 用户只说"帮我把这个功能做成接口文档"，不使用 OpenAPI/swagger 触发词 |
| eval-5 | **边界/降级：只有一个端点且无参数** | 极简需求，测试 skill 是否仍生成完整的 OpenAPI 结构 |

---

## 第三步 & 第四步：evals.json

```json
{
  "skill_name": "api-spec-generator",
  "version": "1.0",
  "description": "验证 api-spec-generator skill 能否根据用户描述的 API 需求正确生成 OpenAPI 3.0 规范的 YAML 文件",
  "scoring": {
    "total_points": 100,
    "dimensions": {
      "file_generation": {
        "weight": 25,
        "description": "是否生成了 api-spec.yaml 文件，文件是否可读"
      },
      "openapi_compliance": {
        "weight": 30,
        "description": "生成的文件是否符合 OpenAPI 3.0 规范结构（openapi、info、paths、components）"
      },
      "endpoint_accuracy": {
        "weight": 25,
        "description": "paths 中的端点是否与用户需求一致（路径、HTTP 方法、参数）"
      },
      "schema_quality": {
        "weight": 10,
        "description": "components/schemas 中的数据模型是否合理（字段名、类型）"
      },
      "boundary_handling": {
        "weight": 10,
        "description": "对模糊输入和边界场景的处理质量"
      }
    }
  },
  "evals": [
    {
      "id": 1,
      "name": "basic-user-crud-api",
      "prompt": "请帮我生成一个用户管理的 API 规范。需要以下端点：\n\n1. GET /users — 获取用户列表，支持分页参数 page 和 limit\n2. POST /users — 创建新用户，请求体包含 name（字符串）、email（字符串）、age（整数）\n3. GET /users/{id} — 获取单个用户详情\n4. DELETE /users/{id} — 删除用户\n\n返回的用户对象包含 id、name、email、age、created_at 字段。",
      "expected_output": "生成 api-spec.yaml 文件，包含 openapi: 3.0.x、info 块、4 个 /users 相关的 path。schemas 中定义 User 模型（含 id/name/email/age/created_at）。对话中简要说明生成了什么。",
      "assertions": [
        {
          "id": "A1-01",
          "text": "生成了 api-spec.yaml 文件",
          "type": "file_exists",
          "points": 10
        },
        {
          "id": "A1-02",
          "text": "文件包含 openapi: 3.0 版本声明",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-03",
          "text": "文件包含 info 块（含 title 和 version）",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A1-04",
          "text": "paths 中包含 /users 端点",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-05",
          "text": "paths 中包含 /users/{id} 端点",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-06",
          "text": "/users 路径下包含 get 和 post 方法",
          "type": "content",
          "points": 7
        },
        {
          "id": "A1-07",
          "text": "components/schemas 中定义了 User 相关的数据模型",
          "type": "content",
          "points": 7
        },
        {
          "id": "A1-08",
          "text": "User schema 包含 name、email、age 字段",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 2,
      "name": "ecommerce-multi-endpoint",
      "prompt": "为一个电商平台生成 OpenAPI 规范，需要以下 API：\n\n商品模块：\n- GET /products — 商品列表（支持 category 过滤）\n- POST /products — 创建商品（name, price, category, stock）\n- GET /products/{id} — 商品详情\n\n订单模块：\n- POST /orders — 创建订单（product_id, quantity, shipping_address）\n- GET /orders/{id} — 订单详情\n- PUT /orders/{id}/status — 更新订单状态（status 枚举：pending, paid, shipped, delivered）\n\n商品对象：id, name, price, category, stock, created_at\n订单对象：id, product_id, quantity, total_price, status, shipping_address, created_at",
      "expected_output": "生成包含 /products 和 /orders 两组端点的 OpenAPI 文件。schemas 中定义 Product 和 Order 两个模型。status 字段使用 enum 约束。",
      "assertions": [
        {
          "id": "A2-01",
          "text": "生成了 api-spec.yaml 文件",
          "type": "file_exists",
          "points": 8
        },
        {
          "id": "A2-02",
          "text": "paths 中包含 /products 端点",
          "type": "content",
          "points": 7
        },
        {
          "id": "A2-03",
          "text": "paths 中包含 /orders 端点",
          "type": "content",
          "points": 7
        },
        {
          "id": "A2-04",
          "text": "paths 中包含 PUT 方法（用于更新订单状态）",
          "type": "content",
          "points": 5
        },
        {
          "id": "A2-05",
          "text": "schemas 中定义了 Product 相关模型",
          "type": "content",
          "points": 6
        },
        {
          "id": "A2-06",
          "text": "schemas 中定义了 Order 相关模型",
          "type": "content",
          "points": 6
        },
        {
          "id": "A2-07",
          "text": "订单状态字段使用 enum 约束（pending/paid/shipped/delivered）",
          "type": "content",
          "points": 5
        },
        {
          "id": "A2-08",
          "text": "文件包含 openapi: 3.0 版本声明",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 3,
      "name": "iot-device-api",
      "prompt": "我们做 IoT 平台，帮我生成 API 文档：\n\n设备管理：\n- GET /devices — 获取设备列表，按 status 过滤（online/offline/error）\n- POST /devices — 注册新设备（serial_number, device_type, location）\n- GET /devices/{id}/readings — 获取设备传感器读数（支持 start_time/end_time 时间范围查询）\n\n告警：\n- GET /alerts — 获取告警列表（按 severity 过滤：critical/warning/info）\n- POST /alerts/{id}/acknowledge — 确认告警\n\n设备对象：id, serial_number, device_type, location, status, last_seen\n读数对象：timestamp, temperature, humidity, battery_level\n告警对象：id, device_id, severity, message, created_at, acknowledged",
      "expected_output": "生成 OpenAPI 文件，包含 /devices 和 /alerts 端点。schemas 定义 Device、Reading、Alert 模型。读数查询支持时间范围参数。",
      "assertions": [
        {
          "id": "A3-01",
          "text": "生成了 api-spec.yaml 文件",
          "type": "file_exists",
          "points": 8
        },
        {
          "id": "A3-02",
          "text": "paths 中包含 /devices 端点",
          "type": "content",
          "points": 7
        },
        {
          "id": "A3-03",
          "text": "paths 中包含 /alerts 端点",
          "type": "content",
          "points": 7
        },
        {
          "id": "A3-04",
          "text": "paths 中包含 /devices/{id}/readings 端点",
          "type": "content",
          "points": 6
        },
        {
          "id": "A3-05",
          "text": "schemas 中包含传感器读数相关字段（temperature/humidity/battery）",
          "type": "content",
          "points": 5
        },
        {
          "id": "A3-06",
          "text": "告警严重程度使用 enum 约束（critical/warning/info）",
          "type": "content",
          "points": 5
        },
        {
          "id": "A3-07",
          "text": "文件包含 openapi: 3.0 版本声明和 info 块",
          "type": "structural",
          "points": 5
        }
      ]
    },
    {
      "id": 4,
      "name": "fuzzy-input-no-trigger-words",
      "prompt": "帮我把这个功能做成接口文档吧：\n\n我们有一个博客系统，需要这些功能：\n- 查看文章列表，可以按标签筛选\n- 发布新文章，包含标题、内容、标签列表\n- 修改文章\n- 删除文章\n- 给文章点赞\n\n文章有这些信息：标题、内容、作者、标签、点赞数、发布时间",
      "expected_output": "即使用户没有说"OpenAPI"或"API 规范"，skill 应识别需求并生成 api-spec.yaml。paths 包含文章 CRUD + 点赞端点。schemas 定义文章模型。",
      "assertions": [
        {
          "id": "A4-01",
          "text": "生成了 api-spec.yaml 文件（即使用户未使用 OpenAPI 触发词）",
          "type": "file_exists",
          "points": 10
        },
        {
          "id": "A4-02",
          "text": "文件包含 openapi: 3.0 版本声明",
          "type": "content",
          "points": 6
        },
        {
          "id": "A4-03",
          "text": "paths 中包含文章相关端点（如 /articles 或 /posts 或 /blogs）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A4-04",
          "text": "包含点赞功能的端点（如 POST /articles/{id}/like）",
          "type": "content",
          "points": 6
        },
        {
          "id": "A4-05",
          "text": "schemas 中包含文章模型（含标题/内容/标签相关字段）",
          "type": "content",
          "points": 6
        },
        {
          "id": "A4-06",
          "text": "paths 中包含 get/post/put/delete 方法覆盖 CRUD 操作",
          "type": "content",
          "points": 6
        }
      ]
    },
    {
      "id": 5,
      "name": "boundary-minimal-single-endpoint",
      "prompt": "生成一个 API 规范，只有一个端点：\n\nGET /health — 返回服务健康状态，无参数，返回 { \"status\": \"ok\" }",
      "expected_output": "即使只有一个极简端点，仍然生成完整的 OpenAPI 结构（openapi、info、paths、components）。paths 只有 /health 的 GET。schemas 可以很简单或为空。",
      "assertions": [
        {
          "id": "A5-01",
          "text": "生成了 api-spec.yaml 文件",
          "type": "file_exists",
          "points": 10
        },
        {
          "id": "A5-02",
          "text": "文件包含 openapi: 3.0 版本声明",
          "type": "content",
          "points": 7
        },
        {
          "id": "A5-03",
          "text": "paths 中包含 /health 端点",
          "type": "content",
          "points": 8
        },
        {
          "id": "A5-04",
          "text": "/health 只有 get 方法（不应有 post/put/delete）",
          "type": "content",
          "points": 5
        },
        {
          "id": "A5-05",
          "text": "文件包含 info 块（即使是极简 API 也要有 title/version）",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A5-06",
          "text": "responses 中包含 200 状态码和 status: ok 的描述",
          "type": "content",
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
api-spec-generator 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 api-spec.yaml（生成的文件）和可选的 response.md（对话输出）。

也可以传入单个 eval 目录:
    python grade.py output_dir/eval-1

脚本自动检测输出，执行可程序化验证的断言。
最终输出 grading.json 到 output_dir/ 下。
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
# 文件收集工具 — 文件生成型
# ═════════════════════════════════════════════


def collect_output_files(eval_dir: Path) -> dict[str, str]:
    """递归收集 eval 目录下所有文件内容，返回 {相对路径: 内容}。
    适用于文件生成型 skill。"""
    files = {}
    for fpath in eval_dir.rglob("*"):
        if fpath.is_file():
            rel = str(fpath.relative_to(eval_dir))
            try:
                files[rel] = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                files[rel] = "<binary or unreadable>"
    return files


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


# ── 文件生成型 skill 专用 ──


def find_file_by_name(files: dict[str, str], name: str) -> tuple[str, str]:
    """在 files dict 中查找文件名匹配的文件（不区分目录层级）。
    返回 (path, content) 或 (None, None)。"""
    for path, content in files.items():
        if Path(path).name.lower() == name.lower():
            return path, content
    return None, None


def find_file_by_extension(files: dict[str, str], ext: str) -> tuple[str, str]:
    """在 files dict 中查找指定扩展名的文件。
    返回 (path, content) 或 (None, None)。"""
    for path, content in files.items():
        if path.lower().endswith(ext.lower()):
            return path, content
    return None, None


def find_yaml_spec(files: dict[str, str]) -> tuple[str, str]:
    """在 files 中查找 api-spec.yaml 或任何 .yaml/.yml 文件。
    优先匹配 api-spec.yaml，其次匹配任意 .yaml/.yml。"""
    # 优先精确匹配
    path, content = find_file_by_name(files, "api-spec.yaml")
    if path is not None:
        return path, content
    # 尝试 .yml 后缀
    path, content = find_file_by_name(files, "api-spec.yml")
    if path is not None:
        return path, content
    # 回退：任何 yaml/yml 文件
    for p, c in files.items():
        if p.lower().endswith((".yaml", ".yml")):
            return p, c
    # 最后回退：在 response.md 中查找 YAML 代码块
    for p, c in files.items():
        if p.lower().endswith(".md"):
            yaml_blocks = re.findall(r"```ya?ml\s*\n(.*?)```", c, re.DOTALL)
            if yaml_blocks:
                # 返回最长的 YAML 块（最可能是完整 spec）
                longest = max(yaml_blocks, key=len)
                return p + "::yaml-block", longest
    return None, None


def check_openapi_version(content: str) -> tuple[bool, str]:
    """检查是否包含 openapi: 3.0.x 版本声明。"""
    pattern = r"openapi\s*:\s*['\"]?3\.0\.\d+['\"]?"
    m = re.search(pattern, content, re.IGNORECASE)
    if m:
        return True, f"找到 OpenAPI 版本声明: '{m.group()}'"
    # 宽松匹配：openapi: "3.0" 或 openapi: 3.0
    pattern = r"openapi\s*:\s*['\"]?3\.0['\"]?"
    m = re.search(pattern, content, re.IGNORECASE)
    if m:
        return True, f"找到 OpenAPI 版本声明（宽松）: '{m.group()}'"
    # 也匹配 3.1.x
    pattern = r"openapi\s*:\s*['\"]?3\.\d+\.\d+['\"]?"
    m = re.search(pattern, content, re.IGNORECASE)
    if m:
        return True, f"找到 OpenAPI 版本声明（3.x）: '{m.group()}'"
    return False, "未找到 openapi: 3.0.x 版本声明"


def check_info_block(content: str) -> tuple[bool, str]:
    """检查是否包含 info 块，且含 title 和 version。"""
    has_info = bool(re.search(r"^info\s*:", content, re.MULTILINE))
    has_title = bool(re.search(r"^\s+title\s*:", content, re.MULTILINE))
    has_version = bool(re.search(r"^\s+version\s*:", content, re.MULTILINE))
    if not has_info:
        return False, "未找到 info: 块"
    missing = []
    if not has_title:
        missing.append("title")
    if not has_version:
        missing.append("version")
    if missing:
        return False, f"info 块缺少: {missing}"
    return True, "info 块结构正确（含 title 和 version）"


def check_path_exists(content: str, path_pattern: str) -> tuple[bool, str]:
    """检查 paths 中是否包含指定的 API 路径。
    path_pattern 可以是精确路径如 /users 或含变量的 /users/{id}。"""
    # 在 YAML 中路径通常是 "  /users:" 或 "  '/users/{id}':"
    escaped = re.escape(path_pattern)
    # 允许 {xxx} 中的变量名不完全匹配
    escaped = re.sub(r"\\{[^}]+\\}", r"\\{[^}]+\\}", escaped)
    pattern = rf"^\s*['\"]?{escaped}['\"]?\s*:"
    m = re.search(pattern, content, re.MULTILINE)
    if m:
        return True, f"找到路径 '{path_pattern}': '{m.group().strip()}'"
    # 宽松匹配：只查找路径字符串
    if path_pattern.lower() in content.lower():
        return True, f"找到路径 '{path_pattern}'（宽松匹配）"
    return False, f"未找到路径 '{path_pattern}'"


def check_http_methods(content: str, path_pattern: str, methods: list[str]) -> tuple[bool, str]:
    """检查指定路径下是否包含预期的 HTTP 方法。"""
    # 提取路径下的内容块
    escaped = re.escape(path_pattern)
    escaped = re.sub(r"\\{[^}]+\\}", r"\\{[^}]+\\}", escaped)
    pattern = rf"['\"]?{escaped}['\"]?\s*:\s*\n((?:\s+.*\n)*)"
    m = re.search(pattern, content, re.MULTILINE)

    if not m:
        # 回退：在全文中查找路径和方法的近邻
        found_methods = []
        for method in methods:
            p, _ = check_proximity(content, path_pattern, method, 200)
            if p:
                found_methods.append(method)
        if found_methods:
            passed = len(found_methods) >= len(methods)
            return passed, f"近邻匹配到方法: {found_methods}"
        return False, f"未找到路径 '{path_pattern}' 的内容块"

    path_content = m.group(1)
    found = [method for method in methods if re.search(rf"^\s+{method}\s*:", path_content, re.MULTILINE | re.IGNORECASE)]
    passed = len(found) >= len(methods)
    evidence = f"路径 '{path_pattern}' 下找到方法: {found}, 期望: {methods}"
    return passed, evidence


def check_schemas_defined(content: str, schema_keywords: list[str], min_hits: int = 1) -> tuple[bool, str]:
    """检查 components/schemas 区域是否定义了预期的模型。"""
    # 提取 schemas 区域
    schemas_match = re.search(
        r"(schemas|components)\s*:.*",
        content, re.DOTALL | re.IGNORECASE
    )
    search_text = schemas_match.group() if schemas_match else content

    found = [kw for kw in schema_keywords if kw.lower() in search_text.lower()]
    passed = len(found) >= min_hits
    evidence = f"schemas 中命中 {len(found)}/{len(schema_keywords)}: {found}"
    return passed, evidence


def check_enum_values(content: str, enum_values: list[str], min_hits: int = 2) -> tuple[bool, str]:
    """检查内容中是否包含 enum 约束及预期的枚举值。"""
    has_enum = bool(re.search(r"enum\s*:", content, re.IGNORECASE))
    found_values = [v for v in enum_values if v.lower() in content.lower()]
    passed = has_enum and len(found_values) >= min_hits
    evidence = f"enum 关键字={has_enum}; 枚举值命中 {len(found_values)}/{len(enum_values)}: {found_values}"
    return passed, evidence


def check_no_extra_methods(content: str, path_pattern: str, allowed: list[str], forbidden: list[str]) -> tuple[bool, str]:
    """检查指定路径下不包含不该有的 HTTP 方法。"""
    for method in forbidden:
        p, _ = check_proximity(content, path_pattern, method, 150)
        if p:
            return False, f"路径 '{path_pattern}' 不应包含 {method} 方法"
    return True, f"路径 '{path_pattern}' 未包含禁止的方法: {forbidden}"


# ═════════════════════════════════════════════
# 每个 eval 的专属检查逻辑
# ═════════════════════════════════════════════


def grade_eval_1(files: dict[str, str]) -> list[dict]:
    """eval-1: 基本路径 — 简单用户管理 CRUD API"""
    results = []

    # A1-01: 生成了 api-spec.yaml 文件
    yaml_path, yaml_content = find_yaml_spec(files)
    passed = yaml_path is not None
    evidence = f"找到文件: {yaml_path}" if passed else "未找到 api-spec.yaml 或任何 YAML 文件"
    results.append({
        "id": "A1-01",
        "text": "生成了 api-spec.yaml 文件",
        "passed": passed,
        "evidence": evidence,
    })

    if yaml_content is None:
        # 如果没有 YAML 文件，后续断言全部失败
        for aid, text in [
            ("A1-02", "文件包含 openapi: 3.0 版本声明"),
            ("A1-03", "文件包含 info 块"),
            ("A1-04", "paths 中包含 /users 端点"),
            ("A1-05", "paths 中包含 /users/{id} 端点"),
            ("A1-06", "/users 路径下包含 get 和 post 方法"),
            ("A1-07", "schemas 中定义了 User 相关数据模型"),
            ("A1-08", "User schema 包含 name、email、age 字段"),
        ]:
            results.append({"id": aid, "text": text, "passed": False, "evidence": "无 YAML 文件可检查"})
        return results

    # A1-02: 文件包含 openapi: 3.0
    passed, evidence = check_openapi_version(yaml_content)
    results.append({
        "id": "A1-02",
        "text": "文件包含 openapi: 3.0 版本声明",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-03: 文件包含 info 块
    passed, evidence = check_info_block(yaml_content)
    results.append({
        "id": "A1-03",
        "text": "文件包含 info 块（含 title 和 version）",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-04: paths 中包含 /users
    passed, evidence = check_path_exists(yaml_content, "/users")
    results.append({
        "id": "A1-04",
        "text": "paths 中包含 /users 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-05: paths 中包含 /users/{id}
    passed, evidence = check_path_exists(yaml_content, "/users/{id}")
    results.append({
        "id": "A1-05",
        "text": "paths 中包含 /users/{id} 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-06: /users 下包含 get 和 post
    passed, evidence = check_http_methods(yaml_content, "/users", ["get", "post"])
    results.append({
        "id": "A1-06",
        "text": "/users 路径下包含 get 和 post 方法",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-07: schemas 中定义了 User 相关模型
    passed, evidence = check_schemas_defined(
        yaml_content, ["User", "user"], min_hits=1
    )
    results.append({
        "id": "A1-07",
        "text": "schemas 中定义了 User 相关数据模型",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-08: User schema 包含 name、email、age 字段
    passed, evidence = check_keywords(yaml_content, ["name", "email", "age"], 3)
    results.append({
        "id": "A1-08",
        "text": "User schema 包含 name、email、age 字段",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_2(files: dict[str, str]) -> list[dict]:
    """eval-2: 领域变体 — 电商多端点 API"""
    results = []

    yaml_path, yaml_content = find_yaml_spec(files)

    # A2-01: 生成了 api-spec.yaml 文件
    passed = yaml_path is not None
    evidence = f"找到文件: {yaml_path}" if passed else "未找到 YAML 文件"
    results.append({
        "id": "A2-01",
        "text": "生成了 api-spec.yaml 文件",
        "passed": passed,
        "evidence": evidence,
    })

    if yaml_content is None:
        for aid, text in [
            ("A2-02", "paths 中包含 /products"),
            ("A2-03", "paths 中包含 /orders"),
            ("A2-04", "包含 PUT 方法"),
            ("A2-05", "schemas 定义 Product 模型"),
            ("A2-06", "schemas 定义 Order 模型"),
            ("A2-07", "订单状态使用 enum 约束"),
            ("A2-08", "包含 openapi: 3.0 声明"),
        ]:
            results.append({"id": aid, "text": text, "passed": False, "evidence": "无 YAML 文件可检查"})
        return results

    # A2-02: /products 端点
    passed, evidence = check_path_exists(yaml_content, "/products")
    results.append({
        "id": "A2-02",
        "text": "paths 中包含 /products 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-03: /orders 端点
    passed, evidence = check_path_exists(yaml_content, "/orders")
    results.append({
        "id": "A2-03",
        "text": "paths 中包含 /orders 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-04: 包含 PUT 方法
    has_put = bool(re.search(r"^\s+put\s*:", yaml_content, re.MULTILINE | re.IGNORECASE))
    if not has_put:
        has_put = "put:" in yaml_content.lower() or "put :" in yaml_content.lower()
    passed = has_put
    evidence = f"PUT 方法: {has_put}"
    results.append({
        "id": "A2-04",
        "text": "paths 中包含 PUT 方法",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-05: schemas 定义 Product 模型
    passed, evidence = check_schemas_defined(yaml_content, ["Product", "product"], 1)
    results.append({
        "id": "A2-05",
        "text": "schemas 中定义了 Product 相关模型",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-06: schemas 定义 Order 模型
    passed, evidence = check_schemas_defined(yaml_content, ["Order", "order"], 1)
    results.append({
        "id": "A2-06",
        "text": "schemas 中定义了 Order 相关模型",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-07: 订单状态 enum
    passed, evidence = check_enum_values(
        yaml_content, ["pending", "paid", "shipped", "delivered"], 3
    )
    results.append({
        "id": "A2-07",
        "text": "订单状态字段使用 enum 约束",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-08: openapi 版本
    passed, evidence = check_openapi_version(yaml_content)
    results.append({
        "id": "A2-08",
        "text": "文件包含 openapi: 3.0 版本声明",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_3(files: dict[str, str]) -> list[dict]:
    """eval-3: 领域跨越 — IoT 设备 API"""
    results = []

    yaml_path, yaml_content = find_yaml_spec(files)

    # A3-01: 生成了文件
    passed = yaml_path is not None
    evidence = f"找到文件: {yaml_path}" if passed else "未找到 YAML 文件"
    results.append({
        "id": "A3-01",
        "text": "生成了 api-spec.yaml 文件",
        "passed": passed,
        "evidence": evidence,
    })

    if yaml_content is None:
        for aid, text in [
            ("A3-02", "/devices 端点"),
            ("A3-03", "/alerts 端点"),
            ("A3-04", "/devices/{id}/readings 端点"),
            ("A3-05", "传感器读数字段"),
            ("A3-06", "告警 severity enum"),
            ("A3-07", "openapi 和 info"),
        ]:
            results.append({"id": aid, "text": text, "passed": False, "evidence": "无 YAML 文件可检查"})
        return results

    # A3-02: /devices
    passed, evidence = check_path_exists(yaml_content, "/devices")
    results.append({
        "id": "A3-02",
        "text": "paths 中包含 /devices 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-03: /alerts
    passed, evidence = check_path_exists(yaml_content, "/alerts")
    results.append({
        "id": "A3-03",
        "text": "paths 中包含 /alerts 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-04: /devices/{id}/readings
    # 路径可能有不同的变量名
    passed = False
    evidence = "未找到 readings 端点"
    for path_variant in ["/devices/{id}/readings", "/devices/{device_id}/readings",
                          "/devices/{deviceId}/readings"]:
        p, e = check_path_exists(yaml_content, path_variant)
        if p:
            passed = True
            evidence = e
            break
    if not passed:
        # 宽松：检查是否同时有 devices 和 readings
        if "readings" in yaml_content.lower() and "devices" in yaml_content.lower():
            passed = True
            evidence = "找到 devices 和 readings 关键词（宽松匹配）"
    results.append({
        "id": "A3-04",
        "text": "paths 中包含 /devices/{id}/readings 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-05: 传感器读数字段
    sensor_fields = ["temperature", "humidity", "battery"]
    passed, evidence = check_keywords(yaml_content, sensor_fields, 2)
    results.append({
        "id": "A3-05",
        "text": "schemas 中包含传感器读数相关字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-06: 告警 severity enum
    passed, evidence = check_enum_values(
        yaml_content, ["critical", "warning", "info"], 2
    )
    results.append({
        "id": "A3-06",
        "text": "告警严重程度使用 enum 约束",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-07: openapi + info
    passed_ver, ev_ver = check_openapi_version(yaml_content)
    passed_info, ev_info = check_info_block(yaml_content)
    passed = passed_ver and passed_info
    evidence = f"版本: {ev_ver}; info: {ev_info}"
    results.append({
        "id": "A3-07",
        "text": "文件包含 openapi: 3.0 版本声明和 info 块",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_4(files: dict[str, str]) -> list[dict]:
    """eval-4: 模糊输入 — 用户未使用 OpenAPI 触发词"""
    results = []

    yaml_path, yaml_content = find_yaml_spec(files)

    # A4-01: 即使未使用触发词也生成了文件
    passed = yaml_path is not None
    evidence = f"找到文件: {yaml_path}" if passed else "未找到 YAML 文件"
    results.append({
        "id": "A4-01",
        "text": "生成了 api-spec.yaml 文件（即使用户未使用 OpenAPI 触发词）",
        "passed": passed,
        "evidence": evidence,
    })

    if yaml_content is None:
        for aid, text in [
            ("A4-02", "openapi 版本"),
            ("A4-03", "文章端点"),
            ("A4-04", "点赞端点"),
            ("A4-05", "文章模型"),
            ("A4-06", "CRUD 方法覆盖"),
        ]:
            results.append({"id": aid, "text": text, "passed": False, "evidence": "无 YAML 文件可检查"})
        return results

    # A4-02: openapi 版本
    passed, evidence = check_openapi_version(yaml_content)
    results.append({
        "id": "A4-02",
        "text": "文件包含 openapi: 3.0 版本声明",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-03: 文章相关端点
    article_paths = ["/articles", "/posts", "/blogs", "/blog"]
    passed = False
    evidence = "未找到文章相关端点"
    for ap in article_paths:
        p, e = check_path_exists(yaml_content, ap)
        if p:
            passed = True
            evidence = e
            break
    results.append({
        "id": "A4-03",
        "text": "paths 中包含文章相关端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-04: 点赞端点
    like_patterns = ["like", "likes", "upvote", "favorite", "thumb"]
    passed, evidence = check_keywords(yaml_content, like_patterns, 1)
    results.append({
        "id": "A4-04",
        "text": "包含点赞功能的端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-05: 文章模型字段
    article_fields = ["title", "content", "tag"]
    passed, evidence = check_keywords(yaml_content, article_fields, 2)
    results.append({
        "id": "A4-05",
        "text": "schemas 中包含文章模型（含标题/内容/标签相关字段）",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-06: CRUD 方法覆盖
    crud_methods = ["get", "post", "put", "delete"]
    found_methods = [m for m in crud_methods
                     if re.search(rf"^\s+{m}\s*:", yaml_content, re.MULTILINE | re.IGNORECASE)]
    passed = len(found_methods) >= 3  # 至少 3 个 CRUD 方法
    evidence = f"找到 HTTP 方法: {found_methods}"
    results.append({
        "id": "A4-06",
        "text": "paths 中包含 CRUD 方法覆盖",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_5(files: dict[str, str]) -> list[dict]:
    """eval-5: 边界 — 极简单端点 API"""
    results = []

    yaml_path, yaml_content = find_yaml_spec(files)

    # A5-01: 生成了文件
    passed = yaml_path is not None
    evidence = f"找到文件: {yaml_path}" if passed else "未找到 YAML 文件"
    results.append({
        "id": "A5-01",
        "text": "生成了 api-spec.yaml 文件",
        "passed": passed,
        "evidence": evidence,
    })

    if yaml_content is None:
        for aid, text in [
            ("A5-02", "openapi 版本"),
            ("A5-03", "/health 端点"),
            ("A5-04", "只有 get 方法"),
            ("A5-05", "info 块"),
            ("A5-06", "200 状态码"),
        ]:
            results.append({"id": aid, "text": text, "passed": False, "evidence": "无 YAML 文件可检查"})
        return results

    # A5-02: openapi 版本
    passed, evidence = check_openapi_version(yaml_content)
    results.append({
        "id": "A5-02",
        "text": "文件包含 openapi: 3.0 版本声明",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-03: /health 端点
    passed, evidence = check_path_exists(yaml_content, "/health")
    results.append({
        "id": "A5-03",
        "text": "paths 中包含 /health 端点",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-04: /health 只有 get（不应有 post/put/delete）
    # 提取 /health 路径下的内容
    health_section = ""
    m = re.search(
        r"/health['\"]?\s*:\s*\n((?:\s{4,}.*\n)*)",
        yaml_content, re.MULTILINE
    )
    if m:
        health_section = m.group(1)

    if health_section:
        has_get = bool(re.search(r"^\s+get\s*:", health_section, re.MULTILINE | re.IGNORECASE))
        has_post = bool(re.search(r"^\s+post\s*:", health_section, re.MULTILINE | re.IGNORECASE))
        has_put = bool(re.search(r"^\s+put\s*:", health_section, re.MULTILINE | re.IGNORECASE))
        has_delete = bool(re.search(r"^\s+delete\s*:", health_section, re.MULTILINE | re.IGNORECASE))
        passed = has_get and not has_post and not has_put and not has_delete
        extra = [m for m, v in [("post", has_post), ("put", has_put), ("delete", has_delete)] if v]
        evidence = f"get={has_get}, 多余方法: {extra}" if extra else f"get={has_get}, 无多余方法"
    else:
        # 回退：检查全文中 /health 和 get 的关联
        p, e = check_proximity(yaml_content, "/health", "get", 100)
        passed = p
        evidence = f"回退近邻匹配: {e}"
    results.append({
        "id": "A5-04",
        "text": "/health 只有 get 方法",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-05: info 块
    passed, evidence = check_info_block(yaml_content)
    results.append({
        "id": "A5-05",
        "text": "文件包含 info 块",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-06: responses 包含 200 和 status
    has_200 = bool(re.search(r"['\"]?200['\"]?\s*:", yaml_content))
    has_status = "status" in yaml_content.lower()
    passed = has_200 and has_status
    evidence = f"200 响应={has_200}, status 字段={has_status}"
    results.append({
        "id": "A5-06",
        "text": "responses 中包含 200 状态码和 status 描述",
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
    """评分单个 eval 目录。使用 collect_output_files 收集文件。"""
    files = collect_output_files(eval_dir)
    if not files:
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

    results = grader(files)
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
    has_content = any(target.rglob("*.yaml")) or any(target.rglob("*.yml")) or any(target.rglob("*.md"))
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
        print("目录结构应为 eval-1/, eval-2/, ... 包含 api-spec.yaml 或其他输出文件")
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
        "skill_name": "api-spec-generator",
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
    │   ├── api-spec.yaml    # skill 生成的文件
    │   └── response.md      # 可选：对话输出
    ├── eval-2/
    │   ├── api-spec.yaml
    │   └── response.md
    ├── eval-3/
    │   ├── api-spec.yaml
    │   └── response.md
    ├── eval-4/
    │   ├── api-spec.yaml
    │   └── response.md
    ├── eval-5/
    │   ├── api-spec.yaml
    │   └── response.md
    └── grading.json  # 评分结果
```

### 运行步骤

1. **将 evals.json 和 grade.py 放入 `evals/` 目录**

2. **运行每个 eval**：对 eval-1 到 eval-5，启动一个 subagent：
   - 将 api-spec-generator 的 SKILL.md 注入 subagent 的 system prompt
   - 将 eval 的 `prompt` 字段作为用户输入
   - 将 subagent 生成的文件保存到 `evals/output/eval-N/` 目录下
   - 将对话输出保存到 `evals/output/eval-N/response.md`（可选）

3. **运行评分**：
   ```bash
   python3 evals/grade.py evals/output
   ```

4. **查看结果**：评分结果保存在 `evals/output/grading.json`

### 关键设计决策

**为什么使用 `collect_output_files` 而非 `collect_output`：**

这是文件生成型 skill，核心输出是 `api-spec.yaml` 文件而非对话文本。`collect_output_files()` 返回 `{相对路径: 内容}` 的字典，使得 `grade_eval_N(files)` 可以精确定位和检查特定文件。

**YAML 文件查找策略（`find_yaml_spec`）：**

1. 精确匹配 `api-spec.yaml`
2. 回退匹配 `api-spec.yml`
3. 回退匹配任意 `.yaml/.yml` 文件
4. 最后回退：从 `response.md` 中提取 YAML 代码块

这种分层回退确保即使 skill 没有严格按照文件名约定输出，评分仍然能够工作。

### 评分维度说明

| 维度 | 权重 | 衡量内容 |
|------|------|---------|
| file_generation | 25% | 是否生成了 api-spec.yaml 文件 |
| openapi_compliance | 30% | 是否符合 OpenAPI 3.0 结构（openapi/info/paths/components） |
| endpoint_accuracy | 25% | 端点路径和 HTTP 方法是否与需求一致 |
| schema_quality | 10% | 数据模型定义是否合理 |
| boundary_handling | 10% | 模糊输入和极简需求的处理 |

### 5 个 eval 设计总结

| eval | 类型 | 核心验证点 | 断言数 | 总分 |
|------|------|---------|--------|------|
| eval-1 | 基本路径 | 用户 CRUD 的完整 OpenAPI 生成 | 8 | 57 |
| eval-2 | 领域变体 | 多资源端点 + enum 约束 | 8 | 49 |
| eval-3 | 领域跨越 | IoT 传感器 API（非典型领域） | 7 | 43 |
| eval-4 | 模糊输入 | 无触发词时自动识别意图 | 6 | 42 |
| eval-5 | 边界降级 | 极简单端点的完整结构保持 | 6 | 41 |
