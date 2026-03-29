---
name: go-team-wrapper
description: >-
  Go 项目团队编码规范与最佳实践封装。当用户使用 Go 开发时，自动加载团队约定的
  错误处理、日志、HTTP handler、配置管理等规范。当用户提到"Go"、"Golang"、
  "golang"、"go 代码"、"写个 Go 服务"、"Go HTTP"、"Go handler"、"Go 接口"、
  "Go 微服务"、"go run"、"go build"、"Go 项目"时使用此 skill。
  即使用户没有明确提到 Go，只要他们在写 .go 文件或讨论 Go 相关代码，
  也应考虑使用此 skill。
---

# Go 团队编码规范与最佳实践

## 为什么用 tool-wrapper skill 模式

你的需求非常适合用 **tool-wrapper**（工具封装）模式来解决。

传统做法是把团队编码规范写到 `.cursorrules` 或 `CLAUDE.md` 里，但这种方式有明显的缺点：这些文件**始终加载在上下文中**，无论用户当前是否在写 Go 代码都会占用 token 额度。当团队有多个技术栈（Go、Python、前端等）的规范时，上下文会被大量无关内容挤占，影响 AI 助手的响应质量。

**Skill 模式**（按需加载）解决了这个问题：

- **按需加载**：只有当用户触发 Go 相关关键词时才加载规范文档，不浪费 context window
- **封装隔离**：每个技术栈的规范独立封装为一个 wrapper skill，互不干扰
- **渐进式加载**：先加载硬性规则（conventions），遇到具体问题再加载最佳实践（best-practices），避免一次性灌入过多内容
- **易于维护**：规范更新只需修改 `references/` 下的文档，不影响其他 skill

相比把所有规范塞进 `.cursorrules` / `CLAUDE.md`，tool-wrapper skill 模式在 token 使用效率和维护性上都更优。

## 何时加载哪份文档

| 场景 | 加载内容 |
|------|---------|
| 用户提到 Go，但还在讨论/规划阶段 | 只读 SKILL.md 本身，了解可用规范 |
| 开始写 Go 代码 | 加载 `references/conventions.md`（硬性规则） |
| 遇到设计选择或实现细节问题 | 加载 `references/best-practices.md` |
| 做 code review / 代码审查 | 全部加载，逐条对照检查 |

## 工作流

1. 用户开始 Go 开发时，先加载 `references/conventions.md`
2. 所有生成的代码**必须**符合 conventions 中的规则（编号 GO-01 ~ GO-08）
3. 遇到架构设计、性能调优等问题时，参考 `references/best-practices.md`（编号 BP-01 ~ BP-10）
4. 如果 conventions 中的规则与 Go 社区通用惯例冲突，**以 conventions 为准**（团队约定优先）

## 输出要求

- 代码中涉及规范条目时，用注释标注编号（如 `// ref: GO-03`）
- 错误处理必须使用 `pkg/errors` 包装，禁止裸返回原始 error
- 日志统一使用 `go.uber.org/zap`，禁止 `log` 标准库
- HTTP handler 签名统一为 `func(w http.ResponseWriter, r *http.Request)`
- 配置管理使用 `viper` 从 YAML 文件读取
