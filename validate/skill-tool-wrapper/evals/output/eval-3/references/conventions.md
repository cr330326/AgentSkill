# Terraform 编码规范

本文件定义团队 Terraform 项目的硬性规则。所有 IaC 代码必须遵循这些约定，
违反即视为不合规，需在 code review 中修正。

## 目录
- [TF-01 ~ TF-05] 项目结构与文件组织
- [TF-06 ~ TF-10] 命名规范
- [TF-11 ~ TF-14] 状态管理
- [TF-15 ~ TF-18] 部署流程
- [TF-19 ~ TF-22] 模块设计

---

## 项目结构与文件组织

### TF-01 标准目录布局

```
project-name/
├── main.tf                  # 根模块主入口，provider 和核心资源
├── variables.tf             # 根模块输入变量
├── outputs.tf               # 根模块输出值
├── terraform.tf             # terraform 块（required_version、required_providers）
├── backend.tf               # 后端配置（S3）
├── locals.tf                # 局部变量定义
├── data.tf                  # data source 定义
├── modules/                 # 所有自定义模块必须放在此目录下
│   ├── networking/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md        # 每个模块必须有 README
│   └── compute/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── README.md
├── environments/            # 环境级变量文件
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
└── README.md
```

### TF-02 模块必须放在 modules/ 目录下

所有团队自定义模块必须放在项目根目录的 `modules/` 下，禁止散落在项目其他位置。
第三方模块通过 Terraform Registry 或 Git 引用，不复制到本地。

```hcl
# 正确 — 引用 modules/ 下的本地模块
module "networking" {
  source = "./modules/networking"
  vpc_cidr = var.vpc_cidr
}

# 正确 — 引用远程模块
module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"
}
```

```hcl
# 错误 — 模块放在 modules/ 以外的位置
module "networking" {
  source = "./infra/network"   # 禁止！必须放在 modules/ 下
}
```

### TF-03 每个模块必须有 README.md

`modules/` 下的每个模块目录必须包含 `README.md`，至少包含：
- 模块用途说明
- 输入变量列表（可使用 terraform-docs 自动生成）
- 输出值列表
- 使用示例

### TF-04 文件拆分原则

- 每个 `.tf` 文件有明确的单一职责
- 禁止把所有资源堆在一个 `main.tf` 中（超过 200 行应拆分）
- 相关资源放在同一文件中，文件名反映资源类型（如 `iam.tf`、`security_groups.tf`）

### TF-05 环境变量文件

不同环境的配置通过 `.tfvars` 文件管理，放在 `environments/` 目录下。
禁止在代码中硬编码环境相关的值。

```hcl
# environments/prod.tfvars
environment    = "prod"
instance_type  = "m5.xlarge"
instance_count = 3
```

---

## 命名规范

### TF-06 资源与数据源命名

- 使用 `snake_case`
- 名称应反映用途而非资源类型（类型已由资源块声明）
- 如果同类型只有一个资源，使用 `this` 或 `main` 作为名称

```hcl
# 正确
resource "aws_instance" "web_server" {
  ami           = var.ami_id
  instance_type = var.instance_type
}

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
}
```

```hcl
# 错误 — 名称重复资源类型信息
resource "aws_instance" "aws_instance_web" { ... }

# 错误 — 使用 camelCase
resource "aws_instance" "webServer" { ... }
```

### TF-07 变量命名必须用 snake_case 且必须有 description

所有变量名使用 `snake_case`，且每个变量必须包含 `description` 字段。
没有 `description` 的变量定义视为不合规。

```hcl
# 正确
variable "instance_type" {
  description = "EC2 实例类型"
  type        = string
  default     = "t3.micro"
}

variable "vpc_cidr_block" {
  description = "VPC 的 CIDR 地址范围"
  type        = string
}
```

```hcl
# 错误 — 缺少 description
variable "instance_type" {
  type    = string
  default = "t3.micro"
}

# 错误 — 使用 camelCase
variable "instanceType" {
  description = "EC2 instance type"
  type        = string
}
```

### TF-08 输出值命名

输出值使用 `snake_case`，命名格式为 `<资源>_<属性>`：

```hcl
output "vpc_id" {
  description = "VPC 的 ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "公有子网 ID 列表"
  value       = aws_subnet.public[*].id
}
```

### TF-09 标签规范

所有支持标签的资源必须包含以下标准标签：

```hcl
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
}

resource "aws_instance" "web_server" {
  # ...
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-web-${var.environment}"
  })
}
```

### TF-10 局部变量

复杂表达式或重复使用的值提取为 `locals`，避免在资源块中内联复杂逻辑：

```hcl
# 正确
locals {
  subnet_cidrs = [for i in range(var.subnet_count) : cidrsubnet(var.vpc_cidr, 8, i)]
}

resource "aws_subnet" "private" {
  count      = var.subnet_count
  cidr_block = local.subnet_cidrs[count.index]
}
```

---

## 状态管理

### TF-11 必须使用 S3 后端存储

State 文件必须使用 S3 后端远程存储，禁止使用本地 state。
所有项目的 `backend.tf` 必须配置 S3 + DynamoDB 锁：

```hcl
# 正确 — backend.tf
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "projects/my-project/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

```hcl
# 错误 — 使用本地 state（禁止！）
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}

# 错误 — 不配置 backend（默认使用本地 state，同样禁止）
terraform {
  required_version = ">= 1.5.0"
  # 未配置 backend — 将默认使用本地存储
}
```

### TF-12 State 文件加密

S3 后端必须开启 `encrypt = true`，state 文件中可能包含敏感信息（如密码、密钥）。

### TF-13 State 锁定

必须配置 DynamoDB 表进行状态锁定（`dynamodb_table`），防止并发操作导致状态损坏。

### TF-14 State 文件路径规范

S3 key 使用分层路径，格式为 `projects/<项目名>/terraform.tfstate`。
多环境项目使用 `projects/<项目名>/<环境>/terraform.tfstate`。

---

## 部署流程

### TF-15 Plan 输出必须保存为文件再 Apply

`terraform plan` 必须将执行计划保存为文件，`terraform apply` 必须使用该计划文件。
禁止直接运行 `terraform apply` 而不指定 plan 文件。

```bash
# 正确流程
terraform plan -out=tfplan
# 审查 plan 输出后...
terraform apply tfplan
```

```bash
# 错误 — 直接 apply 而未指定 plan 文件
terraform apply
terraform apply -auto-approve
```

### TF-16 Plan 文件命名

Plan 文件命名应包含环境和时间戳信息，便于追踪：

```bash
# 推荐
terraform plan -out="plans/${ENV}-$(date +%Y%m%d-%H%M%S).tfplan"

# 最简
terraform plan -out=tfplan
```

### TF-17 变量文件引用

执行 plan/apply 时必须显式指定环境对应的变量文件：

```bash
terraform plan -var-file=environments/prod.tfvars -out=tfplan
terraform apply tfplan
```

### TF-18 销毁保护

生产环境资源必须启用销毁保护，防止误删：

```hcl
resource "aws_instance" "production" {
  # ...
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_rds_cluster" "production" {
  # ...
  deletion_protection = true
}
```

---

## 模块设计

### TF-19 模块接口规范

每个模块必须包含三个标准文件：

- `variables.tf` — 所有输入变量（每个变量必须有 `description` 和 `type`）
- `outputs.tf` — 所有输出值（每个输出必须有 `description`）
- `main.tf` — 资源定义

### TF-20 模块变量验证

模块的输入变量应使用 `validation` 块进行约束检查：

```hcl
variable "environment" {
  description = "部署环境名称"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment 必须是 dev、staging 或 prod 之一。"
  }
}

variable "cidr_block" {
  description = "CIDR 地址范围"
  type        = string

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "cidr_block 必须是合法的 CIDR 格式。"
  }
}
```

### TF-21 模块不硬编码 Provider

模块内部不定义 `provider` 块，provider 由调用方传入：

```hcl
# 正确 — 模块内不声明 provider
# modules/networking/main.tf
resource "aws_vpc" "this" {
  cidr_block = var.vpc_cidr
}
```

```hcl
# 错误 — 模块内硬编码 provider
# modules/networking/main.tf
provider "aws" {
  region = "us-east-1"   # 禁止在模块中定义 provider！
}
```

### TF-22 模块版本约束

引用远程模块时必须指定版本约束，禁止不锁版本：

```hcl
# 正确
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
}

# 错误 — 未指定版本
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
}
```
