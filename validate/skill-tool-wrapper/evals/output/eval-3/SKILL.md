---
name: terraform-wrapper
description: >-
  Terraform IaC 项目的编码规范和最佳实践封装。当用户使用 Terraform 管理基础设施时，
  自动加载团队约定的模块结构、变量规范、状态管理和部署流程。当用户提到
  "Terraform"、"terraform"、"HCL"、"hcl"、"基础设施即代码"、"IaC"、
  "infrastructure as code"、"infrastructure"、"基础设施"、"tf 文件"、
  "terraform plan"、"terraform apply"、"terraform module"、"写个模块"、
  "创建资源"、"管理云资源"、"state 管理"、"远程状态"时使用此 skill。
  即使用户没有明确提到 Terraform，只要在写 .tf 文件或讨论云基础设施编排，
  也应考虑使用此 skill。
---

# Terraform 编码规范与最佳实践

## 何时加载哪份文档

| 场景 | 加载 |
|------|------|
| 新建 Terraform 项目或模块 | `conventions.md`（目录结构与命名部分） |
| 编写资源定义 / 变量 / 输出 | `conventions.md` + `best-practices.md` |
| 配置后端或状态管理 | `conventions.md`（状态管理部分） |
| 执行 plan / apply 流程 | `conventions.md`（部署流程部分） |
| 做 code review | 全部加载，逐条对照 |

## 工作流

1. 用户开始 Terraform 开发时，先加载 `references/conventions.md`
2. 所有生成的 HCL 代码必须符合 conventions 中的规则
3. 遇到架构设计选择时（如模块拆分、workspace 策略），参考 `references/best-practices.md`
4. 如果 conventions 中的规则与 Terraform 官方文档冲突，以 conventions 为准（团队约定优先）

## 输出要求

- 代码中涉及规范条目时，用注释标注编号（如 `# ref: TF-03`）
- 生成的项目结构必须符合 conventions 中定义的目录布局
- 所有 backend 配置必须使用 S3，禁止生成 local backend
- plan 输出必须保存为文件，apply 必须引用该文件
- 变量定义必须包含 `description` 字段
