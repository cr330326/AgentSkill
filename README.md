# AgentSkill

面向 Agent Skills 设计与评估的开源资料仓库。

这个项目聚焦两个核心问题：

- 如何把一个 Skill 写成可触发、可路由、可维护的结构
- 如何用可复用的标准、脚本和模板评估一个 Skill 的质量

如果你正在设计自己的 Skill 体系，或者想为团队建立一套更清晰的 Skill 评审方法，这个仓库可以作为起点。

## Why This Repo

很多 Skill 文档会在两个方向上失控：

- 触发描述太泛，导致该触发时触发不到，不该触发时又容易误触发
- 主文件塞入过多细节，导致上下文噪声大、token 浪费高、后期维护困难

这个仓库围绕“渐进式披露”整理了一套更稳妥的实践方式：

1. 用 description 做入口层，解决触发问题
2. 用 SKILL.md 做主路由，解决任务分流问题
3. 用 reference、templates、scripts、examples 等目录做按需加载资源，解决知识组织问题

## What You Will Find

| 模块 | 作用 | 适合谁 |
|------|------|--------|
| [committing](committing) | 一个小而专一的提交辅助 Skill 示例 | 想看简单 Skill 写法的人 |
| [skill-evaluator](skill-evaluator) | Skill 评估主模块，包含标准、脚本、模板和示例 | 想审核或改进 Skill 的人 |
| [doc](doc) | 渐进式披露方法论文档 | 想理解架构设计原则的人 |

## Repository Layout

```text
AgentSkill/
├── committing/
│   └── SKILL.md
├── doc/
│   └── 循序渐进：渐进式披露架构设计.md
└── skill-evaluator/
    ├── SKILL.md
    ├── examples/
    │   ├── bad_skill.md
    │   └── good_skill.md
    ├── reference/
    │   ├── content_quality.md
    │   ├── progressive_disclosure.md
    │   └── structure_standards.md
    ├── scripts/
    │   └── analyze_skill.py
    └── templates/
        └── evaluation_report.md
```

## Start Here

### 1. 先理解方法论

建议先读这篇文档，建立对“渐进式披露”的整体认识：

- [doc/循序渐进：渐进式披露架构设计.md](doc/%E5%BE%AA%E5%BA%8F%E6%B8%90%E8%BF%9B%EF%BC%9A%E6%B8%90%E8%BF%9B%E5%BC%8F%E6%8A%AB%E9%9C%B2%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1.md)

### 2. 再看评估器如何组织知识

如果你想看一个更完整的 Skill 设计样例，优先阅读这些文件：

- [skill-evaluator/SKILL.md](skill-evaluator/SKILL.md)
- [skill-evaluator/reference/structure_standards.md](skill-evaluator/reference/structure_standards.md)
- [skill-evaluator/reference/content_quality.md](skill-evaluator/reference/content_quality.md)
- [skill-evaluator/reference/progressive_disclosure.md](skill-evaluator/reference/progressive_disclosure.md)

### 3. 使用脚本做基线检查

仓库提供了一个静态分析脚本，可以对某个 Skill 目录或单个 SKILL.md 做基础检查：

```bash
python skill-evaluator/scripts/analyze_skill.py <path-to-skill-or-skill-md>
```

示例：

```bash
python skill-evaluator/scripts/analyze_skill.py skill-evaluator
python skill-evaluator/scripts/analyze_skill.py committing/SKILL.md
```

如果你要把结果接到其他流程里，可以使用 JSON 输出：

```bash
python skill-evaluator/scripts/analyze_skill.py <path> --json
```

### 4. 用模板输出评审结果

正式评估时，可以直接使用报告模板：

- [skill-evaluator/templates/evaluation_report.md](skill-evaluator/templates/evaluation_report.md)

## Example Workflow

如果你想评估一个新的 Skill，推荐按下面的顺序走：

1. 明确这个 Skill 的目标、触发条件和边界。
2. 运行 analyze_skill.py 获取确定性基线信号。
3. 根据问题类型阅读对应标准：
   - 结构设计问题，看 [skill-evaluator/reference/structure_standards.md](skill-evaluator/reference/structure_standards.md)
   - 内容和路由问题，看 [skill-evaluator/reference/content_quality.md](skill-evaluator/reference/content_quality.md)
   - token 效率和文件拆分问题，看 [skill-evaluator/reference/progressive_disclosure.md](skill-evaluator/reference/progressive_disclosure.md)
4. 用 [skill-evaluator/examples/good_skill.md](skill-evaluator/examples/good_skill.md) 和 [skill-evaluator/examples/bad_skill.md](skill-evaluator/examples/bad_skill.md) 做对照校准。
5. 用 [skill-evaluator/templates/evaluation_report.md](skill-evaluator/templates/evaluation_report.md) 整理出结构化结论和改进建议。

## Design Principles

这个仓库持续强调同一件事：主文件应该是路由器，不是手册全文。

一个质量更高的 Skill 通常具备这些特征：

- description 足够具体，能帮助系统正确触发
- SKILL.md 负责判断路径，而不是堆满低频细节
- 辅助资料按职责拆分到清晰的目录中
- 脚本承担确定性工作，模板承担输出规范，示例承担校准作用

这套拆分方式的价值不只是节省 token，也能显著降低后续迭代成本。

## Who This Repo Is For

- 正在编写或重构 Skill 的开发者
- 需要建立 Skill Review 流程的团队
- 想系统理解渐进式披露设计方法的学习者
- 希望把经验沉淀成标准、模板和可执行检查工具的人

## Requirements

- Python 3，用于运行 [skill-evaluator/scripts/analyze_skill.py](skill-evaluator/scripts/analyze_skill.py)
- 任意支持 Markdown 的编辑器，用于阅读文档和编写评估报告

当前仓库是轻量结构，没有复杂依赖，也没有单独的构建流程。

## Contributing

欢迎围绕以下方向补充内容：

- 新的真实 Skill 示例
- 更精细的评估标准和反例
- 更强的静态分析规则或报告导出能力
- 更清晰的教学材料与案例

如果你准备提交改动，建议保持以下原则：

- 示例尽量小而清晰，避免一次塞入过多职责
- 标准文件优先讲判断依据，不只给结论
- 脚本输出应可复现、可解释，便于人工复核
- 目录命名保持语义明确，避免模糊文件名

## Project Status

这个项目目前更像一个开放的参考库，而不是一个完整产品。

它已经适合用于：

- Skill 设计学习
- 团队内部评审基线搭建
- 渐进式披露架构教学与讨论

后续自然的扩展方向包括：

- 增加更多面向不同场景的 Skill 样例
- 补充更完整的评估自动化能力
- 增加贡献规范、版本说明和许可证文件