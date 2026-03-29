---
name: skill-inversion
description: 反转模式，Agent先收集全必要信息再执行操作，避免猜测导致错误
metadata: {"emoji: "❓", "requires": {"dirs": ["assets/"]}}
---
# Inversion Skill
## 用途
反转传统Agent直接生成流程，Agent先作为面试官向用户提问，收集齐所有必要信息后再执行操作，避免猜测用户需求导致错误。
适合场景：
- 项目规划
- 需求确认
- 复杂任务拆解
- 配置初始化
## 结构
```
inversion/
├── SKILL.md
└── assets/
    ├── project-planning-questions.md # 项目规划问题清单
    └── requirement-collect-questions.md # 需求收集问题清单
```
## 使用规则
1. 接到对应任务时，首先加载`assets/`下对应场景的问题清单
2. 按顺序逐个向用户提问，每次只提一个问题
3. 所有问题没有全部得到用户回答前，禁止执行任何实际操作
4. 收集齐所有答案后，再按规则执行任务
## 激活条件
当用户输入包含以下关键词时自动激活：
- 项目规划, 需求确认, 初始化配置, 新建项目
## 输出要求
必须严格遵循门控规则，未完成所有问题收集禁止输出最终结果。
