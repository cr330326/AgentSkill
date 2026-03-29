---
name: skill-reviewer
description: 审查模式，基于动态加载审查清单，输出结构化审查结果
metadata: {"emoji: "🔍", "requires": {"dirs": ["references/"]}}
---
# Reviewer Skill
## 用途
分离审查标准和审查逻辑，动态加载不同的检查清单，实现各类专项审查，输出结构化结果。
适合场景：
- 代码风格审查
- 安全漏洞审计
- 文档质量检查
- 发布前合规检查
## 结构
```
reviewer/
├── SKILL.md
└── references/
    ├── python-review-checklist.md # Python代码审查清单
    ├── owasp-checklist.md # OWASP安全检查清单
    └── doc-quality-checklist.md # 文档质量检查清单
```
## 使用规则
1. 接到审查任务时，根据审查类型加载对应`references/`下对应的审查清单
2. 逐条对照清单检查待审查内容
3. 输出按「严重程度分组的结构化审查结果：
   - 严重问题：必须修复
   - 警告问题：建议修复
   - 优化建议：可选优化
4. 每个问题必须包含：问题位置、问题描述、修复建议
## 激活条件
当用户输入包含以下关键词时自动激活：
- 代码审查, 安全审计, 质量检查, 合规检查, 代码评审
## 输出要求
禁止无依据的主观评价，所有问题必须对应审查清单中的条目。
