# AWS CDK — VPC 配置规范

本文件定义 VPC 及其相关网络资源（子网、安全组、NAT Gateway 等）的 CDK 配置规范。
所有 VPC 相关的 CDK 代码必须遵循这些规则。

## 目录
- [VPC-01 ~ VPC-05] VPC 基础配置
- [VPC-06 ~ VPC-10] 子网设计
- [VPC-11 ~ VPC-15] 安全组规范
- [VPC-16 ~ VPC-18] NAT 与网关配置
- [VPC-19 ~ VPC-20] VPC 对等连接与端点

---

## VPC 基础配置

### VPC-01 使用标准 CIDR 规划

VPC 必须使用 RFC 1918 私有地址段，并为将来扩展预留足够空间。
生产环境使用 `/16`，开发/测试环境最少使用 `/20`。

**正确示例：**
```typescript
// ref: VPC-01
const vpc = new ec2.Vpc(this, 'MainVpc', {
  ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 3,
});
```

**错误示例：**
```typescript
// 错误：CIDR 太小，无法满足生产环境扩展需要
const vpc = new ec2.Vpc(this, 'MainVpc', {
  ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/24'),
  maxAzs: 3,
});
```

### VPC-02 多可用区部署

生产环境 VPC 必须跨至少 2 个可用区（推荐 3 个）。
禁止生产环境使用单可用区。

```typescript
// ref: VPC-02
const vpc = new ec2.Vpc(this, 'ProdVpc', {
  maxAzs: 3, // 生产环境至少 2，推荐 3
});
```

### VPC-03 VPC 命名规范

VPC 名称使用 `{环境}-{项目}-vpc` 格式，通过 CDK Tag 设置。

```typescript
// ref: VPC-03
const vpc = new ec2.Vpc(this, 'MainVpc', {
  vpcName: `${props.environment}-${props.projectName}-vpc`,
  ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 3,
});
```

### VPC-04 启用 DNS 支持

VPC 必须启用 `enableDnsHostnames` 和 `enableDnsSupport`，以支持内部服务发现。

```typescript
// ref: VPC-04
// ec2.Vpc 默认启用 DNS，无需显式设置。
// 如果使用 CfnVPC，必须显式启用：
const cfnVpc = new ec2.CfnVPC(this, 'Vpc', {
  cidrBlock: '10.0.0.0/16',
  enableDnsHostnames: true,
  enableDnsSupport: true,
});
```

### VPC-05 启用 Flow Logs

生产环境 VPC 必须启用 Flow Logs，发送到 CloudWatch Logs 或 S3，用于安全审计和排障。

```typescript
// ref: VPC-05
vpc.addFlowLog('FlowLog', {
  destination: ec2.FlowLogDestination.toCloudWatchLogs(),
  trafficType: ec2.FlowLogTrafficType.ALL,
});
```

---

## 子网设计

### VPC-06 三层子网架构

每个 VPC 使用 Public / Private / Isolated 三层子网：
- **Public**：仅放 ALB、NAT Gateway 等需要公网访问的资源
- **Private**：放应用层资源（Lambda、ECS、EC2），通过 NAT 访问外网
- **Isolated**：放数据库（RDS、ElastiCache），不允许出站到公网

```typescript
// ref: VPC-06
const vpc = new ec2.Vpc(this, 'MainVpc', {
  ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 3,
  subnetConfiguration: [
    {
      cidrMask: 24,
      name: 'Public',
      subnetType: ec2.SubnetType.PUBLIC,
    },
    {
      cidrMask: 24,
      name: 'Private',
      subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
    },
    {
      cidrMask: 24,
      name: 'Isolated',
      subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
    },
  ],
});
```

### VPC-07 子网 CIDR 分配

Public 子网使用 `/24`，Private 子网使用 `/22` 或 `/24`（视资源密度），
Isolated 子网使用 `/24`。每个可用区的子网 CIDR 不得重叠。

### VPC-08 子网标签

所有子网必须带标签标注用途和环境：

```typescript
// ref: VPC-08
cdk.Tags.of(vpc).add('Network', 'vpc');
// CDK 自动为子网添加 aws-cdk:subnet-name 和 aws-cdk:subnet-type 标签
```

---

## 安全组规范

### VPC-09 最小权限安全组

安全组规则遵循最小权限原则。禁止使用 `0.0.0.0/0` 作为入站来源（ALB 公网入口除外）。

**正确示例：**
```typescript
// ref: VPC-09
const lambdaSg = new ec2.SecurityGroup(this, 'LambdaSg', {
  vpc,
  description: 'Security group for Lambda functions',
  allowAllOutbound: false, // 显式控制出站
});

// 仅允许来自 ALB 安全组的流量
lambdaSg.addIngressRule(albSg, ec2.Port.tcp(443), 'Allow HTTPS from ALB');
```

**错误示例：**
```typescript
// 错误：允许所有 IP 入站
lambdaSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow all');
```

### VPC-10 安全组命名规范

安全组名称格式：`{环境}-{服务名}-sg`。Description 字段必须填写，说明用途。

```typescript
// ref: VPC-10
const sg = new ec2.SecurityGroup(this, 'ApiSg', {
  vpc,
  securityGroupName: `${props.environment}-api-sg`,
  description: 'Security group for API Gateway VPC Link',
});
```

---

## NAT 与网关配置

### VPC-11 NAT Gateway 高可用

生产环境每个可用区部署一个 NAT Gateway。开发/测试环境可以使用单个 NAT Gateway 节省成本。

```typescript
// ref: VPC-11
// 生产环境
const prodVpc = new ec2.Vpc(this, 'ProdVpc', {
  natGateways: 3, // 每个 AZ 一个
  maxAzs: 3,
});

// 开发环境
const devVpc = new ec2.Vpc(this, 'DevVpc', {
  natGateways: 1, // 节省成本
  maxAzs: 2,
});
```

### VPC-12 VPC Endpoints

对于频繁访问的 AWS 服务（S3、DynamoDB、ECR、CloudWatch Logs），
必须配置 VPC Endpoint 以降低数据传输成本并提升安全性。

```typescript
// ref: VPC-12
vpc.addGatewayEndpoint('S3Endpoint', {
  service: ec2.GatewayVpcEndpointAwsService.S3,
});

vpc.addGatewayEndpoint('DynamoDbEndpoint', {
  service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
});

vpc.addInterfaceEndpoint('EcrEndpoint', {
  service: ec2.InterfaceVpcEndpointAwsService.ECR,
});
```
