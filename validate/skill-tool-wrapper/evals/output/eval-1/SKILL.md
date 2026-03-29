---
name: react-wrapper
description: >-
  React + TypeScript 前端项目的组件规范、状态管理约定和最佳实践封装。当用户使用
  React 开发前端时，自动加载团队约定的组件设计规范、TypeScript 类型约定、
  状态管理模式和推荐的项目结构。当用户提到"React"、"react"、"组件"、"component"、
  "前端"、"frontend"、"TypeScript"、"tsx"、"hooks"、"状态管理"、"state management"、
  "写个页面"、"写个组件"、"创建组件"、"create component"、"React 开发"、
  "前端开发"、"UI 组件"时使用此 skill。即使用户没有明确提到 React，只要他们在写
  TypeScript 前端组件相关代码，也应考虑使用此 skill。
---

# React + TypeScript 编码规范与最佳实践

## 何时加载哪份文档

| 场景 | 加载 |
|------|------|
| 新建 React 项目或讨论项目结构 | `conventions.md`（项目结构部分） |
| 编写组件、页面 | `conventions.md` + `best-practices.md` |
| 涉及状态管理、数据流设计 | `conventions.md`（状态管理部分）+ `best-practices.md`（性能优化部分） |
| 编写自定义 Hook 或工具函数 | `best-practices.md`（Hook 设计部分） |
| 做 code review | 全部加载，逐条对照 |

## 工作流

1. 用户开始 React + TypeScript 开发时，先加载 `references/conventions.md`
2. 所有生成的代码必须符合 conventions 中的规则
3. 遇到设计选择时（如状态管理方案、组件拆分策略），参考 `references/best-practices.md`
4. 如果 conventions 中的规则与 React 官方文档冲突，以 conventions 为准（团队约定优先）

## 输出要求

- 代码中涉及规范条目时，用注释标注编号（如 `// ref: REACT-03`）
- 生成的项目结构必须符合 conventions 中定义的目录布局
- 组件必须使用 conventions 中定义的命名规范和类型约定
- 状态管理必须遵循 conventions 中定义的分层模式
