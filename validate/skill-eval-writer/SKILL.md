---
name: skill-eval-writer
description: >-
  为任意 skill 编写测试用例（evals）和自动评分脚本（grade.py）的元工具。
  输入一个 skill 的 SKILL.md 和 references/，输出 evals.json + grade.py + 
  运行指南。用于验证 skill 的指令质量——同一个 AI 加载好 skill 和差 skill，
  输出质量会有显著差异，eval 就是量化这个差异的手段。
  当用户提到"给 skill 写测试"、"写 eval"、"测试用例"、"验证 skill 效果"、
  "skill evaluation"、"skill testing"、"eval for skill"、"grade skill"、
  "帮我测一下这个 skill"、"这个 skill 效果怎么样"时使用。
---

# Skill Eval Writer — 为 Skill 编写测试用例的元工具

## 核心理念

Skill 的价值在于**指令质量**，而非 AI 本身的能力。同一个 AI，加载好 skill 和差 skill，输出质量会有显著差异。Eval 的目的就是量化这个差异：

- **不是测 AI** — 是测 skill 的"指导效果"
- **已知答案测试** — 每个 eval prompt 都有预设的"正确行为"，通过关键词和结构匹配来验证
- **可重复验证** — grade.py 是纯自动化的，任何时候重跑都能得到一致结果

## 工作流程

### 第一步：阅读目标 skill

仔细阅读要测试的 skill 的全部内容：

1. **SKILL.md** — 理解 skill 的工作流、输出格式、规则约束
2. **references/** — 理解 skill 依赖的参考资料（清单、模板、示例代码等）
3. 识别 skill 的**核心行为**（skill 成功时应该做什么）和**边界行为**（遇到模糊或不支持的输入时应该怎么做）

关键问题清单——读完后你应该能回答：
- 这个 skill 的输入是什么格式？（代码片段、文档、需求描述、文件路径？）
- 这个 skill 的输出是什么格式？（结构化报告、文件树、对话式回复？）
- skill 有哪些**必须出现**的输出元素？（标题、编号、模板字段、特定关键词？）
- skill 有哪些**分支逻辑**？（根据输入类型走不同路径？自动检测？组合加载？）
- skill 的边界在哪？（什么输入它应该拒绝或降级处理？）

### 第二步：设计 5 个 eval 用例

每个 skill 固定设计 **5 个 eval**，覆盖从基本到边界的完整测试面。遵循以下 5 槽位模式：

| 槽位 | 类型 | 设计目标 | 要点 |
|------|------|---------|------|
| eval-1 | **基本路径** | 最典型的使用场景 | 用户意图明确，输入格式标准，所有核心行为都应触发 |
| eval-2 | **领域变体** | 同一 skill 的不同子领域 | 验证 skill 能处理不同类型的输入（如不同语言/不同框架/不同文档类型） |
| eval-3 | **领域跨越** | 与 eval-1 差异较大的场景 | 验证 skill 的泛化能力，是否只对一种情况有效 |
| eval-4 | **模糊/自动检测** | 用户没有明确说出 skill 的关键词 | 验证 skill 在输入模糊时能否自动识别意图。prompt 不要包含 skill 的触发词 |
| eval-5 | **边界/降级** | 超出 skill 能力范围的输入 | 验证 skill 是否优雅降级——不假装能做、告知局限、给出替代建议 |

#### 设计 eval prompt 的技巧

1. **埋"已知答案"** — 在 prompt 里故意放入 skill 应该识别的元素。例如测试代码审查 skill 时，故意写一段有 SQL 注入和硬编码密钥的代码。这些"坑"是你事先知道的，所以可以精确验证输出是否提到了它们。

2. **模拟真实用户** — prompt 应该像真实用户会说的话，不要写得像测试指令。"帮我看看这段代码有没有问题"比"请根据 PY-24 检查 SQL 注入"更接近真实场景。

3. **控制 prompt 复杂度** — eval-1 的 prompt 要足够简单（验证基本功能），eval-4/5 的 prompt 可以有歧义或陷阱（验证鲁棒性）。

4. **让每个 eval 有独特价值** — 5 个 eval 不要测重复的东西。如果 eval-1 已经验证了"输出包含标题"，其他 eval 可以假设这点成立，把分数花在各自独特的验证点上。

### 第三步：为每个 eval 编写 assertions

每个 eval 包含 5-10 个 assertions（断言）。断言是 grade.py 能自动验证的最小单元。

#### 断言类型

| 类型 | 说明 | 验证方式 | 示例 |
|------|------|---------|------|
| `structural` | 输出的格式和结构 | 关键词存在、正则匹配 | "输出包含 `# 审查报告` 标题" |
| `content` | 输出的语义内容 | 关键词匹配、近邻匹配 | "发现了 SQL 注入问题" |
| `checklist_ref` | 引用了特定编号 | 精确 ID 匹配 | "引用了 PY-24" |
| `checkpoint` | 行为控制（暂停、确认） | 关键词缺失检测 | "在阶段 2 后暂停，未继续执行阶段 3" |
| `file_exists` | 生成了特定文件 | 文件路径检测 | "生成了 SKILL.md 文件" |

#### 断言编写原则

1. **每个断言必须可程序化验证** — 如果需要人工判断"写得好不好"，那不是好的断言。改为"是否包含了关键词 X"或"是否引用了编号 Y"。

2. **分值反映重要性** — 核心行为的断言给 7-10 分，锦上添花的给 3-5 分。一个 eval 的总分通常在 38-65 分之间。

3. **断言 ID 格式** — 使用 `A{eval_id}-{seq:02d}` 格式，如 `A1-01`、`A3-07`。这在 grade.py 和 evals.json 之间建立映射关系。

4. **避免过宽关键词** — "使用"、"建议"这类极常见词容易造成假阳性。优先选择领域特定的关键词组合，或使用近邻正则（如 `r"(密码|password).{0,20}(日志|log)"`）。

5. **组合断言优于单一断言** — "发现了 SQL 注入"+ "引用了 PY-24"比单独验证任一项更有区分度。在 grade.py 中可以实现为：发现问题且引用编号 = 满分，只发现问题但没引用编号 = 也通过（skill 的核心目的是发现问题，编号引用是加分项）。

### 第四步：编写 evals.json

按照以下 JSON Schema 编写：

```json
{
  "skill_name": "目标 skill 的名称",
  "version": "1.0",
  "description": "一句话描述这个测试套件验证什么",
  "scoring": {
    "total_points": 100,
    "dimensions": {
      "维度key": {
        "weight": 25,
        "description": "这个维度衡量什么"
      }
    }
  },
  "evals": [
    {
      "id": 1,
      "name": "kebab-case-名称",
      "prompt": "模拟用户的输入（可以包含代码块、文档等）",
      "expected_output": "人类可读的期望行为描述（不被 grade.py 使用，仅供参考）",
      "assertions": [
        {
          "id": "A1-01",
          "text": "这个断言验证什么",
          "type": "structural",
          "points": 5
        }
      ]
    }
  ]
}
```

评分维度（dimensions）通常设 4-5 个，权重之和为 100。常见维度模式：
- **核心行为覆盖** (25-30)：skill 的主要功能是否触发
- **输出结构合规** (20-25)：格式是否符合 skill 定义的模板
- **内容质量** (15-25)：发现的问题/生成的内容是否准确有深度
- **规则遵循** (10-15)：编号引用、命名规范等细节
- **边界处理** (10-15)：模糊输入、不支持类型的处理

### 第五步：编写 grade.py

grade.py 是核心产出。它读取 eval 的输出文件，执行断言验证，输出评分结果。

#### 文件结构

参考 `references/grade-template.py` 获取完整模板。关键结构：

```
grade.py
├── 加载 evals.json
├── 收集输出内容
│   ├── collect_output(eval_dir) → str          # 适用于文本输出型 skill
│   └── collect_output_files(eval_dir) → dict   # 适用于文件生成型 skill
├── 通用检查函数
│   ├── check_keywords(content, keywords, min_hits)
│   ├── check_section_content(content, section_heading, keywords)
│   └── ... 根据目标 skill 的特点添加
├── 每个 eval 的评分函数
│   ├── grade_eval_1(content) → list[dict]
│   ├── grade_eval_2(content) → list[dict]
│   └── ... 
├── 计算分数
│   └── compute_score(eval_id, results, evals_data)
└── main() CLI 入口
```

#### 检查函数设计原则

1. **返回 (passed, evidence) 元组** — `passed` 是布尔值，`evidence` 是人类可读的证据字符串，用于调试和结果展示。

2. **不区分大小写** — 所有文本匹配使用 `.lower()` 或 `re.IGNORECASE`。

3. **处理 Markdown 格式** — 数字可能被 `**bold**` 包裹，标题可能有不同级别。正则中用 `\*{0,2}` 匹配可选的 bold 标记。

4. **正则提取分段时，注意标题层级** — 提取 `## 严重问题` 到下一个 `## 警告问题` 之间的内容时，用 `(?=\n## [^#]|\Z)` 而非 `(?=##|$)`，否则 `###` 子标题会中断匹配。

5. **Python 3.9 兼容** — 文件开头必须加 `from __future__ import annotations`，不要使用 `str | None` 语法。

#### 常见检查函数模板

参考 `references/check-functions-catalog.md` 获取可复用的检查函数清单。根据目标 skill 的输出特点，从中选取合适的函数，并根据需要编写领域专用的新函数。

### 第六步：运行 eval 并评分

1. **创建输出目录**：`mkdir -p evals/output/eval-{1,2,3,4,5}`

2. **运行 eval**：对每个 eval，启动一个 subagent：
   - 将 SKILL.md + 相关 references 内容注入 subagent 的 prompt
   - 将 eval 的 prompt 作为"用户输入"
   - 告诉 subagent"你已加载了这个 skill，请按照 skill 的工作流回应用户"
   - 将输出保存到 `evals/output/eval-N/response.md`（或对应的文件结构）

3. **运行评分**：`python3 grade.py evals/output`

4. **分析结果**：
   - 100% 通过 → skill 指令质量优秀
   - 90%+ → 检查失败项是 grade.py 的误判（正则不够宽容）还是 skill 的实际缺陷
   - <90% → skill 需要迭代改进，根据失败的断言调整 SKILL.md

5. **迭代**：
   - 如果是 **grade.py 误判**（如正则没考虑 markdown bold）→ 修 grade.py，重新评分
   - 如果是 **skill 缺陷**（如 skill 没有指导 AI 做某个关键步骤）→ 修 SKILL.md，重新运行 eval

## 输出清单

完成后，目标 skill 的 `evals/` 目录应包含：

```
evals/
├── evals.json       # 5 个测试用例 + 断言定义
├── grade.py         # 自动评分脚本
└── output/          # 运行 eval 后生成
    ├── eval-1/
    │   └── response.md   # 或其他输出文件
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

## 判断 eval 质量的标准

好的 eval 套件应满足：

1. **区分度** — 好 skill 得高分，差 skill 得低分。如果随便写的 skill 也能得 90+，说明断言太宽松。
2. **稳定性** — 同一个 skill 多次运行 eval，分数波动在 5% 以内。如果波动大，说明断言依赖了不确定的措辞而非核心行为。
3. **可调试性** — 每个失败的断言都有 `evidence` 字段解释为什么失败，便于判断是 skill 问题还是 grade.py 问题。
4. **无假阳性** — 不应该因为过宽的关键词给不合格的输出打通过分。
5. **合理覆盖** — 5 个 eval 覆盖了基本路径、变体、跨领域、模糊输入、边界降级五种场景。
