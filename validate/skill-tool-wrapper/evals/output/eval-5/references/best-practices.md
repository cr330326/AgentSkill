# AWS CDK — 跨服务通用最佳实践

本文件包含不属于某个具体 AWS 服务、但所有 CDK 项目都应遵循的最佳实践。
涵盖 Stack 组织、标签策略、环境管理、构造设计等跨服务主题。

## 目录
- [BP-01 ~ BP-05] Stack 组织与项目结构
- [BP-06 ~ BP-10] 标签与合规
- [BP-11 ~ BP-14] 环境管理与部署
- [BP-15 ~ BP-18] Construct 设计原则

---

## Stack 组织与项目结构

### BP-01 按领域拆分 Stack

禁止将所有资源放在单个 Stack 中。按业务领域或基础设施层拆分 Stack，
降低部署耦合度和 CloudFormation 模板大小风险。

**推荐的 Stack 拆分方式：**
```typescript
// ref: BP-01
const app = new cdk.App();

// 网络层
const networkStack = new NetworkStack(app, 'NetworkStack', {
  env: prodEnv,
});

// 数据层
const dataStack = new DataStack(app, 'DataStack', {
  env: prodEnv,
  vpc: networkStack.vpc,
});

// 应用层
const appStack = new ApplicationStack(app, 'ApplicationStack', {
  env: prodEnv,
  vpc: networkStack.vpc,
  table: dataStack.table,
});
```

### BP-02 Stack 命名规范

Stack 名称使用 `{项目}-{环境}-{领域}` 格式：

```typescript
// ref: BP-02
new NetworkStack(app, 'myproject-prod-network', { env: prodEnv });
new DataStack(app, 'myproject-prod-data', { env: prodEnv });
new ApplicationStack(app, 'myproject-prod-app', { env: prodEnv });
```

### BP-03 显式环境配置

所有 Stack 必须显式指定 `env`（account + region），禁止依赖 CDK 默认的环境推断。

```typescript
// ref: BP-03
const prodEnv: cdk.Environment = {
  account: '123456789012',
  region: 'ap-northeast-1',
};

new MyStack(app, 'ProdStack', { env: prodEnv });
```

### BP-04 跨 Stack 引用

Stack 之间的资源引用通过构造参数传递（props），不使用 `Fn.importValue`。

```typescript
// ref: BP-04
// 正确：通过 props 传递
interface AppStackProps extends cdk.StackProps {
  vpc: ec2.IVpc;
  table: dynamodb.ITable;
}

class ApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AppStackProps) {
    super(scope, id, props);
    // 使用 props.vpc 和 props.table
  }
}
```

### BP-05 项目目录结构

CDK 项目使用以下标准目录布局：

```
my-project/
├── bin/
│   └── app.ts               # CDK App 入口
├── lib/
│   ├── stacks/               # Stack 定义
│   │   ├── network-stack.ts
│   │   ├── data-stack.ts
│   │   └── app-stack.ts
│   └── constructs/           # 自定义 Construct
│       ├── secure-bucket.ts
│       └── monitored-function.ts
├── lambda/                   # Lambda 函数源码
│   ├── api/
│   └── processor/
├── test/                     # 测试
├── cdk.json
├── tsconfig.json
└── package.json
```

---

## 标签与合规

### BP-06 必须标签策略

所有资源必须带以下标签。使用 `cdk.Tags.of()` 在 Stack 或 App 级别统一添加。

| 标签键 | 说明 | 示例值 |
|--------|------|--------|
| `Project` | 项目名称 | `my-project` |
| `Environment` | 环境 | `prod` / `staging` / `dev` |
| `Owner` | 负责团队 | `platform-team` |
| `CostCenter` | 成本中心 | `CC-1234` |
| `ManagedBy` | 管理方式 | `cdk` |

```typescript
// ref: BP-06
cdk.Tags.of(app).add('Project', 'my-project');
cdk.Tags.of(app).add('Environment', props.environment);
cdk.Tags.of(app).add('Owner', 'platform-team');
cdk.Tags.of(app).add('CostCenter', 'CC-1234');
cdk.Tags.of(app).add('ManagedBy', 'cdk');
```

### BP-07 资源删除保护

生产环境的有状态资源（数据库、S3 存储桶、DynamoDB 表）必须设置
`removalPolicy: cdk.RemovalPolicy.RETAIN`，防止误删导致数据丢失。

```typescript
// ref: BP-07
const table = new dynamodb.Table(this, 'DataTable', {
  removalPolicy: props.environment === 'prod'
    ? cdk.RemovalPolicy.RETAIN
    : cdk.RemovalPolicy.DESTROY,
  // ...
});
```

### BP-08 启用 CloudFormation 终止保护

生产环境 Stack 必须启用终止保护：

```typescript
// ref: BP-08
new MyStack(app, 'ProdStack', {
  terminationProtection: true,
  env: prodEnv,
});
```

---

## 环境管理与部署

### BP-09 环境配置外部化

不同环境的配置通过 `cdk.json` 的 context 或单独的配置文件管理，禁止在代码中硬编码。

```typescript
// ref: BP-09
// cdk.json
{
  "context": {
    "environments": {
      "prod": {
        "account": "123456789012",
        "region": "ap-northeast-1",
        "vpcCidr": "10.0.0.0/16",
        "natGateways": 3
      },
      "dev": {
        "account": "987654321098",
        "region": "ap-northeast-1",
        "vpcCidr": "10.1.0.0/16",
        "natGateways": 1
      }
    }
  }
}
```

### BP-10 cdk diff 必须在 deploy 之前

部署流程中，`cdk diff` 必须在 `cdk deploy` 之前执行，且输出需要人工审查（生产环境）。

---

## Construct 设计原则

### BP-11 封装可复用 Construct

将常见的资源组合封装为 L3 Construct，确保团队内一致性：

```typescript
// ref: BP-11
export class MonitoredFunction extends Construct {
  public readonly function: lambda.Function;

  constructor(scope: Construct, id: string, props: MonitoredFunctionProps) {
    super(scope, id);

    this.function = new lambda.Function(this, 'Function', {
      runtime: lambda.Runtime.NODEJS_20_X,
      memorySize: props.memorySize ?? 256,
      timeout: props.timeout ?? cdk.Duration.seconds(15),
      ...props,
    });

    // 自动添加错误告警 (ref: LAM-13)
    this.function.metricErrors({
      period: cdk.Duration.minutes(5),
    }).createAlarm(this, 'ErrorAlarm', {
      threshold: 5,
      evaluationPeriods: 2,
    });

    // 自动添加标签 (ref: BP-06)
    cdk.Tags.of(this).add('ManagedBy', 'cdk');
  }
}
```

### BP-12 Construct Props 使用接口定义

所有自定义 Construct 的 props 必须使用 TypeScript 接口定义，
继承相关 CDK 接口，并为常用属性提供合理默认值。

```typescript
// ref: BP-12
export interface MonitoredFunctionProps {
  readonly entry: string;
  readonly handler?: string;
  readonly memorySize?: number;
  readonly timeout?: cdk.Duration;
  readonly environment?: Record<string, string>;
  readonly vpc?: ec2.IVpc;
}
```

### BP-13 使用 cdk-nag 进行合规检查

所有项目必须集成 `cdk-nag`，在 synth 阶段自动检查安全合规问题：

```typescript
// ref: BP-13
import { Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';

Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
```

### BP-14 快照测试

每个 Stack 必须有快照测试，防止意外的基础设施变更：

```typescript
// ref: BP-14
import { Template } from 'aws-cdk-lib/assertions';

test('Stack matches snapshot', () => {
  const app = new cdk.App();
  const stack = new MyStack(app, 'TestStack', { env: testEnv });
  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});
```
