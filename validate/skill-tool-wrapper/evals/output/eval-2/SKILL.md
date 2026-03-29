---
name: drf-wrapper
description: >-
  Django REST Framework (DRF) 项目的编码规范和最佳实践封装。当用户使用 DRF 构建
  后端 API 时，自动加载团队约定的 ViewSet 规范、序列化器规则、权限管理和路由注册模式。
  当用户提到"Django REST Framework"、"DRF"、"django rest"、"REST framework"、
  "ViewSet"、"Serializer"、"序列化器"、"写个接口"、"后端 API"、"Django API"、
  "create endpoint"、"API view"、"Django 后端"、"REST 接口"时使用此 skill。
  即使用户没有明确提到 DRF，只要他们在写 Django Web API 相关代码，也应考虑使用此 skill。
---

# Django REST Framework 编码规范与最佳实践

## 何时加载哪份文档

| 场景 | 加载 |
|------|------|
| 提到 DRF / Django API，但还在讨论阶段 | 只读 SKILL.md 本身，了解有哪些规范可用 |
| 新建 DRF 项目或 app | `conventions.md`（项目结构 + 团队自定义规则） |
| 编写 ViewSet / Serializer / URL | `conventions.md`（全部） |
| 遇到性能、安全、分页等实现问题 | `best-practices.md`（按需加载对应章节） |
| 做 code review | 全部加载，逐条对照 |

## 工作流

1. 用户开始 DRF 开发时，先加载 `references/conventions.md`
2. 所有生成的代码必须符合 conventions 中的规则——尤其是标记为 **[团队自定义]** 的四条硬性约定
3. 遇到设计选择时（如分页策略、限流方案、过滤后端），参考 `references/best-practices.md`
4. 如果 conventions 中的规则与 DRF 官方文档或模型自带知识冲突，以 conventions 为准（团队约定优先）

## 输出要求

- 代码中涉及规范条目时，用注释标注编号（如 `# ref: DRF-01`）
- 生成的代码必须使用 ViewSet 而非 APIView（`DRF-01`）
- 序列化器必须继承 BaseSerializer（`DRF-02`）
- 权限类必须定义在 permissions.py 中（`DRF-03`）
- URL 路由必须使用 DefaultRouter 注册（`DRF-04`）
- 以上四条为团队硬性约定，不可违反
