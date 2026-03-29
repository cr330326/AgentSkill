# 示范：FastAPI Wrapper Skill 的 SKILL.md

以下是一个完整的 FastAPI Tool Wrapper Skill 的 SKILL.md 示范。
创建你自己的 wrapper 时，可以参照这个结构，替换为你的工具内容。

---

```yaml
---
name: fastapi-wrapper
description: >-
  FastAPI 项目的编码规范和最佳实践。当用户使用 FastAPI 构建 API 时，自动加载
  团队约定的项目结构、路由规范、错误处理模式和示例代码。当用户提到"FastAPI"、
  "fastapi"、"写个接口"、"API 开发"、"创建 endpoint"、"路由"时使用此 skill。
  即使用户没有明确提到 FastAPI，只要他们在写 Python Web API 相关代码，
  也应考虑使用此 skill。
---
```

```markdown
# FastAPI 编码规范与最佳实践

## 何时加载哪份文档

| 场景 | 加载 |
|------|------|
| 新建 FastAPI 项目 | `conventions.md`（项目结构部分） |
| 编写路由/接口 | `conventions.md` + `best-practices.md` |
| 需要参考代码 | `examples.md`（按需加载对应模块的示例） |
| 做 code review | 全部加载，逐条对照 |

## 工作流

1. 用户开始 FastAPI 开发时，先加载 `references/conventions.md`
2. 所有生成的代码必须符合 conventions 中的规则
3. 遇到设计选择时（如认证方案、分页策略），参考 `references/best-practices.md`
4. 需要提供完整代码示例时，参考 `references/examples.md` 的风格
5. 如果 conventions 中的规则与 FastAPI 官方文档冲突，以 conventions 为准（团队约定优先）

## 输出要求

- 代码中涉及规范条目时，用注释标注编号（如 `# ref: FAPI-03`）
- 生成的项目结构必须符合 conventions 中定义的目录布局
- 错误处理必须使用 conventions 中定义的错误码体系
```
