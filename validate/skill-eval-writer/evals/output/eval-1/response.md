# Skill Eval Writer — 为 commit-message-reviewer 编写测试用例

## 第一步：阅读目标 skill 分析

### 目标 skill 核心信息

| 属性 | 分析结果 |
|------|---------|
| **输入格式** | Git commit message 文本，单条或多条 |
| **输出格式** | 结构化审查报告（Markdown） |
| **必须出现的输出元素** | 总览（合格数/总数）、每条不合格 commit 的问题描述、改写建议 |
| **分支逻辑** | 单条 vs 多条 commit；全部合格 vs 存在不合格 |
| **边界** | 非 commit message 的输入；已经完全合规的 commit |

### 核心规则清单

1. 格式规则：`type(scope): description`
2. type 限定：feat / fix / docs / style / refactor / test / chore（共 7 种）
3. description 首字母小写
4. description 不以句号结尾
5. body 和 footer 用空行分隔
6. 输出包含总览统计（合格数/总数）
7. 每条不合格 commit 需要给出问题描述 + 改写建议

---

## 第二步：设计 5 个 eval 用例

| 槽位 | 名称 | 设计意图 |
|------|------|---------|
| eval-1 | **基本路径：混合合规/不合规** | 3 条 commit，2 条有明显格式错误，1 条合规。验证完整审查流程 |
| eval-2 | **领域变体：含 body/footer 的多行 commit** | 包含多行 commit message（有 body 和 footer），验证空行分隔检查 |
| eval-3 | **领域跨越：全部合规** | 所有 commit 都符合规范，验证 skill 能正确识别并给出"全部通过"结论 |
| eval-4 | **模糊输入：用户没说"审查 commit"** | 用户只说"帮我看看这些提交信息写得怎么样"，不使用触发关键词 |
| eval-5 | **边界/降级：非 commit message 输入** | 输入是一段普通文本或代码变更描述，不是 commit message 格式 |

---

## 第三步 & 第四步：evals.json

```json
{
  "skill_name": "commit-message-reviewer",
  "version": "1.0",
  "description": "验证 commit-message-reviewer skill 能否正确审查 git commit message 的 Conventional Commits 规范合规性，输出结构化报告并给出改写建议",
  "scoring": {
    "total_points": 100,
    "dimensions": {
      "core_detection": {
        "weight": 30,
        "description": "能否正确识别 commit message 中的格式错误（type 不合法、大小写、句号等）"
      },
      "report_structure": {
        "weight": 25,
        "description": "输出是否包含总览统计、问题列表、改写建议等结构化元素"
      },
      "rewrite_quality": {
        "weight": 20,
        "description": "改写建议是否符合 Conventional Commits 规范"
      },
      "rule_coverage": {
        "weight": 15,
        "description": "是否覆盖了所有规则（type 校验、首字母、句号、空行分隔）"
      },
      "boundary_handling": {
        "weight": 10,
        "description": "对全部合规、模糊输入、非 commit 输入等边界场景的处理"
      }
    }
  },
  "evals": [
    {
      "id": 1,
      "name": "basic-mixed-commits",
      "prompt": "请帮我审查以下 3 条 commit message：\n\n1. `Update user login flow`\n2. `feat(auth): add OAuth2 support`\n3. `Fixed: bug in payment module.`\n\n请检查是否符合 Conventional Commits 规范。",
      "expected_output": "应输出审查报告：总览 1/3 合格。第 1 条缺少 type(scope): 格式，首字母大写。第 3 条 type 不合法（Fixed 不在允许列表），以句号结尾。第 2 条合格。对每条不合格 commit 给出改写建议。",
      "assertions": [
        {
          "id": "A1-01",
          "text": "输出包含总览统计（合格数/总数，应为 1/3）",
          "type": "structural",
          "points": 8
        },
        {
          "id": "A1-02",
          "text": "识别第 1 条 commit 缺少 type(scope): 格式",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-03",
          "text": "识别第 3 条 commit 的 type 不在允许列表中（Fixed 不是合法 type）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-04",
          "text": "识别第 3 条 commit 以句号结尾",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-05",
          "text": "确认第 2 条 commit 合格",
          "type": "content",
          "points": 6
        },
        {
          "id": "A1-06",
          "text": "为不合格 commit 提供改写建议",
          "type": "structural",
          "points": 7
        },
        {
          "id": "A1-07",
          "text": "改写建议中使用了合法的 type（feat/fix/docs/style/refactor/test/chore）",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 2,
      "name": "multiline-body-footer",
      "prompt": "审查这两条 commit message 是否规范：\n\n第一条：\n```\nfeat(api): add rate limiting\nAdded rate limiting to prevent abuse.\nRefs: #1234\n```\n\n第二条：\n```\nfix(db): resolve connection pool leak\n\nThe connection pool was not properly releasing connections\nafter timeout. This caused gradual resource exhaustion.\n\nCloses #5678\n```",
      "expected_output": "第一条不合格：body 和 header 之间缺少空行分隔，footer 和 body 之间也缺少空行。第二条合格：格式正确，空行分隔规范。总览 1/2 合格。",
      "assertions": [
        {
          "id": "A2-01",
          "text": "输出包含总览统计（合格数/总数）",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A2-02",
          "text": "识别第一条 commit 的空行分隔问题",
          "type": "content",
          "points": 10
        },
        {
          "id": "A2-03",
          "text": "确认第二条 commit 合格或基本合规",
          "type": "content",
          "points": 7
        },
        {
          "id": "A2-04",
          "text": "提及 body 和 header 之间需要空行",
          "type": "content",
          "points": 8
        },
        {
          "id": "A2-05",
          "text": "为不合格 commit 提供改写建议",
          "type": "structural",
          "points": 6
        },
        {
          "id": "A2-06",
          "text": "改写建议中体现了正确的空行分隔格式",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 3,
      "name": "all-compliant-commits",
      "prompt": "帮我检查一下这几条提交信息有没有问题：\n\n1. `feat(user): add profile avatar upload`\n2. `fix(cart): correct quantity calculation`\n3. `docs(readme): update installation guide`\n4. `refactor(auth): extract token validation logic`",
      "expected_output": "所有 4 条 commit 均符合 Conventional Commits 规范。总览 4/4 合格。可附带最佳实践提示。不应凭空编造问题。",
      "assertions": [
        {
          "id": "A3-01",
          "text": "总览统计显示全部合格（4/4）",
          "type": "structural",
          "points": 10
        },
        {
          "id": "A3-02",
          "text": "没有给合规 commit 报告虚假问题（不含"不合格"或"不符合"等否定评价）",
          "type": "content",
          "points": 10
        },
        {
          "id": "A3-03",
          "text": "明确确认所有 commit 合规",
          "type": "content",
          "points": 8
        },
        {
          "id": "A3-04",
          "text": "可选：包含最佳实践提示或正面评价",
          "type": "content",
          "points": 4
        },
        {
          "id": "A3-05",
          "text": "仍然包含审查报告的基本结构（有总览/统计段落）",
          "type": "structural",
          "points": 5
        }
      ]
    },
    {
      "id": 4,
      "name": "fuzzy-input-no-trigger-words",
      "prompt": "看看这几个写得行不行：\n\n- `ADD new feature for dashboard`\n- `bugfix: resolve login timeout issue`\n- `chore(deps): bump lodash to 4.17.21`",
      "expected_output": "即使用户没有明确说'审查 commit message'，skill 应识别出这些是 commit message 并进行规范检查。第 1 条：type 不合法（ADD 不在列表）且首字母大写。第 2 条：bugfix 不是合法 type（应为 fix），缺少 scope 括号格式。第 3 条合格。总览 1/3。",
      "assertions": [
        {
          "id": "A4-01",
          "text": "识别出输入是 commit message 并进行规范审查",
          "type": "content",
          "points": 8
        },
        {
          "id": "A4-02",
          "text": "识别 ADD 不是合法 type",
          "type": "content",
          "points": 7
        },
        {
          "id": "A4-03",
          "text": "识别 bugfix 不是合法 type（应为 fix）",
          "type": "content",
          "points": 7
        },
        {
          "id": "A4-04",
          "text": "确认第 3 条 chore(deps) 合规",
          "type": "content",
          "points": 6
        },
        {
          "id": "A4-05",
          "text": "输出包含总览统计",
          "type": "structural",
          "points": 5
        },
        {
          "id": "A4-06",
          "text": "提供改写建议",
          "type": "structural",
          "points": 5
        }
      ]
    },
    {
      "id": 5,
      "name": "boundary-non-commit-input",
      "prompt": "审查一下这个 commit message：\n\n```\n今天完成了用户模块的开发，主要包括：\n1. 登录功能\n2. 注册功能\n3. 密码重置\n\n明天计划做支付模块。\n```",
      "expected_output": "这段文字不是 commit message 格式（看起来是工作日志/日报）。skill 应该指出这不符合 Conventional Commits 的任何格式要求，建议将其拆分为多条规范的 commit message，并给出拆分和改写示例。",
      "assertions": [
        {
          "id": "A5-01",
          "text": "指出输入不符合 commit message 的基本格式",
          "type": "content",
          "points": 10
        },
        {
          "id": "A5-02",
          "text": "提到 Conventional Commits 格式要求（type(scope): description）",
          "type": "content",
          "points": 7
        },
        {
          "id": "A5-03",
          "text": "建议拆分为多条 commit 或给出改写示例",
          "type": "content",
          "points": 8
        },
        {
          "id": "A5-04",
          "text": "改写示例中使用了合法 type（feat/fix 等）",
          "type": "content",
          "points": 6
        },
        {
          "id": "A5-05",
          "text": "没有假装输入是合规的（不应给出"合格"评价）",
          "type": "content",
          "points": 7
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
commit-message-reviewer 评分脚本

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


def check_section_content(
    content: str, section_heading: str, keywords: list[str], min_hits: int = 1
) -> tuple[bool, str]:
    """提取指定 ## 标题下的内容段落，检查其中是否包含关键词。"""
    pattern = rf"## {re.escape(section_heading)}(.*?)(?=\n## [^#]|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if not m:
        return False, f"未找到 '## {section_heading}' 段落"
    section = m.group(1)
    found = [kw for kw in keywords if kw.lower() in section.lower()]
    passed = len(found) >= min_hits
    evidence = f"'{section_heading}' 段中命中 {len(found)}/{len(keywords)}: {found}"
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


def check_count_summary(content: str) -> tuple[bool, str]:
    """检查是否有数量统计（如"1/3 合格"或"合格数: 1"）。"""
    patterns = [
        r"\*{0,2}\d+\*{0,2}\s*/\s*\*{0,2}\d+\*{0,2}",  # 1/3 格式
        r"合格\D{0,5}\*{0,2}\d+\*{0,2}",
        r"\*{0,2}\d+\*{0,2}\s*条?\s*合格",
        r"通过\D{0,5}\*{0,2}\d+\*{0,2}",
        r"\*{0,2}\d+\*{0,2}\s*条?\s*通过",
        r"pass(ed)?\D{0,5}\*{0,2}\d+\*{0,2}",
        r"\*{0,2}\d+\*{0,2}\s*pass",
        r"共\s*\*{0,2}\d+\*{0,2}\s*条",
        r"总[计共]\D{0,5}\*{0,2}\d+\*{0,2}",
    ]
    found = []
    for pat in patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found.extend(matches[:2])
    passed = len(found) > 0
    evidence = f"找到统计: {found[:3]}" if found else "未找到数量统计"
    return passed, evidence


def check_count_ratio(content: str, expected_pass: int, expected_total: int) -> tuple[bool, str]:
    """检查是否包含特定的合格/总数比例（如 1/3）。"""
    # 匹配 N/M 格式，允许 bold 包裹
    pattern = rf"\*{{0,2}}{expected_pass}\*{{0,2}}\s*/\s*\*{{0,2}}{expected_total}\*{{0,2}}"
    m = re.search(pattern, content)
    if m:
        return True, f"找到比例 {expected_pass}/{expected_total}: '{m.group()}'"
    # 也检查中文表述
    patterns_cn = [
        rf"{expected_pass}\s*条?\s*合格.*{expected_total}\s*条",
        rf"{expected_total}\s*条.*{expected_pass}\s*条?\s*合格",
        rf"合格.*{expected_pass}.*总.*{expected_total}",
    ]
    for pat in patterns_cn:
        m = re.search(pat, content, re.IGNORECASE | re.DOTALL)
        if m:
            return True, f"找到统计: '{m.group()[:60]}'"
    return False, f"未找到 {expected_pass}/{expected_total} 比例"


def check_rewrite_suggestion(content: str) -> tuple[bool, str]:
    """检查是否包含改写建议（关键词：改写、建议、推荐写法、suggested、rewrite）。"""
    keywords = ["改写", "建议", "推荐写法", "修改为", "应改为", "可以改为",
                 "suggested", "rewrite", "recommend", "should be", "改成",
                 "正确写法", "规范写法", "示例"]
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"改写建议关键词命中: {found}" if found else "未找到改写建议"
    return passed, evidence


def check_valid_type_in_suggestion(content: str) -> tuple[bool, str]:
    """检查改写建议中是否使用了合法的 Conventional Commits type。"""
    valid_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
    # 在改写/建议上下文中查找 type(scope): 或 type: 格式
    suggestion_pattern = r"(改写|建议|修改|推荐|应改|可以改|suggested|rewrite|correct|示例|规范).{0,200}"
    suggestion_blocks = re.findall(suggestion_pattern, content, re.IGNORECASE | re.DOTALL)

    # 也在代码块和反引号中查找
    code_pattern = r"`([^`]+)`"
    code_blocks = re.findall(code_pattern, content)

    search_text = " ".join(suggestion_blocks) + " " + " ".join(code_blocks)
    if not search_text.strip():
        search_text = content

    found_types = []
    for t in valid_types:
        # 匹配 type( 或 type: 格式
        if re.search(rf"\b{t}\s*[\(:]", search_text, re.IGNORECASE):
            found_types.append(t)

    passed = len(found_types) >= 1
    evidence = f"建议中使用的合法 type: {found_types}" if found_types else "未在建议中找到合法 type"
    return passed, evidence


def check_no_false_negatives(content: str) -> tuple[bool, str]:
    """检查输出是否没有对合规 commit 给出否定评价（用于全部合规场景）。"""
    # 查找针对具体 commit 的否定评价
    negative_patterns = [
        r"不合[格规]",
        r"不符合",
        r"存在问题",
        r"需要修[改正]",
        r"错误",
        r"不规范",
        r"违反",
        r"invalid",
        r"incorrect",
        r"does not comply",
        r"non-compliant",
    ]
    # 但允许在"规则说明"或"如果不合规"的假设性语境中出现
    # 简化判断：如果出现否定词且同时出现具体 commit 的引用，则判为 false negative
    found_negatives = []
    for pat in negative_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            found_negatives.extend(matches[:2])

    # 如果存在否定词，检查是否有具体 commit 被标记为不合格
    commit_refs = ["feat(user)", "fix(cart)", "docs(readme)", "refactor(auth)"]
    flagged_commits = []
    for ref in commit_refs:
        for neg in negative_patterns:
            # 在 ref 附近 200 字符内查找否定词
            pattern = rf"{re.escape(ref)}.{{0,200}}{neg}"
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                flagged_commits.append(ref)
                break
            pattern = rf"{neg}.{{0,200}}{re.escape(ref)}"
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                flagged_commits.append(ref)
                break

    passed = len(flagged_commits) == 0
    if passed:
        evidence = "未发现对合规 commit 的虚假否定评价"
    else:
        evidence = f"对以下合规 commit 给出了否定评价: {flagged_commits}"
    return passed, evidence


def check_all_pass_confirmation(content: str) -> tuple[bool, str]:
    """检查是否明确确认所有 commit 均合规。"""
    keywords = [
        "全部合格", "全部合规", "全部符合", "均合格", "均合规", "均符合",
        "都合格", "都合规", "都符合", "全部通过", "均通过", "都通过",
        "all pass", "all comply", "all valid", "all correct",
        "没有问题", "无问题", "4/4", "4条合格", "4 条合格",
    ]
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"确认词命中: {found}" if found else "未找到全部合规确认"
    return passed, evidence


def check_blank_line_issue(content: str) -> tuple[bool, str]:
    """检查是否识别了空行分隔问题。"""
    keywords = [
        "空行", "blank line", "empty line", "分隔", "separator",
        "header 和 body", "header与body", "标题和正文", "标题与正文",
        "缺少空行", "没有空行", "需要空行", "应有空行",
    ]
    found = [kw for kw in keywords if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"空行问题关键词命中: {found}" if found else "未提及空行分隔问题"
    return passed, evidence


def check_invalid_type_detection(content: str, invalid_type: str) -> tuple[bool, str]:
    """检查是否识别了非法 type。"""
    # 检查是否提到了非法 type 且指出它不合法
    keywords_context = [
        "不合法", "不在", "不是有效", "不属于", "不是合法",
        "不在允许", "invalid", "not valid", "not allowed",
        "不支持", "不规范", "非标准", "不正确",
    ]
    # 先检查是否提到了这个 invalid type
    if invalid_type.lower() not in content.lower():
        return False, f"未提及 '{invalid_type}'"

    # 检查 invalid_type 附近是否有否定性评价
    for kw in keywords_context:
        passed_prox, _ = check_proximity(content, invalid_type, kw, max_distance=80)
        if passed_prox:
            return True, f"识别了 '{invalid_type}' 为非法 type"

    # 宽松检查：只要提到了 invalid_type 且整体有否定评价
    has_negative = any(kw.lower() in content.lower() for kw in keywords_context)
    if has_negative:
        return True, f"提到了 '{invalid_type}' 并有否定评价（宽松匹配）"

    return False, f"提到了 '{invalid_type}' 但未明确指出其为非法 type"


# ═════════════════════════════════════════════
# 每个 eval 的专属检查逻辑
# ═════════════════════════════════════════════


def grade_eval_1(content: str) -> list[dict]:
    """eval-1: 基本路径 — 混合合规/不合规的 3 条 commit"""
    results = []

    # A1-01: 输出包含总览统计（合格数/总数，应为 1/3）
    passed, evidence = check_count_summary(content)
    results.append({
        "id": "A1-01",
        "text": "输出包含总览统计（合格数/总数）",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-02: 识别第 1 条 commit 缺少 type(scope): 格式
    kw_list = ["Update user login", "格式", "type", "缺少"]
    passed_kw, ev_kw = check_keywords(content, kw_list, 2)
    passed_prox, ev_prox = check_proximity(content, "Update user login", "type", 150)
    passed = passed_kw or passed_prox
    evidence = f"关键词: {ev_kw} | 近邻: {ev_prox}"
    results.append({
        "id": "A1-02",
        "text": "识别第 1 条 commit 缺少 type(scope): 格式",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-03: 识别第 3 条 commit 的 type 不合法（Fixed）
    passed, evidence = check_invalid_type_detection(content, "Fixed")
    results.append({
        "id": "A1-03",
        "text": "识别第 3 条 commit 的 type 不合法（Fixed）",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-04: 识别第 3 条 commit 以句号结尾
    period_keywords = ["句号", "句点", "period", "结尾", "末尾",
                       "trailing", "ending with", "以.结尾", "以 . 结尾",
                       "以「.」结尾", "不应以"]
    passed_kw, ev_kw = check_keywords(content, period_keywords, 1)
    # 也检查近邻：payment 和 句号/period
    passed_prox, ev_prox = check_proximity(content, "payment", "句号", 100)
    passed_prox2, ev_prox2 = check_proximity(content, "payment", "period", 100)
    passed_prox3, ev_prox3 = check_proximity(content, "payment", ".", 60)
    passed = passed_kw or passed_prox or passed_prox2 or passed_prox3
    evidence = f"关键词: {ev_kw}"
    results.append({
        "id": "A1-04",
        "text": "识别第 3 条 commit 以句号结尾",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-05: 确认第 2 条 commit (feat(auth): add OAuth2 support) 合格
    oauth_keywords = ["OAuth2", "auth", "feat(auth)"]
    pass_keywords = ["合格", "合规", "符合", "通过", "正确", "pass", "valid",
                      "comply", "correct", "没有问题", "✓", "✅"]
    # 检查 OAuth/auth 附近有合格评价
    passed = False
    evidence_parts = []
    for ok in oauth_keywords:
        for pk in pass_keywords:
            p, e = check_proximity(content, ok, pk, 100)
            if p:
                passed = True
                evidence_parts.append(e)
                break
        if passed:
            break
    evidence = evidence_parts[0] if evidence_parts else "未找到对第 2 条 commit 的合格确认"
    results.append({
        "id": "A1-05",
        "text": "确认第 2 条 commit 合格",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-06: 为不合格 commit 提供改写建议
    passed, evidence = check_rewrite_suggestion(content)
    results.append({
        "id": "A1-06",
        "text": "为不合格 commit 提供改写建议",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-07: 改写建议中使用了合法的 type
    passed, evidence = check_valid_type_in_suggestion(content)
    results.append({
        "id": "A1-07",
        "text": "改写建议中使用了合法的 type",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_2(content: str) -> list[dict]:
    """eval-2: 领域变体 — 含 body/footer 的多行 commit"""
    results = []

    # A2-01: 输出包含总览统计
    passed, evidence = check_count_summary(content)
    results.append({
        "id": "A2-01",
        "text": "输出包含总览统计（合格数/总数）",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-02: 识别第一条 commit 的空行分隔问题
    passed, evidence = check_blank_line_issue(content)
    results.append({
        "id": "A2-02",
        "text": "识别第一条 commit 的空行分隔问题",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-03: 确认第二条 commit 合格或基本合规
    fix_db_keywords = ["fix(db)", "connection pool", "resolve connection"]
    pass_keywords = ["合格", "合规", "符合", "通过", "正确", "pass", "valid",
                      "comply", "correct", "没有问题", "规范", "✓", "✅"]
    passed = False
    evidence = "未找到对第二条 commit 的合规确认"
    for fk in fix_db_keywords:
        for pk in pass_keywords:
            p, e = check_proximity(content, fk, pk, 120)
            if p:
                passed = True
                evidence = e
                break
        if passed:
            break
    results.append({
        "id": "A2-03",
        "text": "确认第二条 commit 合格或基本合规",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-04: 提及 body 和 header 之间需要空行
    passed_kw, ev_kw = check_keywords(content, ["空行", "blank line", "empty line"], 1)
    passed_prox, ev_prox = check_proximity(content, "body", "空行", 80)
    passed_prox2, ev_prox2 = check_proximity(content, "header", "空行", 80)
    passed_prox3, ev_prox3 = check_proximity(content, "body", "blank line", 80)
    passed = passed_kw or passed_prox or passed_prox2 or passed_prox3
    evidence = f"关键词: {ev_kw}"
    results.append({
        "id": "A2-04",
        "text": "提及 body 和 header 之间需要空行",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-05: 为不合格 commit 提供改写建议
    passed, evidence = check_rewrite_suggestion(content)
    results.append({
        "id": "A2-05",
        "text": "为不合格 commit 提供改写建议",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-06: 改写建议中体现了正确的空行分隔格式
    # 检查是否有包含空行分隔的代码块或示例
    # 正确格式应该是: header\n\nbody
    blank_line_in_example = bool(re.search(
        r"```[\s\S]*?\n\n[\s\S]*?```",
        content
    ))
    # 也检查反引号外的改写示例
    rewrite_with_blank = bool(re.search(
        r"(改写|建议|修改|示例|correct).{0,100}\n\n",
        content, re.IGNORECASE
    ))
    passed = blank_line_in_example or rewrite_with_blank
    evidence = f"代码块含空行={blank_line_in_example}, 改写含空行={rewrite_with_blank}"
    results.append({
        "id": "A2-06",
        "text": "改写建议中体现了正确的空行分隔格式",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_3(content: str) -> list[dict]:
    """eval-3: 领域跨越 — 全部合规的 4 条 commit"""
    results = []

    # A3-01: 总览统计显示全部合格（4/4）
    passed, evidence = check_count_ratio(content, 4, 4)
    if not passed:
        # 宽松：检查是否有"全部合格"等表述
        passed, evidence = check_all_pass_confirmation(content)
    results.append({
        "id": "A3-01",
        "text": "总览统计显示全部合格（4/4）",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-02: 没有给合规 commit 报告虚假问题
    passed, evidence = check_no_false_negatives(content)
    results.append({
        "id": "A3-02",
        "text": "没有给合规 commit 报告虚假问题",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-03: 明确确认所有 commit 合规
    passed, evidence = check_all_pass_confirmation(content)
    results.append({
        "id": "A3-03",
        "text": "明确确认所有 commit 合规",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-04: 可选 — 包含最佳实践提示或正面评价
    best_practice_kw = ["最佳实践", "best practice", "建议", "提示", "tip",
                         "补充", "注意", "良好", "优秀", "规范",
                         "不错", "很好", "good", "well"]
    passed, evidence = check_keywords(content, best_practice_kw, 1)
    results.append({
        "id": "A3-04",
        "text": "可选：包含最佳实践提示或正面评价",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-05: 仍然包含审查报告的基本结构
    passed, evidence = check_count_summary(content)
    if not passed:
        # 宽松：至少有审查报告的标题或总结性段落
        structure_kw = ["审查", "报告", "review", "result", "总览",
                        "summary", "结果", "总结", "检查"]
        passed, evidence = check_keywords(content, structure_kw, 1)
    results.append({
        "id": "A3-05",
        "text": "仍然包含审查报告的基本结构",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_4(content: str) -> list[dict]:
    """eval-4: 模糊输入 — 用户没说"审查 commit""""
    results = []

    # A4-01: 识别出输入是 commit message 并进行规范审查
    review_kw = ["commit", "conventional", "规范", "格式", "type",
                  "scope", "审查", "检查", "review"]
    passed, evidence = check_keywords(content, review_kw, 2)
    results.append({
        "id": "A4-01",
        "text": "识别出输入是 commit message 并进行规范审查",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-02: 识别 ADD 不是合法 type
    passed, evidence = check_invalid_type_detection(content, "ADD")
    results.append({
        "id": "A4-02",
        "text": "识别 ADD 不是合法 type",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-03: 识别 bugfix 不是合法 type
    passed, evidence = check_invalid_type_detection(content, "bugfix")
    results.append({
        "id": "A4-03",
        "text": "识别 bugfix 不是合法 type（应为 fix）",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-04: 确认第 3 条 chore(deps) 合规
    chore_keywords = ["chore(deps)", "chore", "lodash"]
    pass_keywords = ["合格", "合规", "符合", "通过", "正确", "pass", "valid",
                      "comply", "correct", "没有问题", "规范", "✓", "✅"]
    passed = False
    evidence = "未找到对 chore(deps) 的合规确认"
    for ck in chore_keywords:
        for pk in pass_keywords:
            p, e = check_proximity(content, ck, pk, 120)
            if p:
                passed = True
                evidence = e
                break
        if passed:
            break
    results.append({
        "id": "A4-04",
        "text": "确认第 3 条 chore(deps) 合规",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-05: 输出包含总览统计
    passed, evidence = check_count_summary(content)
    results.append({
        "id": "A4-05",
        "text": "输出包含总览统计",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-06: 提供改写建议
    passed, evidence = check_rewrite_suggestion(content)
    results.append({
        "id": "A4-06",
        "text": "提供改写建议",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_5(content: str) -> list[dict]:
    """eval-5: 边界/降级 — 非 commit message 输入"""
    results = []

    # A5-01: 指出输入不符合 commit message 的基本格式
    not_commit_kw = [
        "不符合", "不是", "非标准", "不合格", "不规范",
        "格式不", "没有遵循", "不满足", "does not", "invalid",
        "not a valid", "工作日志", "日报", "不像",
    ]
    passed, evidence = check_keywords(content, not_commit_kw, 1)
    results.append({
        "id": "A5-01",
        "text": "指出输入不符合 commit message 的基本格式",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-02: 提到 Conventional Commits 格式要求
    format_kw = ["type(scope)", "type:", "conventional commit",
                  "feat", "fix", "格式要求", "规范格式"]
    passed, evidence = check_keywords(content, format_kw, 1)
    results.append({
        "id": "A5-02",
        "text": "提到 Conventional Commits 格式要求",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-03: 建议拆分为多条 commit 或给出改写示例
    split_kw = ["拆分", "拆成", "分成", "分为", "split", "separate",
                 "改写", "改为", "rewrite", "建议", "示例", "example",
                 "可以写成", "应该写成"]
    passed, evidence = check_keywords(content, split_kw, 1)
    results.append({
        "id": "A5-03",
        "text": "建议拆分为多条 commit 或给出改写示例",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-04: 改写示例中使用了合法 type
    passed, evidence = check_valid_type_in_suggestion(content)
    results.append({
        "id": "A5-04",
        "text": "改写示例中使用了合法 type",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-05: 没有假装输入是合规的
    false_pass_kw = ["合格", "合规", "符合规范", "全部通过", "没有问题",
                      "all pass", "compliant", "valid commit"]
    found = [kw for kw in false_pass_kw if kw.lower() in content.lower()]
    passed = len(found) == 0  # 应该没有这些词
    evidence = f"{'未出现合规假象' if passed else f'出现了不应有的合规评价: {found}'}"
    results.append({
        "id": "A5-05",
        "text": "没有假装输入是合规的",
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
        "skill_name": "commit-message-reviewer",
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
   - 将 commit-message-reviewer 的 SKILL.md 注入 subagent 的 system prompt
   - 将 eval 的 `prompt` 字段作为用户输入
   - 将输出保存到 `evals/output/eval-N/response.md`

3. **运行评分**：
   ```bash
   python3 evals/grade.py evals/output
   ```

4. **查看结果**：评分结果保存在 `evals/output/grading.json`

### 评分维度说明

| 维度 | 权重 | 衡量内容 |
|------|------|---------|
| core_detection | 30% | 能否正确识别格式错误 |
| report_structure | 25% | 输出结构是否完整（总览、问题列表、改写建议） |
| rewrite_quality | 20% | 改写建议是否使用合法 type、格式正确 |
| rule_coverage | 15% | 是否覆盖全部规则（type、大小写、句号、空行） |
| boundary_handling | 10% | 边界场景（全合规、非 commit 输入）的处理 |

### 5 个 eval 设计总结

| eval | 类型 | 核心验证点 | 断言数 | 总分 |
|------|------|---------|--------|------|
| eval-1 | 基本路径 | 混合 commit 的完整审查流程 | 7 | 48 |
| eval-2 | 领域变体 | 多行 commit 的空行分隔检查 | 6 | 42 |
| eval-3 | 领域跨越 | 全部合规时不报假阳性 | 5 | 37 |
| eval-4 | 模糊输入 | 无触发词时自动识别意图 | 6 | 38 |
| eval-5 | 边界降级 | 非 commit 输入的优雅处理 | 5 | 38 |
