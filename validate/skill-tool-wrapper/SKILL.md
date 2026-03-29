---
name: skill-tool-wrapper
description: >-
  Tool Wrapper 模式模板——帮助用户将任意库、框架、工具的规范文档和最佳实践封装为一个
  可按需加载的 Skill。当用户想要"创建工具封装 skill"、"把框架文档打包成 skill"、
  "封装 SDK 使用规范"、"团队编码规范分发"、"create a tool wrapper skill"、
  "wrap a framework into a skill"、"把 XXX 的最佳实践做成 skill" 时使用此模板。
  即使用户只是说"帮我做一个 FastAPI/React/Vue 的 skill"，也应该参考此模板的结构。
---

# Tool Wrapper — 工具封装 Skill 模板

## 这个 Skill 是什么

Tool Wrapper 是一种 **Skill 设计模式**，而非某个具体工具的封装。它解决的问题是：

> 团队有一套技术栈的编码规范、最佳实践和示例代码，希望 AI 编程助手在写代码时自动遵循，
> 但又不想把这些文档永远塞在系统提示里浪费上下文。

这个模板定义了标准的目录结构和工作流，让你可以快速为任意工具/框架创建一个封装 Skill。
`references/` 目录下包含一个 FastAPI 的示范封装，展示具体应该怎么写。

## 目录结构模板

每个 Tool Wrapper Skill 应遵循以下结构：

```
<tool-name>-wrapper/
├── SKILL.md                    # 入口：触发条件 + 工作流 + 加载策略
└── references/
    ├── conventions.md          # 编码规范与约定（必须遵循的规则）
    ├── best-practices.md       # 最佳实践（推荐但非强制的模式）
    └── examples.md             # 示例代码（可直接参考的代码片段）
```

三份文档的分工：
- **conventions.md**：硬性规则。违反了就是 bug 或不合规。比如命名规范、目录结构约定、错误码定义。
- **best-practices.md**：软性建议。遵循可以获得更好的效果，但不是必须的。比如性能优化技巧、推荐的设计模式。
- **examples.md**：参考实现。展示 conventions 和 best-practices 在实际代码中的样子。用户说"帮我写个 XXX"时直接参考这里的风格。

如果你的工具文档较多（比如超过 300 行），可以按主题进一步拆分：
```
references/
├── conventions.md
├── best-practices-api.md
├── best-practices-testing.md
├── examples-crud.md
└── examples-auth.md
```

这样模型可以按需只加载需要的部分，而非一次性全部读入。

## 如何创建一个新的 Tool Wrapper Skill

### 第一步：确定封装范围

问自己这几个问题：
1. 这个工具/框架的哪些知识是模型不太可能自带的？（训练数据已经覆盖的通用知识不需要封装）
2. 团队有哪些**自定义的**约定和规范？（这才是封装的核心价值）
3. 用户会用什么关键词/短语来触发这个 skill？

### 第二步：编写 SKILL.md

SKILL.md 是入口文件，包含三个核心部分：

**1) YAML frontmatter — 触发配置**

```yaml
---
name: <tool-name>-wrapper
description: >-
  <工具名称>的编码规范和最佳实践封装。当用户使用 <工具名称> 开发时自动加载
  团队约定的规范、推荐模式和示例代码。当用户提到"<工具名称>"、"<常见缩写>"、
  "<相关关键词>"时使用此 skill。
---
```

description 要写得具体，包含用户真实会说的话。参考 `references/example-fastapi-skill.md`
中的示范。

**2) 工作流 — 告诉模型什么时候加载什么**

不要一上来就全部加载。按需渐进：

| 用户操作 | 加载内容 |
|---------|---------|
| 提到工具名，但还在讨论阶段 | 只读 SKILL.md 本身，了解有哪些规范可用 |
| 开始写代码 | 加载 `conventions.md`（硬性规则不能违反） |
| 遇到具体实现问题 | 加载对应的 `best-practices-*.md` |
| 需要参考实现 | 加载对应的 `examples-*.md` |

**3) 输出要求 — 告诉模型怎么用加载的文档**

关键原则：
- conventions.md 中的规则优先级高于模型自带的通用知识
- 如果 conventions.md 和模型的通用知识冲突，以 conventions.md 为准（这是团队自定义规范的意义）
- 输出代码时应标注哪些地方遵循了规范中的哪条规则（便于审查）

### 第三步：编写 references/ 文档

每份文档遵循这个格式：

```markdown
# <文档标题>

## 目录
- [XXX-01 ~ XXX-05] 分类一
- [XXX-06 ~ XXX-10] 分类二
...

---

## 分类一

### XXX-01 规则/实践名称
具体内容。如果是规范，说明什么是允许的、什么是禁止的。
如果是最佳实践，解释为什么推荐这样做。

**正确示例：**
（代码片段）

**错误示例：**
（代码片段 + 解释为什么错）
```

每条规则用编号前缀（如 `FAPI-01`、`REACT-01`），方便在审查报告中引用。

### 第四步：编写 description 触发词

description 是 skill 能否被正确触发的关键。要点：
- 包含工具的全名和常见缩写
- 包含用户真实会说的短语（中英文都要）
- 稍微"激进"一点——宁可多触发也不要漏触发
- 覆盖模糊意图（用户可能不会说"加载 FastAPI 规范"，而是说"帮我写个 FastAPI 接口"）

## 示范：FastAPI Wrapper Skill

`references/` 目录下包含一个完整的 FastAPI 封装示范：

- `references/example-fastapi-skill.md` — 一个完整的 FastAPI wrapper 的 SKILL.md 示范
- `references/example-fastapi-conventions.md` — FastAPI 编码规范示范
- `references/example-fastapi-best-practices.md` — FastAPI 最佳实践示范

创建新的 Tool Wrapper Skill 时，可以参照这些示范文件的结构和写法，替换为自己工具的内容。

## 常见问题

**Q: references/ 里的文档应该写多详细？**
每份文档控制在 200-300 行以内。如果超过了，按主题拆分为多个文件，让模型按需加载。

**Q: 如何处理工具版本更新？**
在 conventions.md 开头标注适用的版本范围。版本更新时只需更新 references/ 下的文档，
SKILL.md 的工作流逻辑通常不需要改动。

**Q: 这个模式和直接把文档放到 .cursorrules / CLAUDE.md 有什么区别？**
主要区别是**按需加载**。.cursorrules 始终在上下文中，会占用 token 额度。
Skill 模式只在用户触发相关关键词时才加载，适合文档量较大或有多个技术栈的场景。
