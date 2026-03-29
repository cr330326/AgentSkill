# AWS CDK — Lambda 函数规范

本文件定义 Lambda 函数的 CDK 配置规范，涵盖运行时、内存、超时、打包、
环境变量、层（Layer）、并发等方面的硬性规则。

## 目录
- [LAM-01 ~ LAM-05] 基础配置
- [LAM-06 ~ LAM-10] 打包与依赖
- [LAM-11 ~ LAM-15] 安全与权限
- [LAM-16 ~ LAM-18] 性能与并发
- [LAM-19 ~ LAM-20] 监控与告警

---

## 基础配置

### LAM-01 运行时版本

统一使用 Node.js 20.x 运行时。禁止使用已停止维护的运行时版本（Node.js 16.x 及更早）。
新函数必须使用 `Runtime.NODEJS_20_X`。

```typescript
// ref: LAM-01
const fn = new lambda.Function(this, 'MyFunction', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/my-function'),
});
```

### LAM-02 内存与超时配置

每个 Lambda 函数必须显式设置 `memorySize` 和 `timeout`，禁止使用默认值。
- API 触发的函数：timeout 不超过 30 秒，memorySize 128-512 MB
- 后台处理函数：timeout 不超过 900 秒，memorySize 根据需要设置
- 必须留出比实际处理时间至少 20% 的余量

```typescript
// ref: LAM-02
// API 处理函数
const apiHandler = new lambda.Function(this, 'ApiHandler', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/api'),
  memorySize: 256,
  timeout: cdk.Duration.seconds(15),
});

// 后台处理函数
const processor = new lambda.Function(this, 'Processor', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/processor'),
  memorySize: 1024,
  timeout: cdk.Duration.minutes(5),
});
```

### LAM-03 函数命名规范

函数名使用 `{项目}-{环境}-{功能}` 格式。CDK 构造 ID 使用 PascalCase。

```typescript
// ref: LAM-03
const fn = new lambda.Function(this, 'OrderProcessor', {
  functionName: `${props.projectName}-${props.environment}-order-processor`,
  // ...
});
```

### LAM-04 环境变量管理

敏感信息（API Key、数据库密码）禁止放在环境变量中，必须使用 Secrets Manager
或 SSM Parameter Store。非敏感配置项可以使用环境变量。

**正确示例：**
```typescript
// ref: LAM-04
const secret = secretsmanager.Secret.fromSecretNameV2(
  this, 'DbSecret', 'prod/db/password'
);

const fn = new lambda.Function(this, 'MyFunction', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/my-function'),
  environment: {
    TABLE_NAME: table.tableName,       // 非敏感：允许
    REGION: cdk.Stack.of(this).region, // 非敏感：允许
    SECRET_ARN: secret.secretArn,      // 传 ARN，运行时读取值
  },
});

secret.grantRead(fn);
```

**错误示例：**
```typescript
// 错误：密码直接写在环境变量中
const fn = new lambda.Function(this, 'MyFunction', {
  environment: {
    DB_PASSWORD: 'my-secret-password', // 绝对禁止
  },
});
```

### LAM-05 描述字段

每个 Lambda 函数必须设置 `description` 字段，说明函数用途。

```typescript
// ref: LAM-05
const fn = new lambda.Function(this, 'OrderProcessor', {
  description: 'Processes incoming orders from SQS queue and writes to DynamoDB',
  // ...
});
```

---

## 打包与依赖

### LAM-06 使用 NodejsFunction 构造

TypeScript Lambda 函数使用 `NodejsFunction`（aws-cdk-lib/aws-lambda-nodejs），
自动处理 esbuild 打包和 tree-shaking，减小部署包体积。

```typescript
// ref: LAM-06
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';

const fn = new NodejsFunction(this, 'MyFunction', {
  entry: 'lambda/my-function/index.ts',
  handler: 'handler',
  runtime: lambda.Runtime.NODEJS_20_X,
  bundling: {
    minify: true,
    sourceMap: true,
    externalModules: ['@aws-sdk/*'], // SDK v3 已内置于运行时
  },
});
```

### LAM-07 排除 AWS SDK

AWS SDK v3 已内置于 Node.js 20.x 运行时，打包时必须排除以减小体积。

```typescript
// ref: LAM-07
const fn = new NodejsFunction(this, 'MyFunction', {
  entry: 'lambda/handler.ts',
  bundling: {
    externalModules: ['@aws-sdk/*'],
  },
});
```

### LAM-08 Lambda Layer 使用规范

多个函数共享的依赖（如自定义工具库）使用 Layer 管理。
单个 Layer 不超过 50 MB（解压后 250 MB）。

```typescript
// ref: LAM-08
const sharedLayer = new lambda.LayerVersion(this, 'SharedLayer', {
  code: lambda.Code.fromAsset('layers/shared'),
  compatibleRuntimes: [lambda.Runtime.NODEJS_20_X],
  description: 'Shared utilities and data validation libraries',
});

const fn = new lambda.Function(this, 'MyFunction', {
  layers: [sharedLayer],
  // ...
});
```

---

## 安全与权限

### LAM-09 最小权限 IAM

Lambda 执行角色遵循最小权限原则。使用 CDK 的 `grant*` 方法而非手动编写 IAM 策略。

**正确示例：**
```typescript
// ref: LAM-09
table.grantReadWriteData(fn);   // 仅授予需要的 DynamoDB 权限
bucket.grantRead(fn);           // 仅授予 S3 读取权限
```

**错误示例：**
```typescript
// 错误：授予管理员权限
fn.role?.addManagedPolicy(
  iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess')
);
```

### LAM-10 VPC 内 Lambda

访问 VPC 内资源（RDS、ElastiCache）的 Lambda 必须配置 VPC。
必须放置在 Private 子网中，并配置安全组。

```typescript
// ref: LAM-10
const fn = new lambda.Function(this, 'VpcFunction', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda/vpc-function'),
  vpc,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
  securityGroups: [lambdaSg],
});
```

---

## 性能与并发

### LAM-11 预留并发

关键业务函数必须设置预留并发（Reserved Concurrency），防止被其他函数挤占账户并发额度。

```typescript
// ref: LAM-11
const fn = new lambda.Function(this, 'CriticalFunction', {
  reservedConcurrentExecutions: 100,
  // ...
});
```

### LAM-12 预置并发（Provisioned Concurrency）

对延迟敏感的 API 函数，使用预置并发消除冷启动。配合 Application Auto Scaling 调整。

```typescript
// ref: LAM-12
const version = fn.currentVersion;
const alias = new lambda.Alias(this, 'ProdAlias', {
  aliasName: 'prod',
  version,
  provisionedConcurrentExecutions: 10,
});
```

---

## 监控与告警

### LAM-13 错误告警

每个生产环境 Lambda 函数必须配置错误率告警。错误率超过 5% 时触发告警。

```typescript
// ref: LAM-13
const errorAlarm = fn.metricErrors({
  period: cdk.Duration.minutes(5),
}).createAlarm(this, 'FunctionErrorAlarm', {
  threshold: 5,
  evaluationPeriods: 2,
  alarmDescription: `Lambda ${fn.functionName} error rate too high`,
});
```

### LAM-14 持续时间告警

监控函数执行时间，当 p99 延迟超过 timeout 的 80% 时触发告警。

```typescript
// ref: LAM-14
const durationAlarm = fn.metricDuration({
  period: cdk.Duration.minutes(5),
  statistic: 'p99',
}).createAlarm(this, 'FunctionDurationAlarm', {
  threshold: 12000, // 如果 timeout 是 15s，80% = 12s
  evaluationPeriods: 3,
  alarmDescription: `Lambda ${fn.functionName} p99 duration approaching timeout`,
});
```
