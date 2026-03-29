---
name: aws-cdk-wrapper
description: >-
  AWS CDK (TypeScript) 基础设施即代码的编码规范和最佳实践封装。当用户使用 AWS CDK
  定义云基础设施时，自动加载团队约定的 VPC、Lambda、DynamoDB、IAM、CloudFront、
  S3、Step Functions、API Gateway 等服务的配置规范。当用户提到"CDK"、"AWS CDK"、
  "基础设施"、"infrastructure"、"IaC"、"云资源"、"stack"、"construct"、
  "cdk deploy"、"cdk synth"时使用此 skill。即使用户没有明确提到 CDK，只要他们
  在用 TypeScript 定义 AWS 资源，也应考虑使用此 skill。
---

# AWS CDK (TypeScript) 编码规范与最佳实践

## 文件拆分策略

本 Skill 涵盖 8 个 AWS 服务的配置规范，每个服务有 30-50 条规则。如果合并为单个文件，
将远超 300 行的建议上限，会造成上下文浪费和加载缓慢。因此，我们**按服务拆分为多个文件**，
每个服务的规范放在单独文件中，模型按需加载用户当前涉及的服务规范即可。

拆分原则：
- **按服务拆分**（per service）：每个 AWS 服务的规范放在单独文件中
- **多个文件**按需加载，避免一次性全部读入
- 每个单独文件控制在 300 行以内；如果某个服务的规则超过 300 行，需进一步按子主题拆分，并在文件开头提供**目录（TOC）**索引
- 跨服务的通用最佳实践（如标签策略、Stack 组织）集中在 `best-practices.md`

## 文件目录

```
aws-cdk-wrapper/
├── SKILL.md                              # 入口：触发条件 + 加载策略
└── references/
    ├── conventions-vpc.md                # VPC 配置规范 (VPC-01 ~ VPC-xx)
    ├── conventions-lambda.md             # Lambda 函数规范 (LAM-01 ~ LAM-xx)
    ├── conventions-dynamodb.md           # DynamoDB 表设计规范 (DDB-01 ~ DDB-xx)
    ├── conventions-iam.md                # IAM 策略规范 (IAM-01 ~ IAM-xx)
    ├── conventions-cloudfront.md         # CloudFront 分发规范 (CF-01 ~ CF-xx)
    ├── conventions-s3.md                 # S3 存储桶规范 (S3-01 ~ S3-xx)
    ├── conventions-stepfunctions.md      # Step Functions 工作流规范 (SF-01 ~ SF-xx)
    ├── conventions-apigateway.md         # API Gateway 配置规范 (APIGW-01 ~ APIGW-xx)
    └── best-practices.md                 # 跨服务通用最佳实践 (BP-01 ~ BP-xx)
```

## 按需加载策略

根据用户提到的 AWS 服务，**只加载对应的规范文件**，不要一次性全部读入：

| 用户操作 / 提到的关键词 | 加载内容 |
|--------------------------|----------|
| 提到 CDK 但还在讨论阶段 | 只读 SKILL.md 本身，了解有哪些规范可用 |
| 提到 VPC、子网、安全组、NAT Gateway | `references/conventions-vpc.md` |
| 提到 Lambda、函数、handler、冷启动 | `references/conventions-lambda.md` |
| 提到 DynamoDB、表、分区键、GSI | `references/conventions-dynamodb.md` |
| 提到 IAM、角色、策略、权限 | `references/conventions-iam.md` |
| 提到 CloudFront、分发、CDN、缓存策略 | `references/conventions-cloudfront.md` |
| 提到 S3、存储桶、桶策略、生命周期 | `references/conventions-s3.md` |
| 提到 Step Functions、状态机、工作流 | `references/conventions-stepfunctions.md` |
| 提到 API Gateway、REST API、HTTP API | `references/conventions-apigateway.md` |
| Stack 组织、标签、通用模式 | `references/best-practices.md` |
| Code review / 全面审查 | 加载涉及到的服务的规范 + `best-practices.md` |

如果用户同时涉及多个服务（例如"创建一个 Lambda 并配置 VPC"），同时加载对应的多个文件。

## 工作流

1. 用户开始 CDK 开发时，先加载 `references/best-practices.md`（通用规范）
2. 根据用户涉及的具体服务，按上表加载对应的 conventions 文件
3. 所有生成的 CDK 代码必须符合已加载的规范文件中的规则
4. 如果规范中的规则与 AWS CDK 官方文档冲突，以本规范为准（团队约定优先）
5. 同一个任务涉及多个服务时，逐个加载对应文件，不要一次全部读入

## 输出要求

- 代码中涉及规范条目时，用注释标注编号（如 `// ref: VPC-03`、`// ref: LAM-05`）
- 生成的 Stack 结构必须符合 `best-practices.md` 中定义的组织方式
- IAM 策略必须遵循最小权限原则（`conventions-iam.md`）
- 所有资源必须打标签（`best-practices.md` 中的标签策略）
