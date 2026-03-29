# Terraform 最佳实践

本文件包含 Terraform 项目的推荐实践。这些是软性建议，遵循可以获得更好的
可维护性、安全性和运维效率，但不是硬性要求。

## 目录
- [BP-01 ~ BP-04] 模块与代码组织
- [BP-05 ~ BP-08] 安全与合规
- [BP-09 ~ BP-12] 运维与协作
- [BP-13 ~ BP-16] 测试与质量保障

---

## 模块与代码组织

### BP-01 模块版本化发布

当模块在多个项目间共享时，推荐使用 Git tag 进行语义化版本控制，
调用方通过版本引用模块，避免意外引入破坏性变更：

```hcl
module "networking" {
  source = "git::https://github.com/company/terraform-modules.git//networking?ref=v2.1.0"
}
```

版本变更时更新 `CHANGELOG.md`，记录新增、修改和移除的变量/输出。

### BP-02 使用 Workspace 管理多环境

对于同一套配置部署到多个环境的场景，推荐使用 Terraform Workspace：

```bash
# 创建并切换环境
terraform workspace new staging
terraform workspace new prod

# 切换到目标环境
terraform workspace select prod
terraform plan -var-file=environments/prod.tfvars -out=tfplan
```

在代码中通过 `terraform.workspace` 引用当前环境：

```hcl
locals {
  environment = terraform.workspace

  instance_type = {
    dev     = "t3.micro"
    staging = "t3.small"
    prod    = "m5.large"
  }
}

resource "aws_instance" "app" {
  instance_type = local.instance_type[local.environment]

  tags = {
    Environment = local.environment
  }
}
```

### BP-03 Data Source 替代硬编码

使用 `data` source 动态查询已有资源的信息，避免硬编码 ID 和 ARN：

```hcl
# 推荐 — 动态查询
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_instance" "web" {
  ami = data.aws_ami.amazon_linux.id
}
```

```hcl
# 不推荐 — 硬编码 AMI ID
resource "aws_instance" "web" {
  ami = "ami-0abcdef1234567890"   # 不同区域/时间会失效
}
```

### BP-04 条件创建资源

使用 `count` 或 `for_each` 实现资源的条件创建，避免注释/删除代码：

```hcl
variable "enable_monitoring" {
  description = "是否启用监控资源"
  type        = bool
  default     = true
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name  = "${var.project_name}-cpu-high"
  namespace   = "AWS/EC2"
  metric_name = "CPUUtilization"
  threshold   = 80
  # ...
}
```

---

## 安全与合规

### BP-05 敏感变量标记

包含密码、密钥等敏感信息的变量必须标记 `sensitive = true`，
防止在 plan 输出和日志中泄露：

```hcl
variable "database_password" {
  description = "RDS 数据库主密码"
  type        = string
  sensitive   = true
}

output "database_endpoint" {
  description = "数据库连接端点"
  value       = aws_rds_cluster.main.endpoint
  # 注意：endpoint 不含密码，不需要标记 sensitive
}
```

### BP-06 使用密钥管理服务

避免在 `.tfvars` 中明文存储密钥，推荐使用 AWS Secrets Manager 或 SSM Parameter Store：

```hcl
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/database/password"
}

resource "aws_rds_cluster" "main" {
  master_password = data.aws_secretsmanager_secret_version.db_password.secret_string
}
```

### BP-07 最小权限原则

IAM 策略遵循最小权限原则，避免使用 `*` 通配符：

```hcl
# 推荐 — 精确授权
resource "aws_iam_policy" "s3_read" {
  name = "s3-read-specific-bucket"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.data.arn,
        "${aws_s3_bucket.data.arn}/*"
      ]
    }]
  })
}
```

```hcl
# 不推荐 — 过度授权
resource "aws_iam_policy" "s3_full" {
  name = "s3-full-access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:*"
      Resource = "*"
    }]
  })
}
```

### BP-08 安全组规则细粒度管理

安全组规则应使用 `aws_security_group_rule` 单独管理，便于追踪变更：

```hcl
resource "aws_security_group" "web" {
  name   = "${var.project_name}-web-sg"
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group_rule" "web_ingress_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.web.id
  description       = "Allow HTTPS from internet"
}
```

---

## 运维与协作

### BP-09 漂移检测

定期运行 `terraform plan` 检测基础设施漂移（实际状态与代码定义不一致）。
推荐在 CI/CD 流水线中设置定时检测任务：

```bash
# CI/CD 定时任务示例
terraform plan -detailed-exitcode -var-file=environments/prod.tfvars
# 退出码：0=无变更，1=错误，2=有漂移
```

发现漂移时应分析原因：
- 手动修改了云资源 → 将变更同步到代码中
- 外部系统自动修改 → 在 `lifecycle` 中使用 `ignore_changes`

```hcl
resource "aws_autoscaling_group" "app" {
  desired_capacity = var.desired_capacity

  lifecycle {
    ignore_changes = [desired_capacity]  # ASG 可能被自动伸缩策略修改
  }
}
```

### BP-10 CI/CD 集成

Terraform 操作应通过 CI/CD 流水线执行，避免个人从本地直接操作生产环境：

```yaml
# GitHub Actions 示例
name: Terraform
on:
  pull_request:
    paths: ['**.tf', '**.tfvars']

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform fmt -check
      - run: terraform validate
      - run: terraform plan -var-file=environments/${{ env.ENV }}.tfvars -out=tfplan
      - run: terraform show -no-color tfplan >> $GITHUB_STEP_SUMMARY
```

### BP-11 代码格式化与验证

提交前运行格式化和验证，推荐在 pre-commit hook 中自动化：

```bash
# 格式化所有 .tf 文件
terraform fmt -recursive

# 验证配置语法
terraform validate
```

推荐配合 `tflint` 进行更深层的检查：

```bash
tflint --init
tflint --recursive
```

### BP-12 Import 已有资源

将已有云资源纳入 Terraform 管理时，使用 `import` 块（Terraform 1.5+）：

```hcl
import {
  to = aws_s3_bucket.legacy_data
  id = "my-existing-bucket-name"
}

resource "aws_s3_bucket" "legacy_data" {
  bucket = "my-existing-bucket-name"
}
```

导入后运行 `terraform plan` 确认无差异，再提交代码。

---

## 测试与质量保障

### BP-13 使用 terraform-docs 自动生成文档

在模块目录中使用 `terraform-docs` 自动生成输入/输出文档到 `README.md`：

```bash
# 为单个模块生成文档
terraform-docs markdown table ./modules/networking > ./modules/networking/README.md
```

在 `README.md` 中使用标记块实现自动更新：

```markdown
<!-- BEGIN_TF_DOCS -->
（terraform-docs 自动填充）
<!-- END_TF_DOCS -->
```

### BP-14 使用 Checkov 进行安全扫描

在 CI/CD 中集成 Checkov 或 tfsec 进行安全合规扫描：

```bash
# Checkov 扫描
checkov -d . --framework terraform

# tfsec 扫描
tfsec .
```

对于已知的合理例外，使用注释跳过：

```hcl
resource "aws_s3_bucket" "public_assets" {
  #checkov:skip=CKV_AWS_18:公开资产桶无需访问日志
  bucket = "${var.project_name}-public-assets"
}
```

### BP-15 模块集成测试

使用 Terratest（Go）或 pytest-terraform 进行模块集成测试：

```go
// Terratest 示例
func TestNetworkingModule(t *testing.T) {
    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/networking",
        Vars: map[string]interface{}{
            "vpc_cidr":    "10.0.0.0/16",
            "environment": "test",
        },
    })
    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    vpcID := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcID)
}
```

### BP-16 Plan 输出审查清单

在 code review 中审查 `terraform plan` 输出时，重点关注：

1. **销毁或替换操作** — 是否预期？是否会导致停机？
2. **安全组变更** — 是否引入了过宽的入站规则？
3. **IAM 变更** — 是否违反最小权限原则？
4. **数据库变更** — 是否触发了实例替换（force replacement）？
5. **资源数量** — 新增/修改/销毁的数量是否合理？
