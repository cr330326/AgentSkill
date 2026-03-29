# Skill Eval Writer — 为 data-migration-planner 编写测试用例

## 第一步：阅读目标 skill 分析

### 目标 skill 核心信息

| 属性 | 分析结果 |
|------|---------|
| **输入格式** | 源表结构 + 目标表结构（SQL DDL 或自然语言描述） |
| **输出格式** | 分阶段 Markdown 报告，每阶段完成后暂停等待确认 |
| **必须出现的输出元素** | 阶段进度标记、差异报告（阶段1）、ALTER TABLE/CREATE TABLE + 风险等级（阶段2）、回滚 SQL + 检查清单（阶段3） |
| **分支逻辑** | 3 阶段串行执行，每阶段后暂停；不同变更类型（新增/删除/修改字段）走不同 SQL 路径 |
| **边界** | 源表和目标表 schema 完全相同（无变更需要）；不兼容的类型变更（如 TEXT→INT 有数据损失风险） |

### 核心规则清单

1. 阶段 1：接收源/目标表结构 → 对比差异 → 输出差异报告 → **暂停**
2. 阶段 2：生成 ALTER TABLE / CREATE TABLE 语句 → 生成 INSERT...SELECT 数据迁移 DML → 标注风险等级（高/中/低） → **暂停**
3. 阶段 3：为每条迁移 SQL 生成回滚语句 → 生成 rollback.sql → 输出执行检查清单
4. **关键行为约束**：每个阶段完成后必须暂停，不自动进入下一阶段

### 关键特征：多阶段暂停型 skill

- 输出类型：文本对话（不生成独立文件），使用 `collect_output()` + `grade_eval_N(content: str)`
- 需要 `check_checkpoint()` 验证暂停行为（阶段完成后不泄漏后续内容）
- 需要 `check_progress_indicator()` 检查阶段进度标记
- 需要 `check_sql_keywords()` 检查 SQL DDL/DML 关键词
- 需要自定义 `check_risk_levels()` 检查风险等级标注

---

## 第二步：设计 5 个 eval 用例

| 槽位 | 名称 | 设计意图 |
|------|------|---------|
| eval-1 | **基本路径：用户表新增字段** | 源表 users(id, name, email)，目标表新增 phone、avatar_url、is_active、updated_at。验证阶段 1 差异分析的完整性和暂停行为 |
| eval-2 | **领域变体：订单表复合变更** | 涉及类型变更（INT→BIGINT）、删除字段、新增字段、ENUM 变更、新增索引，验证阶段 2 的 SQL 生成和风险标注 |
| eval-3 | **领域跨越：多表外键关联迁移** | 三张表 users/products/orders 有外键关联，id 从 INT→BIGINT 需级联处理，验证跨表依赖分析能力 |
| eval-4 | **模糊/自动检测：用户不使用迁移关键词** | 用户说"我想把旧表改成新结构"，不用"数据迁移"/"migration"触发词，验证意图识别 |
| eval-5 | **边界/降级：源表目标表完全相同** | 两表 schema 完全一致，验证 skill 是否正确识别无变更并优雅降级，不编造差异 |

---

## 第三步 & 第四步：evals.json

```json
{
  "skill_name": "data-migration-planner",
  "version": "1.0",
  "description": "验证 data-migration-planner skill 能否正确分析 schema 差异、生成迁移 SQL 和回滚方案，并在每个阶段后正确暂停等待确认",
  "scoring": {
    "total_points": 100,
    "dimensions": {
      "stage_control": {
        "weight": 30,
        "description": "是否正确执行分阶段流程，每阶段后暂停等待确认，不泄漏后续阶段内容"
      },
      "schema_analysis": {
        "weight": 25,
        "description": "阶段 1 差异分析是否准确完整——新增/删除/修改的字段是否全部识别"
      },
      "sql_quality": {
        "weight": 25,
        "description": "阶段 2 生成的 SQL 是否合法，风险等级标注是否合理"
      },
      "rollback_safety": {
        "weight": 10,
        "description": "阶段 3 回滚方案是否完整，检查清单是否可操作"
      },
      "boundary_handling": {
        "weight": 10,
        "description": "对无变更场景、模糊输入等边界情况的处理质量"
      }
    }
  },
  "evals": [
    {
      "id": 1,
      "name": "basic-add-columns",
      "prompt": "请帮我做数据迁移规划。\n\n源表结构：\n```sql\nCREATE TABLE users (\n  id INT PRIMARY KEY AUTO_INCREMENT,\n  name VARCHAR(100) NOT NULL,\n  email VARCHAR(255) UNIQUE NOT NULL,\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n```\n\n目标表结构：\n```sql\nCREATE TABLE users (\n  id INT PRIMARY KEY AUTO_INCREMENT,\n  name VARCHAR(100) NOT NULL,\n  email VARCHAR(255) UNIQUE NOT NULL,\n  phone VARCHAR(20),\n  avatar_url VARCHAR(500),\n  is_active BOOLEAN DEFAULT true,\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP\n);\n```\n\n请分析差异并给出迁移方案。",
      "expected_output": "阶段 1 输出差异报告：新增 phone、avatar_url、is_active、updated_at 四个字段。然后暂停等待确认。不应包含阶段 2 的 ALTER TABLE SQL 或阶段 3 的回滚方案。",
      "assertions": [
        {
          "id": "A1-01",
          "text": "输出包含阶段进度标记（如 [阶段 1/3] 或 阶段 1）",
          "type": "structural",
          "points": 7
        },
        {
          "id": "A1-02",
          "text": "识别出需要新增 phone 字段",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-03",
          "text": "识别出需要新增 avatar_url 字段",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-04",
          "text": "识别出需要新增 is_active 字段",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-05",
          "text": "识别出需要新增 updated_at 字段",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-06",
          "text": "阶段 1 完成后暂停，提示等待用户确认",
          "type": "checkpoint",
          "points": 10
        },
        {
          "id": "A1-07",
          "text": "阶段 1 后不包含 ALTER TABLE 语句（不泄漏阶段 2 内容）",
          "type": "checkpoint",
          "points": 8
        }
      ]
    },
    {
      "id": 2,
      "name": "complex-multi-change-types",
      "prompt": "数据库迁移规划需求。\n\n源表：\n```sql\nCREATE TABLE orders (\n  id INT PRIMARY KEY,\n  user_id INT NOT NULL,\n  product_name VARCHAR(100),\n  amount DECIMAL(8,2),\n  status VARCHAR(20) DEFAULT 'pending',\n  notes TEXT,\n  created_at TIMESTAMP\n);\n```\n\n目标表：\n```sql\nCREATE TABLE orders (\n  id BIGINT PRIMARY KEY,\n  user_id INT NOT NULL,\n  product_id INT NOT NULL,\n  quantity INT DEFAULT 1,\n  unit_price DECIMAL(10,2),\n  total_amount DECIMAL(12,2),\n  status ENUM('pending','paid','shipped','delivered','cancelled') DEFAULT 'pending',\n  shipping_address TEXT,\n  created_at TIMESTAMP,\n  updated_at TIMESTAMP,\n  INDEX idx_user_id (user_id),\n  INDEX idx_status (status)\n);\n```\n\n变更包括：id 从 INT 改为 BIGINT，删除 product_name 和 notes，新增 product_id/quantity/unit_price/total_amount/shipping_address/updated_at，status 从 VARCHAR 改为 ENUM，新增两个索引。\n\n请完成阶段 1 和阶段 2（假设阶段 1 用户已确认）。",
      "expected_output": "阶段 1 差异报告列出所有变更。阶段 2 生成 ALTER TABLE 语句，每条标注风险等级：id 类型变更为高风险，删除字段为中风险，新增字段为低风险。阶段 2 完成后暂停。",
      "assertions": [
        {
          "id": "A2-01",
          "text": "识别 id 字段从 INT 变为 BIGINT 的类型变更",
          "type": "content",
          "points": 8
        },
        {
          "id": "A2-02",
          "text": "识别需要删除 product_name 字段",
          "type": "content",
          "points": 6
        },
        {
          "id": "A2-03",
          "text": "生成包含 ALTER TABLE 的 SQL 语句",
          "type": "content",
          "points": 8
        },
        {
          "id": "A2-04",
          "text": "包含风险等级标注（高/中/低 或 high/medium/low）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A2-05",
          "text": "id 类型变更标注为高风险",
          "type": "content",
          "points": 6
        },
        {
          "id": "A2-06",
          "text": "阶段 2 完成后暂停，不包含回滚 SQL（不泄漏阶段 3 内容）",
          "type": "checkpoint",
          "points": 8
        },
        {
          "id": "A2-07",
          "text": "包含数据迁移 DML（INSERT...SELECT 或 UPDATE 语句）",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 3,
      "name": "multi-table-foreign-key",
      "prompt": "schema 变更规划。涉及多张关联表：\n\n源表：\n```sql\nCREATE TABLE users (\n  id INT PRIMARY KEY,\n  username VARCHAR(50)\n);\n\nCREATE TABLE products (\n  id INT PRIMARY KEY,\n  name VARCHAR(100),\n  price DECIMAL(8,2)\n);\n\nCREATE TABLE orders (\n  id INT PRIMARY KEY,\n  user_id INT REFERENCES users(id),\n  product_id INT REFERENCES products(id),\n  quantity INT\n);\n```\n\n目标表：\n```sql\nCREATE TABLE users (\n  id BIGINT PRIMARY KEY,\n  username VARCHAR(50),\n  email VARCHAR(255)\n);\n\nCREATE TABLE products (\n  id BIGINT PRIMARY KEY,\n  name VARCHAR(200),\n  price DECIMAL(10,2),\n  category VARCHAR(50)\n);\n\nCREATE TABLE orders (\n  id BIGINT PRIMARY KEY,\n  user_id BIGINT REFERENCES users(id),\n  product_id BIGINT REFERENCES products(id),\n  quantity INT,\n  total DECIMAL(10,2)\n);\n```\n\n注意外键约束的迁移顺序。请完成阶段 1。",
      "expected_output": "阶段 1 分析三张表的差异。关键点：识别 id 类型变更涉及外键级联影响，指出迁移顺序需要先改 users 和 products，再改 orders（因为 orders 的外键指向前两张表）。暂停等待确认。",
      "assertions": [
        {
          "id": "A3-01",
          "text": "分析了三张表（users、products、orders）的差异",
          "type": "content",
          "points": 8
        },
        {
          "id": "A3-02",
          "text": "识别了外键约束对迁移顺序的影响",
          "type": "content",
          "points": 10
        },
        {
          "id": "A3-03",
          "text": "提及迁移顺序或依赖关系（应先改被引用的表）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A3-04",
          "text": "识别 id 从 INT 变为 BIGINT 且外键也需要同步变更",
          "type": "content",
          "points": 7
        },
        {
          "id": "A3-05",
          "text": "阶段 1 完成后暂停等待确认",
          "type": "checkpoint",
          "points": 7
        },
        {
          "id": "A3-06",
          "text": "包含阶段进度标记",
          "type": "structural",
          "points": 5
        }
      ]
    },
    {
      "id": 4,
      "name": "fuzzy-input-no-trigger-words",
      "prompt": "我有一个旧数据库的表，想改成新的结构，你帮我看看：\n\n现在的表：\n```sql\nCREATE TABLE articles (\n  id INT PRIMARY KEY,\n  title VARCHAR(200),\n  body TEXT,\n  author VARCHAR(100),\n  created DATE\n);\n```\n\n我想改成这样：\n```sql\nCREATE TABLE articles (\n  id INT PRIMARY KEY,\n  title VARCHAR(300),\n  body TEXT,\n  author_id INT,\n  summary VARCHAR(500),\n  tags JSON,\n  published_at DATETIME,\n  created_at DATETIME,\n  updated_at DATETIME\n);\n```\n\n帮我看看要怎么改。",
      "expected_output": "即使用户没有说"数据迁移"或"migration"，skill 应识别出这是数据库 schema 变更场景，输出阶段 1 的差异分析。应识别：title 长度变更、author→author_id（语义变更）、删除 created、新增 summary/tags/published_at/created_at/updated_at。",
      "assertions": [
        {
          "id": "A4-01",
          "text": "识别出这是数据库 schema 变更场景（即使用户未使用迁移/migration 关键词）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A4-02",
          "text": "识别 title 字段长度从 VARCHAR(200) 变为 VARCHAR(300)",
          "type": "content",
          "points": 6
        },
        {
          "id": "A4-03",
          "text": "识别 author 字段变更为 author_id（语义变更或删除+新增）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A4-04",
          "text": "识别需要新增 tags（JSON 类型）字段",
          "type": "content",
          "points": 5
        },
        {
          "id": "A4-05",
          "text": "输出包含阶段标记",
          "type": "structural",
          "points": 5
        },
        {
          "id": "A4-06",
          "text": "阶段 1 完成后暂停等待确认",
          "type": "checkpoint",
          "points": 7
        }
      ]
    },
    {
      "id": 5,
      "name": "boundary-no-changes-needed",
      "prompt": "请分析以下数据库迁移需求：\n\n源表：\n```sql\nCREATE TABLE config (\n  id INT PRIMARY KEY,\n  key VARCHAR(100) UNIQUE NOT NULL,\n  value TEXT,\n  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n```\n\n目标表：\n```sql\nCREATE TABLE config (\n  id INT PRIMARY KEY,\n  key VARCHAR(100) UNIQUE NOT NULL,\n  value TEXT,\n  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n```\n\n请开始阶段 1 分析。",
      "expected_output": "阶段 1 应正确识别源表和目标表 schema 完全相同，无需迁移。不应凭空编造差异，应明确告知用户无变更需要，可以跳过后续阶段。",
      "assertions": [
        {
          "id": "A5-01",
          "text": "正确识别源表和目标表 schema 相同，无需变更",
          "type": "content",
          "points": 12
        },
        {
          "id": "A5-02",
          "text": "没有凭空编造不存在的差异",
          "type": "content",
          "points": 10
        },
        {
          "id": "A5-03",
          "text": "建议跳过后续阶段或告知无需迁移",
          "type": "content",
          "points": 8
        },
        {
          "id": "A5-04",
          "text": "仍然保持阶段结构（有阶段标记），展示了专业的分析流程",
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
data-migration-planner 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出）。

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


# ── 多阶段 skill 专用检查函数 ──


def check_progress_indicator(content: str) -> tuple[bool, str]:
    """检查是否有阶段进度标记（如 [阶段 1/3]、阶段 1、Stage 1、Step 1）。"""
    patterns = [
        r"\[阶段\s*\d+\s*/\s*\d+\]",
        r"\[Stage\s*\d+\s*/\s*\d+\]",
        r"\[Step\s*\d+\s*/\s*\d+\]",
        r"第\s*\d+\s*[步阶段]",
        r"阶段\s*\d+",
        r"Stage\s*\d+",
        r"Phase\s*\d+",
        r"##\s*阶段",
        r"##\s*Stage",
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend(matches[:3])
    passed = len(found) > 0
    evidence = f"进度标记: {found[:5]}" if found else "未找到进度标记"
    return passed, evidence


def check_checkpoint(
    content: str, stop_keyword: str, forbidden_keywords: list[str]
) -> tuple[bool, str]:
    """检查输出是否在指定点暂停，不包含后续阶段的内容。

    stop_keyword: 应该出现的暂停标记（如"等待确认"）
    forbidden_keywords: 不应出现的后续阶段关键词
    """
    has_stop = stop_keyword.lower() in content.lower()
    leaked = [kw for kw in forbidden_keywords if kw.lower() in content.lower()]
    if has_stop and len(leaked) == 0:
        passed = True
        evidence = f"暂停标记=True; 正确未包含后续内容"
    elif has_stop and len(leaked) > 0:
        passed = False
        evidence = f"暂停标记=True; 但泄漏了后续内容: {leaked}"
    else:
        # 没有显式暂停标记，检查宽松匹配
        pause_variants = ["等待", "确认", "暂停", "pause", "confirm", "继续",
                          "请确认", "是否继续", "确认后", "回复后"]
        has_pause = any(v.lower() in content.lower() for v in pause_variants)
        if has_pause and len(leaked) == 0:
            passed = True
            evidence = f"找到暂停变体; 正确未包含后续内容"
        elif has_pause and len(leaked) > 0:
            passed = False
            evidence = f"找到暂停变体; 但泄漏了后续内容: {leaked}"
        else:
            passed = False
            evidence = f"未找到暂停标记 '{stop_keyword}'; 泄漏: {leaked}"
    return passed, evidence


def check_sql_keywords(
    content: str, sql_keywords: list[str], min_hits: int
) -> tuple[bool, str]:
    """检查内容是否包含 SQL 关键词（大小写不敏感）。"""
    found = [kw for kw in sql_keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"SQL 关键词命中 {len(found)}/{len(sql_keywords)}: {found}"
    return passed, evidence


def check_risk_levels(content: str) -> tuple[bool, str]:
    """检查是否包含风险等级标注（至少 2 个不同等级）。"""
    risk_patterns = [
        r"高\s*风险|high\s*risk|critical|严重",
        r"中\s*风险|medium\s*risk|moderate|注意",
        r"低\s*风险|low\s*risk|minor|安全",
    ]
    found_levels = []
    for i, pat in enumerate(risk_patterns):
        if re.search(pat, content, re.IGNORECASE):
            found_levels.append(["高", "中", "低"][i])
    passed = len(found_levels) >= 2
    evidence = f"找到风险等级: {found_levels}"
    return passed, evidence


def check_field_mentioned(content: str, field_name: str) -> tuple[bool, str]:
    """检查是否提到了特定字段名。"""
    found = field_name.lower() in content.lower()
    evidence = f"{'找到' if found else '未找到'} 字段 '{field_name}'"
    return found, evidence


def check_no_fabricated_changes(content: str) -> tuple[bool, str]:
    """检查输出是否没有凭空编造差异（用于无变更场景）。"""
    # 如果明确说无变更/无差异/相同，则判断没有编造
    no_change_kw = ["无变更", "无差异", "无需", "不需要", "相同", "一致",
                     "no change", "identical", "no difference", "没有差异",
                     "没有变更", "不需要迁移", "完全相同", "一样", "无需迁移"]
    has_no_change = any(kw.lower() in content.lower() for kw in no_change_kw)
    if has_no_change:
        return True, "明确指出无变更，未编造差异"

    # 如果出现了变更关键词但没有无变更声明，可能编造了差异
    change_kw = ["新增", "删除", "修改", "变更字段", "添加字段", "移除",
                 "ADD COLUMN", "DROP COLUMN", "MODIFY COLUMN"]
    has_changes = any(kw.lower() in content.lower() for kw in change_kw)
    if has_changes:
        return False, "出现了变更相关关键词，可能编造了不存在的差异"

    return True, "未出现变更相关关键词"


# ═════════════════════════════════════════════
# 每个 eval 的专属检查逻辑
# ═════════════════════════════════════════════


def grade_eval_1(content: str) -> list[dict]:
    """eval-1: 基本路径 — 用户表添加字段（阶段 1）"""
    results = []

    # A1-01: 阶段进度标记
    passed, evidence = check_progress_indicator(content)
    results.append({
        "id": "A1-01",
        "text": "输出包含阶段进度标记",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-02: 识别 phone 字段
    passed, evidence = check_field_mentioned(content, "phone")
    results.append({
        "id": "A1-02",
        "text": "识别出需要新增 phone 字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-03: 识别 avatar_url 字段
    passed = "avatar_url" in content.lower() or "avatar" in content.lower()
    evidence = f"avatar_url/avatar 出现: {passed}"
    results.append({
        "id": "A1-03",
        "text": "识别出需要新增 avatar_url 字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-04: 识别 is_active 字段
    passed, evidence = check_field_mentioned(content, "is_active")
    results.append({
        "id": "A1-04",
        "text": "识别出需要新增 is_active 字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-05: 识别 updated_at 字段
    passed, evidence = check_field_mentioned(content, "updated_at")
    results.append({
        "id": "A1-05",
        "text": "识别出需要新增 updated_at 字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-06: 阶段 1 完成后暂停
    passed, evidence = check_checkpoint(
        content,
        "确认",
        []  # 泄漏由 A1-07 单独检查
    )
    results.append({
        "id": "A1-06",
        "text": "阶段 1 完成后暂停，提示等待用户确认",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-07: 不泄漏阶段 2 内容（不包含 ALTER TABLE）
    alter_leaked = bool(re.search(r"ALTER\s+TABLE", content, re.IGNORECASE))
    # 允许在差异报告中引用原始的 CREATE TABLE，但不应有 ALTER TABLE
    passed = not alter_leaked
    evidence = f"ALTER TABLE 泄漏={alter_leaked}"
    results.append({
        "id": "A1-07",
        "text": "阶段 1 后不包含 ALTER TABLE 语句",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_2(content: str) -> list[dict]:
    """eval-2: 领域变体 — 订单表多种变更（阶段 1+2）"""
    results = []

    # A2-01: 识别 id 从 INT 变为 BIGINT
    passed = False
    evidence = "未找到 INT→BIGINT 变更描述"
    if "bigint" in content.lower():
        p1, _ = check_proximity(content, "id", "BIGINT", 100)
        p2, _ = check_proximity(content, "INT", "BIGINT", 100)
        passed = p1 or p2
        if passed:
            evidence = "识别了 id 字段的 INT→BIGINT 类型变更"
    results.append({
        "id": "A2-01",
        "text": "识别 id 字段从 INT 变为 BIGINT",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-02: 识别删除 product_name
    delete_kw = ["删除", "移除", "drop", "remove", "去掉"]
    passed = False
    evidence = "未找到 product_name 删除描述"
    if "product_name" in content.lower():
        for dk in delete_kw:
            p, e = check_proximity(content, "product_name", dk, 80)
            if p:
                passed = True
                evidence = e
                break
        if not passed:
            # 宽松：至少提到了 product_name
            passed = True
            evidence = "提到了 product_name（宽松匹配）"
    results.append({
        "id": "A2-02",
        "text": "识别需要删除 product_name 字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-03: 生成 ALTER TABLE SQL
    passed, evidence = check_sql_keywords(
        content, ["ALTER TABLE", "ALTER"], 1
    )
    results.append({
        "id": "A2-03",
        "text": "生成包含 ALTER TABLE 的 SQL 语句",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-04: 包含风险等级标注
    passed, evidence = check_risk_levels(content)
    results.append({
        "id": "A2-04",
        "text": "包含风险等级标注（高/中/低）",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-05: id 类型变更标注为高风险
    passed = False
    evidence = "未找到 id 变更与高风险的关联"
    high_risk_kw = ["高风险", "high risk", "高", "critical", "dangerous"]
    for hk in high_risk_kw:
        p1, e1 = check_proximity(content, "BIGINT", hk, 150)
        p2, e2 = check_proximity(content, "id", hk, 200)
        if p1 or p2:
            passed = True
            evidence = e1 if p1 else e2
            break
    results.append({
        "id": "A2-05",
        "text": "id 类型变更标注为高风险",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-06: 阶段 2 后暂停，不泄漏阶段 3（回滚）内容
    rollback_kw = ["回滚", "rollback", "ROLLBACK", "回退", "undo"]
    leaked = [kw for kw in rollback_kw if kw.lower() in content.lower()]
    pause_kw = ["确认", "暂停", "等待", "confirm", "pause"]
    has_pause = any(pk.lower() in content.lower() for pk in pause_kw)
    passed = has_pause and len(leaked) == 0
    if not has_pause and len(leaked) == 0:
        passed = True  # 没有泄漏也算通过（暂停表述可能不同）
    evidence = f"暂停={has_pause}; 回滚泄漏={leaked}"
    results.append({
        "id": "A2-06",
        "text": "阶段 2 完成后暂停，不泄漏阶段 3 内容",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-07: 包含数据迁移 DML
    dml_kw = ["INSERT", "SELECT", "UPDATE", "DML", "数据迁移", "数据转移"]
    passed, evidence = check_keywords(content, dml_kw, 1)
    results.append({
        "id": "A2-07",
        "text": "包含数据迁移 DML",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_3(content: str) -> list[dict]:
    """eval-3: 领域跨越 — 多表关联迁移"""
    results = []

    # A3-01: 分析了三张表
    table_names = ["users", "products", "orders"]
    found_tables = [t for t in table_names if t.lower() in content.lower()]
    passed = len(found_tables) >= 3
    evidence = f"找到表名: {found_tables}"
    results.append({
        "id": "A3-01",
        "text": "分析了三张表的差异",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-02: 识别外键约束的影响
    fk_kw = ["外键", "foreign key", "REFERENCES", "引用", "关联",
             "依赖", "约束", "constraint"]
    passed, evidence = check_keywords(content, fk_kw, 1)
    results.append({
        "id": "A3-02",
        "text": "识别了外键约束对迁移顺序的影响",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-03: 提及迁移顺序或依赖关系
    order_kw = ["顺序", "先", "后", "依赖", "order", "sequence",
                "before", "after", "first", "then", "优先",
                "级联", "cascade"]
    passed, evidence = check_keywords(content, order_kw, 1)
    results.append({
        "id": "A3-03",
        "text": "提及迁移顺序或依赖关系",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-04: 识别 INT→BIGINT 且外键同步变更
    has_bigint = "bigint" in content.lower()
    has_fk_sync = False
    sync_kw = ["同步", "一起", "同时", "级联", "cascade",
               r"外键.*变更", r"引用.*更新"]
    for sk in sync_kw:
        if re.search(sk, content, re.IGNORECASE | re.DOTALL):
            has_fk_sync = True
            break
    # 宽松：只要提到了 BIGINT 和外键相关词
    if not has_fk_sync and has_bigint:
        fk_words = ["外键", "foreign key", "REFERENCES"]
        for fkw in fk_words:
            p, _ = check_proximity(content, "BIGINT", fkw, 200)
            if p:
                has_fk_sync = True
                break
    passed = has_bigint and has_fk_sync
    evidence = f"BIGINT={has_bigint}, 外键同步={has_fk_sync}"
    results.append({
        "id": "A3-04",
        "text": "识别 id 变更需要外键同步",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-05: 阶段 1 暂停
    passed, evidence = check_checkpoint(
        content, "确认",
        ["ALTER TABLE"]  # 阶段 1 不应包含 ALTER TABLE
    )
    results.append({
        "id": "A3-05",
        "text": "阶段 1 完成后暂停等待确认",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-06: 阶段进度标记
    passed, evidence = check_progress_indicator(content)
    results.append({
        "id": "A3-06",
        "text": "包含阶段进度标记",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_4(content: str) -> list[dict]:
    """eval-4: 模糊输入 — 用户未使用迁移关键词"""
    results = []

    # A4-01: 识别出 schema 变更场景
    migration_kw = ["迁移", "migration", "变更", "差异", "分析",
                    "对比", "schema", "字段", "ALTER", "阶段"]
    passed, evidence = check_keywords(content, migration_kw, 2)
    results.append({
        "id": "A4-01",
        "text": "识别出数据库 schema 变更场景",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-02: 识别 title VARCHAR(200)→VARCHAR(300)
    passed = False
    evidence = "未找到 title 长度变更描述"
    if "title" in content.lower():
        len_kw = ["200", "300", "VARCHAR", "长度", "length"]
        for lk in len_kw:
            p, e = check_proximity(content, "title", lk, 100)
            if p:
                passed = True
                evidence = e
                break
    results.append({
        "id": "A4-02",
        "text": "识别 title 字段长度变更",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-03: 识别 author→author_id 变更
    has_author = "author" in content.lower()
    has_author_id = "author_id" in content.lower()
    passed = has_author and has_author_id
    evidence = f"author={has_author}, author_id={has_author_id}"
    results.append({
        "id": "A4-03",
        "text": "识别 author→author_id 变更",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-04: 识别 tags JSON 字段
    has_tags = "tags" in content.lower()
    has_json = "json" in content.lower()
    passed = has_tags and has_json
    evidence = f"tags={has_tags}, JSON={has_json}"
    results.append({
        "id": "A4-04",
        "text": "识别需要新增 tags（JSON 类型）字段",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-05: 阶段标记
    passed, evidence = check_progress_indicator(content)
    results.append({
        "id": "A4-05",
        "text": "输出包含阶段标记",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-06: 暂停等待确认
    passed, evidence = check_checkpoint(
        content, "确认", ["ALTER TABLE"]
    )
    results.append({
        "id": "A4-06",
        "text": "阶段 1 完成后暂停等待确认",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_5(content: str) -> list[dict]:
    """eval-5: 边界 — 源表和目标表完全相同"""
    results = []

    # A5-01: 正确识别无变更
    no_change_kw = ["无变更", "无差异", "无需", "不需要", "相同", "一致",
                     "no change", "identical", "no difference", "没有差异",
                     "没有变更", "不需要迁移", "完全相同", "一样", "无需迁移"]
    passed, evidence = check_keywords(content, no_change_kw, 1)
    results.append({
        "id": "A5-01",
        "text": "正确识别 schema 相同，无需变更",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-02: 没有编造差异
    passed, evidence = check_no_fabricated_changes(content)
    results.append({
        "id": "A5-02",
        "text": "没有凭空编造不存在的差异",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-03: 建议跳过后续阶段
    skip_kw = ["跳过", "无需继续", "不需要", "skip", "无需执行",
               "可以省略", "不用", "完成", "无后续"]
    passed, evidence = check_keywords(content, skip_kw, 1)
    if not passed:
        # 宽松匹配：只要表达了"不需要迁移"的意思
        no_migrate_kw = ["无需迁移", "不需要迁移", "无变更", "no migration"]
        passed, evidence = check_keywords(content, no_migrate_kw, 1)
    results.append({
        "id": "A5-03",
        "text": "建议跳过后续阶段或告知无需迁移",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-04: 仍保持阶段结构
    passed, evidence = check_progress_indicator(content)
    results.append({
        "id": "A5-04",
        "text": "仍然保持阶段结构",
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
        "skill_name": "data-migration-planner",
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
   - 将 data-migration-planner 的 SKILL.md 注入 subagent 的 system prompt
   - 将 eval 的 `prompt` 字段作为用户输入
   - 将输出保存到 `evals/output/eval-N/response.md`
   - **重要**：eval-1/3/4/5 只需要执行到阶段 1 暂停。eval-2 的 prompt 明确说"假设阶段 1 用户已确认"，所以应执行到阶段 2 暂停。

3. **运行评分**：
   ```bash
   python3 evals/grade.py evals/output
   ```

4. **查看结果**：评分结果保存在 `evals/output/grading.json`

### 关键设计决策

**为什么使用 `collect_output` 而非 `collect_output_files`：**

这是文本输出型 skill（输出结构化对话报告，不生成独立文件）。虽然阶段 3 提到生成 rollback.sql，但 eval 的主要验证对象是对话输出中的报告内容，所以使用文本拼接模式。

**暂停行为验证策略（`check_checkpoint`）：**

- 检查是否有暂停标记（"等待确认"、"请确认"等）
- 检查是否泄漏了后续阶段的内容（如阶段 1 不应有 ALTER TABLE，阶段 2 不应有回滚/rollback）
- 宽松匹配多种暂停表述变体（等待、确认、暂停、pause、confirm 等）

**风险等级验证（`check_risk_levels`）：**

同时检查中文和英文的风险等级表述。要求至少出现 2 个不同等级（因为合理的迁移方案应包含多种风险级别）。

**边界场景验证（eval-5 `check_no_fabricated_changes`）：**

当源表和目标表 schema 完全相同时，检查输出是否明确声明"无变更"，并且没有凭空编造差异——这是 AI 常见的幻觉问题。

### 评分维度说明

| 维度 | 权重 | 衡量内容 |
|------|------|---------|
| stage_control | 30% | 分阶段执行 + 暂停行为 + 不泄漏后续内容 |
| schema_analysis | 25% | 差异分析的准确性和完整性 |
| sql_quality | 25% | SQL 语句质量和风险标注 |
| rollback_safety | 10% | 回滚方案的完整性 |
| boundary_handling | 10% | 无变更/模糊输入等边界场景处理 |

### 5 个 eval 设计总结

| eval | 类型 | 核心验证点 | 断言数 | 总分 |
|------|------|---------|--------|------|
| eval-1 | 基本路径 | 阶段 1 差异分析 + 暂停 | 7 | 51 |
| eval-2 | 领域变体 | 多变更类型 + SQL 生成 + 风险标注 | 7 | 49 |
| eval-3 | 领域跨越 | 多表外键依赖分析 | 6 | 45 |
| eval-4 | 模糊输入 | 无触发词时自动识别意图 | 6 | 39 |
| eval-5 | 边界降级 | 无变更场景的优雅处理 | 4 | 35 |
