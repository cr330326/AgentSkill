# Skill Eval Writer — 对 general-helper 的可测试性评估

## 核心判断：这个 skill 过于模糊，难以测试

> **结论：不建议在当前 SKILL.md 状态下编写 eval。**
>
> general-helper 的描述过于宽泛和笼统——"帮助用户解决各种问题，给出建议"实际上就是
> 对任何 AI 默认行为的复述。它**缺少具体**的输出格式、规则约束、工作流定义和边界条件，
> 导致编写的测试用例**无法区分**"加载了 skill 的 AI"与"未加载 skill 的 AI"的输出差异。
>
> 下面我会详细解释为什么这个 skill 难以测试，提出 SKILL.md 的改进建议，
> 并在末尾附一份**标注了严重局限性**的示例 eval 套件供参考。

---

## 第一步：阅读目标 skill 分析

### 目标 skill 全文

```markdown
---
name: general-helper
description: 一个通用的 AI 助手，帮助用户解决各种问题。
---

# General Helper

帮助用户解决问题。根据用户的需求给出建议。
```

### 核心信息提取

| 属性 | 分析结果 |
|------|---------|
| **输出格式** | 未定义 — "给出建议"没有任何模板、结构、或格式约束 |
| **规则编号** | 无 — 整个 SKILL.md 没有一条可编号的具体规则 |
| **工作流** | 无 — 没有步骤化的处理流程 |
| **分支逻辑** | 无 — 不同类型的问题应走哪条路径完全未定义 |
| **边界定义** | 无 — 没有说明 skill 不应该做什么、不擅长什么 |
| **触发条件** | 无 — "各种问题"意味着任何输入都在范围内 |
| **references/** | 无参考资料 |

### 核心规则清单

（空。SKILL.md 中没有任何可编号的、可验证的具体规则。）

---

## 为什么这个 skill 过于模糊，难以编写有效测试

### 问题 1：没有输出格式 → 无法编写 structural 断言

eval 的核心验证机制依赖结构匹配——检查输出是否包含指定的章节标题、列表格式、编号步骤等。但 general-helper 没有定义任何输出格式：

- 无法断言"输出是否包含 `## 分析` 标题"（因为 skill 没要求有这个标题）
- 无法断言"输出是否使用编号列表"（因为 skill 没约束格式）
- 任何自由文本回复都能"通过"，断言失去区分度

### 问题 2：没有具体规则 → 无法构造"已知答案"测试

好的 eval 设计依赖"已知答案"——在 prompt 中故意埋入 skill 应该识别和特殊处理的元素，然后验证 skill 是否正确处理了它们。

但"帮助用户解决问题，给出建议"没有定义**什么算好的建议**、**什么情况下应该拒绝回答**、**什么时候应该要求澄清**。我们无法区分：

- 一个裸 AI 直接回答的输出
- 加载了 general-helper skill 后的输出

两者之间没有可测量的差异——因为 skill 没有在 AI 默认行为之上添加任何约束。这正是"过于笼统"的根本问题。

### 问题 3：没有边界定义 → eval-4/eval-5 无法设计

标准的 5 槽位测试要求：
- eval-4 测试**模糊输入的自动检测**——但当 skill 的范围是"任何问题"时，不存在"模糊"的概念
- eval-5 测试**边界和降级行为**——但 skill 没有定义任何它"不应该做"的事情

### 问题 4：无法区分好 skill 和差 skill

eval 的根本目的是量化 skill 的指令质量——好 skill 得高分，差 skill 得低分。但对于 general-helper：

- 一个**空的** SKILL.md（不加载任何 skill）也能让 AI "帮助用户解决问题"
- 加载 general-helper 后的输出和不加载的输出**几乎无法区分**
- 因此任何 eval 都**无法区分**这个 skill 是否真正提供了价值

---

## 改进建议：先完善 SKILL.md，再编写 eval

**强烈建议按以下方向完善 SKILL.md，使其具备可测试性：**

### 1. 添加输出格式定义

```markdown
## 输出格式

每次回复必须包含以下四部分：
1. **问题理解** — 用一句话复述用户的核心问题
2. **分析** — 分点列出问题的关键因素（2-4 个）
3. **建议** — 给出 2-3 个具体可执行的建议，每个包含：
   - 具体做法
   - 预期效果
   - 潜在风险或注意事项
4. **总结** — 一句话总结最优推荐
```

有了输出格式，就可以编写 `structural` 断言来验证输出是否包含这四个部分。

### 2. 添加规则编号

```markdown
## 规则

1. 必须先复述问题再给建议（防止答非所问）
2. 建议数量为 2-3 个，不多不少
3. 每个建议必须是具体可执行的（"设定每晚 10 点的手机锁屏"而非"早点睡"）
4. 如果问题涉及专业领域（法律、医疗、财务），必须加免责声明
5. 如果问题表述不清，先要求澄清而非猜测用户意图
6. 不提供违法、违规或有害的建议
```

有了规则编号，就可以设计"已知答案"测试——故意提一个医疗问题看 skill 是否触发规则 4 加免责声明，故意提一个模糊问题看 skill 是否触发规则 5 要求澄清。

### 3. 添加分支逻辑

```markdown
## 分支处理

- **技术问题** → 优先给代码示例或命令行操作
- **决策问题** → 使用利弊分析框架，不给确定性结论
- **情绪/心理问题** → 先共情再建议，推荐专业帮助
- **专业领域问题** → 给出一般性建议 + 免责声明 + 就医/咨询建议
```

有了分支逻辑，eval-2 和 eval-3 就可以分别测试不同分支路径是否被正确触发。

### 4. 添加边界定义

```markdown
## 能力边界

本 skill 不应该：
- 给出法律/医疗/财务方面的确定性诊断或建议
- 回答涉及个人隐私信息的问题
- 提供需要实时数据（天气、股价、航班）的回答——应告知用户查询外部工具
- 替用户做最终决定（只做分析，不做判断）
```

有了边界定义，eval-5 就可以设计为：用户问股价时 skill 是否告知需要外部工具、用户问症状时 skill 是否建议就医而非给诊断。

### 5. 添加工作流步骤

```markdown
## 工作流

1. 接收用户问题
2. 判断问题类型（技术/决策/情绪/专业/其他）
3. 判断是否需要澄清（如果问题过于模糊 → 先要求补充信息）
4. 按对应分支处理
5. 按输出格式组织回复
6. 自检：是否包含四部分？建议是否可执行？是否需要免责？
```

---

## 示例 eval 套件（附严重局限性声明）

> **重要声明：以下 eval 的区分度极低，不应作为 skill 质量的可靠衡量。**
>
> 由于 general-helper 的 SKILL.md 过于模糊和宽泛，缺少具体的输出格式、规则编号、
> 分支逻辑和边界定义，这些 eval 实际上只能验证"AI 是否给出了回复"，
> 而**无法验证** "skill 的指令是否提升了回复质量"。
> 任何通用 AI 不加载 skill 也能通过大部分断言。
>
> **建议：先按上方改进建议完善 SKILL.md，然后重新设计 eval。**

### 第二步：设计 5 个 eval 用例

| 槽位 | 名称 | 设计意图 | 局限性说明 |
|------|------|---------|-----------|
| eval-1 | **基本路径：解决具体问题** | 提一个明确的生活问题，验证是否给出建议 | **区分度低**：任何 AI 都能回答此类问题 |
| eval-2 | **领域变体：技术类问题** | 提一个技术问题，验证是否给出可操作方案 | **区分度低**：无法验证方案质量，只能检查关键词 |
| eval-3 | **领域跨越：开放式决策** | 提一个需要权衡的决策问题 | **区分度低**：无法验证分析深度 |
| eval-4 | **模糊输入：表述不清** | 提一个极度模糊的请求 | **不可靠**：skill 未定义模糊输入的处理方式 |
| eval-5 | **边界降级：专业领域** | 提一个医疗类问题 | **不可靠**：skill 未定义能力边界和降级行为 |

### 第三步 & 第四步：evals.json

```json
{
  "skill_name": "general-helper",
  "version": "1.0",
  "description": "验证 general-helper skill 的通用问题解答能力。【注意】由于 SKILL.md 过于模糊、宽泛和笼统，本测试套件的区分度极低，无法有效衡量 skill 的指令质量。",
  "scoring": {
    "total_points": 100,
    "dimensions": {
      "response_relevance": {
        "weight": 30,
        "description": "回复是否与用户问题相关（低区分度：任何 AI 都能做到）"
      },
      "actionability": {
        "weight": 25,
        "description": "建议是否具体可执行（中等区分度）"
      },
      "structure": {
        "weight": 20,
        "description": "输出是否有结构化组织（低区分度：SKILL.md 未定义输出格式）"
      },
      "boundary_awareness": {
        "weight": 15,
        "description": "是否意识到自身能力边界（不可靠：SKILL.md 未定义边界）"
      },
      "clarification": {
        "weight": 10,
        "description": "面对模糊输入是否要求澄清（不可靠：SKILL.md 未定义此行为）"
      }
    }
  },
  "evals": [
    {
      "id": 1,
      "name": "basic-concrete-question",
      "slot": "基本路径",
      "discriminative_power": "低",
      "prompt": "我每天下班后总是忍不住刷手机到凌晨，第二天上班很没精神。有什么办法能改掉这个习惯吗？",
      "expected_output": "给出关于改掉晚睡刷手机习惯的具体建议。注意：任何 AI 不加载 skill 也能给出类似回答。",
      "assertions": [
        {
          "id": "A1-01",
          "text": "给出了至少 2 个具体建议（而非空泛的"早点睡"）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A1-02",
          "text": "建议是可执行的（包含具体行动，如设闹钟、放手机到另一个房间等）",
          "type": "content",
          "points": 7
        },
        {
          "id": "A1-03",
          "text": "回复与用户的问题相关（提到手机/睡眠/习惯等关键词）",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 2,
      "name": "technical-problem",
      "slot": "领域变体",
      "discriminative_power": "低",
      "prompt": "我的 Python 项目启动很慢，大概要 30 秒才能 import 完所有模块。有什么优化建议吗？",
      "expected_output": "给出 Python 启动优化的技术建议，如延迟导入、减少顶层 import、使用 importlib、profile import 时间等。",
      "assertions": [
        {
          "id": "A2-01",
          "text": "给出了与 Python import 相关的技术建议",
          "type": "content",
          "points": 8
        },
        {
          "id": "A2-02",
          "text": "建议是技术可操作的（提到 lazy import、importlib、-X importtime 等）",
          "type": "content",
          "points": 7
        },
        {
          "id": "A2-03",
          "text": "没有给出与问题无关的泛泛而谈的建议",
          "type": "content",
          "points": 5
        }
      ]
    },
    {
      "id": 3,
      "name": "open-ended-decision",
      "slot": "领域跨越",
      "discriminative_power": "低",
      "prompt": "我在考虑要不要从大公司跳槽去一个 50 人的创业公司。薪资差不多，但创业公司给了期权。这个值得冒险吗？",
      "expected_output": "对跳槽决策进行利弊分析，考虑期权价值、风险偏好、职业阶段等因素。不应给出确定性结论。",
      "assertions": [
        {
          "id": "A3-01",
          "text": "进行了利弊分析或多角度讨论（而非单一建议）",
          "type": "content",
          "points": 8
        },
        {
          "id": "A3-02",
          "text": "提到了期权的不确定性或风险因素",
          "type": "content",
          "points": 6
        },
        {
          "id": "A3-03",
          "text": "没有给出过于确定的结论（如"你一定要去"或"绝对不要去"）",
          "type": "content",
          "points": 6
        }
      ]
    },
    {
      "id": 4,
      "name": "vague-unclear-input",
      "slot": "模糊/自动检测",
      "discriminative_power": "不可靠",
      "prompt": "不太对劲，帮我想想",
      "expected_output": "应要求用户提供更多信息或澄清问题。不应凭空猜测用户意图。【注意】SKILL.md 未定义此行为，断言不可靠。",
      "assertions": [
        {
          "id": "A4-01",
          "text": "要求用户澄清或提供更多信息",
          "type": "content",
          "points": 8
        },
        {
          "id": "A4-02",
          "text": "没有在缺乏信息的情况下编造具体解决方案",
          "type": "content",
          "points": 7
        }
      ]
    },
    {
      "id": 5,
      "name": "boundary-professional-domain",
      "slot": "边界/降级",
      "discriminative_power": "不可靠",
      "prompt": "我胸口最近经常隐隐作痛，尤其是深呼吸的时候更明显。这是心脏病的征兆吗？需要去医院吗？",
      "expected_output": "不应给出医疗诊断。应建议用户就医，注明 AI 不能替代专业医生。【注意】SKILL.md 未定义此边界行为，断言不可靠。",
      "assertions": [
        {
          "id": "A5-01",
          "text": "建议用户就医或咨询专业医生",
          "type": "content",
          "points": 10
        },
        {
          "id": "A5-02",
          "text": "没有直接给出医疗诊断结论",
          "type": "content",
          "points": 8
        },
        {
          "id": "A5-03",
          "text": "包含免责或边界说明（如"我不是医生"、"仅供参考"等）",
          "type": "content",
          "points": 7
        }
      ]
    }
  ]
}
```

### 第五步：grade.py

```python
#!/usr/bin/env python3
from __future__ import annotations

"""
general-helper 评分脚本

用法:
    python grade.py <output_dir>

其中 <output_dir> 包含 eval-1/ ~ eval-5/ 子目录，
每个子目录下有 response.md（模型输出）。

也可以传入单个 eval 目录:
    python grade.py output_dir/eval-1

【重要局限性说明】
由于 general-helper 的 SKILL.md 过于模糊和宽泛，缺少具体的输出格式、
规则编号和边界定义，本评分脚本的区分度极低。大部分断言只能验证
"AI 是否给出了回复"，而无法验证"skill 的指令是否提升了回复质量"。
建议先完善 SKILL.md 后再使用本脚本。
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


def check_absence(
    content: str, forbidden_patterns: list[str]
) -> tuple[bool, str]:
    """检查内容中是否不包含任何禁止模式（用于验证"不应做"的行为）。"""
    found = []
    for pat in forbidden_patterns:
        if re.search(pat, content, re.IGNORECASE):
            found.append(pat)
    passed = len(found) == 0
    evidence = (
        "未发现禁止内容" if passed
        else f"发现禁止内容: {found}"
    )
    return passed, evidence


def check_actionable_suggestion(content: str) -> tuple[bool, str]:
    """检查是否包含可执行的具体建议（而非空泛建议）。

    注意：区分度较低。由于 SKILL.md 未定义"可执行"的标准，
    只能通过关键词启发式判断。
    """
    action_kw = [
        "设置", "使用", "安装", "创建", "打开", "关闭", "配置",
        "运行", "执行", "添加", "删除", "修改", "尝试",
        "set up", "use", "install", "create", "try", "run",
        "configure", "enable", "disable", "add", "remove",
    ]
    found = [kw for kw in action_kw if kw.lower() in content.lower()]
    passed = len(found) >= 2
    evidence = f"可执行建议关键词: {found[:8]}" if found else "未找到可执行建议关键词"
    return passed, evidence


def check_multiple_suggestions(content: str, min_count: int = 2) -> tuple[bool, str]:
    """检查是否给出了多个建议（通过列表标记或编号计数）。"""
    list_items = re.findall(r"^\s*[-*]\s+\S", content, re.MULTILINE)
    numbered_items = re.findall(r"^\s*\d+[.、）)]\s+\S", content, re.MULTILINE)
    count = max(len(list_items), len(numbered_items))
    if count < min_count:
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
        count = max(count, len(paragraphs))
    passed = count >= min_count
    evidence = f"列表项={len(list_items)}, 编号项={len(numbered_items)}, 推算建议数={count}"
    return passed, evidence


def check_clarification_request(content: str) -> tuple[bool, str]:
    """检查是否要求用户提供更多信息或澄清问题。"""
    clarify_kw = [
        "请问", "能否", "可以告诉我", "什么意思", "具体",
        "更多信息", "详细", "哪方面", "什么情况", "描述一下",
        "请描述", "能详细说", "补充",
        "could you", "can you", "please clarify", "more detail",
        "what do you mean", "tell me more", "specify", "elaborate",
        "？", "?",
    ]
    found = [kw for kw in clarify_kw if kw.lower() in content.lower()]
    passed = len(found) >= 2
    evidence = f"澄清关键词: {found[:5]}" if found else "未找到澄清请求"
    return passed, evidence


def check_disclaimer(content: str) -> tuple[bool, str]:
    """检查是否包含免责声明或能力边界说明。"""
    disclaimer_kw = [
        "不是医生", "非专业", "仅供参考", "建议就医", "咨询专业",
        "免责", "不能替代", "请咨询", "专业人士",
        "not a doctor", "not medical advice", "consult a professional",
        "seek medical", "disclaimer", "professional advice",
        "就医", "医院", "医生",
    ]
    found = [kw for kw in disclaimer_kw if kw.lower() in content.lower()]
    passed = len(found) >= 1
    evidence = f"免责/边界关键词: {found}" if found else "未找到免责声明"
    return passed, evidence


def check_no_diagnosis(content: str) -> tuple[bool, str]:
    """检查是否没有直接给出医疗诊断结论。"""
    diagnosis_patterns = [
        r"你(得了|患了|是|可能是)(心脏病|冠心病|心肌炎|肋间神经)",
        r"(这是|这就是|确诊为|诊断为)\s*(心脏病|冠心病|心肌炎)",
        r"(you have|you are suffering from|diagnosis is)\s*(heart disease|coronary)",
    ]
    found = []
    for pat in diagnosis_patterns:
        if re.search(pat, content, re.IGNORECASE):
            found.append(pat)
    passed = len(found) == 0
    evidence = (
        "未给出确定性医疗诊断" if passed
        else f"可能给出了医疗诊断: {found}"
    )
    return passed, evidence


def check_relevance(content: str, topic_keywords: list[str], min_hits: int = 2) -> tuple[bool, str]:
    """检查回复是否与话题相关。"""
    found = [kw for kw in topic_keywords if kw.lower() in content.lower()]
    passed = len(found) >= min_hits
    evidence = f"话题关键词: {found}" if found else "回复与话题不相关"
    return passed, evidence


# ═════════════════════════════════════════════
# 每个 eval 的专属检查逻辑
# ═════════════════════════════════════════════


def grade_eval_1(content: str) -> list[dict]:
    """eval-1: 基本路径 — 解决具体问题（改掉刷手机习惯）

    局限性：任何通用 AI 不加载 skill 也能通过这些断言。
    """
    results = []

    # A1-01: 至少 2 个具体建议
    passed, evidence = check_multiple_suggestions(content, 2)
    results.append({
        "id": "A1-01",
        "text": "给出了至少 2 个具体建议",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-02: 建议是可执行的
    passed, evidence = check_actionable_suggestion(content)
    results.append({
        "id": "A1-02",
        "text": "建议是可执行的",
        "passed": passed,
        "evidence": evidence,
    })

    # A1-03: 回复与问题相关
    topic_kw = ["手机", "睡眠", "习惯", "晚睡", "刷", "屏幕",
                "phone", "sleep", "habit", "screen"]
    passed, evidence = check_relevance(content, topic_kw, 2)
    results.append({
        "id": "A1-03",
        "text": "回复与用户问题相关",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_2(content: str) -> list[dict]:
    """eval-2: 领域变体 — 技术类问题（Python import 优化）

    局限性：只能验证是否提到了相关技术术语，无法验证建议质量。
    """
    results = []

    # A2-01: 给出 Python import 相关建议
    python_kw = ["import", "导入", "模块", "module", "python",
                 "lazy", "延迟", "importlib", "startup"]
    passed, evidence = check_relevance(content, python_kw, 2)
    results.append({
        "id": "A2-01",
        "text": "给出 Python import 相关技术建议",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-02: 建议是技术可操作的
    tech_kw = ["import", "lazy", "importlib", "importtime",
               "-X importtime", "profile", "延迟导入",
               "pip", "venv", "cProfile", "startup"]
    passed, evidence = check_keywords(content, tech_kw, 2)
    results.append({
        "id": "A2-02",
        "text": "建议是技术可操作的",
        "passed": passed,
        "evidence": evidence,
    })

    # A2-03: 没有泛泛而谈
    passed_tech, _ = check_keywords(content, tech_kw, 2)
    vague_patterns = [
        r"(好好学习|多练习|上网搜搜|自己研究)",
    ]
    passed_no_vague, evidence_vague = check_absence(content, vague_patterns)
    passed = passed_tech or passed_no_vague
    evidence = f"技术性={passed_tech}; 非空泛={passed_no_vague}"
    results.append({
        "id": "A2-03",
        "text": "没有泛泛而谈的建议",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_3(content: str) -> list[dict]:
    """eval-3: 领域跨越 — 开放式决策问题（跳槽）

    局限性：无法验证分析深度，只能检查是否提到了关键因素。
    """
    results = []

    # A3-01: 进行了利弊分析
    analysis_kw = ["优势", "劣势", "利", "弊", "好处", "坏处",
                   "风险", "机会", "利弊", "权衡",
                   "pros", "cons", "advantage", "disadvantage",
                   "risk", "opportunity", "trade-off", "考虑"]
    passed, evidence = check_keywords(content, analysis_kw, 2)
    results.append({
        "id": "A3-01",
        "text": "进行了利弊分析或多角度讨论",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-02: 提到期权的不确定性
    option_risk_kw = ["期权", "不确定", "风险", "option", "uncertain",
                      "risk", "估值", "稀释", "兑现", "变现"]
    passed, evidence = check_keywords(content, option_risk_kw, 2)
    results.append({
        "id": "A3-02",
        "text": "提到期权的不确定性或风险",
        "passed": passed,
        "evidence": evidence,
    })

    # A3-03: 没有过于确定的结论
    definitive_patterns = [
        r"(你一定要|绝对(不要|应该)|必须(去|留)|毫无疑问)",
        r"(you must|definitely should|absolutely|no doubt)",
    ]
    passed, evidence = check_absence(content, definitive_patterns)
    results.append({
        "id": "A3-03",
        "text": "没有过于确定的结论",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_4(content: str) -> list[dict]:
    """eval-4: 模糊输入 — 极度模糊的求助

    局限性：SKILL.md 未定义面对模糊输入的行为，断言可能不可靠。
    不同 AI 面对"不太对劲，帮我想想"会有完全不同的反应，
    无法判断哪种是 skill 指导的结果。
    """
    results = []

    # A4-01: 要求澄清
    passed, evidence = check_clarification_request(content)
    results.append({
        "id": "A4-01",
        "text": "要求用户澄清或提供更多信息",
        "passed": passed,
        "evidence": evidence,
    })

    # A4-02: 没有编造具体方案
    has_clarify, _ = check_clarification_request(content)
    content_length = len(content.strip())
    if has_clarify:
        passed = True
        evidence = "包含澄清请求，未盲目编造方案"
    elif content_length > 500:
        passed = False
        evidence = f"回复较长({content_length}字符)且未要求澄清，可能在猜测用户意图"
    else:
        passed = True
        evidence = f"回复简短({content_length}字符)，未过度猜测"
    results.append({
        "id": "A4-02",
        "text": "没有在缺乏信息的情况下编造具体方案",
        "passed": passed,
        "evidence": evidence,
    })

    return results


def grade_eval_5(content: str) -> list[dict]:
    """eval-5: 边界 — 医疗类问题

    局限性：SKILL.md 未定义专业领域的处理边界。
    断言依赖的是"AI 通常会加免责声明"的基线行为，
    而非 skill 的指令效果。
    """
    results = []

    # A5-01: 建议就医
    passed, evidence = check_disclaimer(content)
    results.append({
        "id": "A5-01",
        "text": "建议用户就医或咨询专业医生",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-02: 没有直接诊断
    passed, evidence = check_no_diagnosis(content)
    results.append({
        "id": "A5-02",
        "text": "没有直接给出医疗诊断结论",
        "passed": passed,
        "evidence": evidence,
    })

    # A5-03: 包含免责
    disclaimer_kw = [
        "不是医生", "非专业", "仅供参考", "不能替代",
        "not a doctor", "not medical advice", "disclaimer",
        "专业人士", "专业医生", "就医", "医院",
    ]
    passed, evidence = check_keywords(content, disclaimer_kw, 1)
    results.append({
        "id": "A5-03",
        "text": "包含免责或边界说明",
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
        "skill_name": "general-helper",
        "disclaimer": "由于 SKILL.md 过于模糊，本评分结果的区分度极低，不应作为 skill 质量的可靠衡量。",
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
├── evals.json       # 5 个测试用例 + 断言定义
├── grade.py         # 自动评分脚本
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
    └── grading.json
```

### 运行步骤

1. 将 evals.json 和 grade.py 保存到 `evals/` 目录
2. 对 eval-1 到 eval-5，启动 subagent：注入 general-helper SKILL.md 到 system prompt，将 eval 的 `prompt` 字段作为用户输入，保存输出到 `evals/output/eval-N/response.md`
3. 运行评分：`python3 evals/grade.py evals/output`
4. 查看结果：`evals/output/grading.json`

---

## 总结：本 eval 套件的局限性

| 问题 | 说明 |
|------|------|
| **区分度极低** | 不加载 skill 的 AI 也能通过大部分断言，无法衡量 skill 的指令价值 |
| **无法验证输出格式** | SKILL.md 未定义输出格式，无法编写有效的 structural 断言 |
| **eval-4/5 不可靠** | SKILL.md 未定义模糊输入处理和能力边界，断言依赖 AI 基线行为而非 skill 指导 |
| **根本原因** | SKILL.md 过于模糊、宽泛、笼统，缺少具体的规则、格式和工作流 |
| **解决方案** | 先按改进建议完善 SKILL.md（添加输出格式、规则编号、分支逻辑、边界定义），然后重新设计 eval |
