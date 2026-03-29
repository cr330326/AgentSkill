---
name: skill-tool-wrapper
description: 工具封装模式，将特定库/框架/工具的规范文档、最佳实践打包成Skill，按需动态加载
metadata: {"emoji: "📦", "requires": {"dirs: ["references/"]}}
---
# Tool Wrapper Skill
## 用途
将特定技术栈、工具、框架的规范文档、最佳实践、使用指南打包成Skill，只有当用户触发对应关键词时才动态加载相关文档，避免占用不必要的上下文占用。
适合场景：
- 团队内部编码规范分发
- 特定框架/SDK的最佳实践
- 专用工具的使用指引
## 结构
```
tool-wrapper/
├── SKILL.md
└── references/
    ├── conventions.md # 规范文档
    ├── best-practices.md # 最佳实践
    └── examples.md # 示例代码
```
## 使用规则
1. 当用户提及或开始使用对应技术/工具/框架时，自动加载`references/`目录下的所有文档
2. 所有输出必须严格遵循`references/conventions.md`中的规范
3. 优先使用`references/best-practices.md`中推荐的实现方式
4. 示例代码必须参考`references/examples.md`中的风格
## 激活条件
当用户输入包含以下关键词时自动激活：
- fastapi, spring-boot, react, vue, 编码规范, SDK使用
## 输出要求
所有输出必须符合加载的规范文档要求，禁止输出不符合规范的代码/内容。
